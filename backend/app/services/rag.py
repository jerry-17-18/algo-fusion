from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.record import Record
from app.models.session import ClinicalSession
from app.schemas.record import RAGAnswer, RAGCitation, StructuredClinicalData
from app.services.extraction import ClinicalLLMService

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover - optional on lightweight deployments
    faiss = None

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional on lightweight deployments
    np = None

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:  # pragma: no cover - optional on lightweight deployments
    SentenceTransformer = None


@dataclass
class IndexedRecord:
    record_id: str
    patient_id: str
    session_id: str
    excerpt: str


class RAGService:
    def __init__(self, llm_service: ClinicalLLMService) -> None:
        self.llm_service = llm_service
        self.index: Any | None = None
        self.metadata: list[IndexedRecord] = []
        self.dimension: int | None = None
        self._embedding_model: Any | None = None
        self._openai_client: OpenAI | None = None
        settings.faiss_index_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def rebuild(self, db: Session) -> None:
        records = list(db.scalars(select(Record).order_by(Record.created_at.asc())).all())
        indexed_records = [
            IndexedRecord(
                record_id=str(record.id),
                patient_id=str(record.patient_id),
                session_id=str(record.session_id),
                excerpt=(record.rag_summary or record.raw_transcript or "")[:1500],
            )
            for record in records
            if (record.rag_summary or record.raw_transcript)
        ]
        self._write_index(indexed_records)

    def refresh_record_from_session(self, db: Session, session_id: UUID) -> None:
        session = db.get(ClinicalSession, session_id)
        if not session or not session.record:
            return

        existing = [item for item in self.metadata if item.record_id != str(session.record.id)]
        existing.append(
            IndexedRecord(
                record_id=str(session.record.id),
                patient_id=str(session.record.patient_id),
                session_id=str(session.record.session_id),
                excerpt=(session.record.rag_summary or session.record.raw_transcript or "")[:1500],
            )
        )
        self._write_index(existing)

    def answer_question(
        self,
        db: Session,
        question: str,
        patient_id: UUID | None,
        top_k: int,
    ) -> RAGAnswer:
        direct_answer = self._answer_from_structured_history(db, question, patient_id)
        if direct_answer is not None:
            return direct_answer

        if not self.metadata:
            self.rebuild(db)
        citations = self.search(question=question, patient_id=patient_id, top_k=top_k)
        return self.llm_service.answer_with_context(question=question, citations=citations)

    def search(self, question: str, patient_id: UUID | None, top_k: int) -> list[RAGCitation]:
        if not self.metadata:
            return []

        top_k = max(1, top_k)
        if self._can_use_vector_search():
            return self._vector_search(question=question, patient_id=patient_id, top_k=top_k)
        return self._lexical_search(question=question, patient_id=patient_id, top_k=top_k)

    def _load(self) -> None:
        metadata_path = Path(settings.faiss_metadata_path)
        if metadata_path.exists():
            self.metadata = [IndexedRecord(**item) for item in json.loads(metadata_path.read_text())]

        if not self._can_use_vector_search():
            return

        index_path = Path(settings.faiss_index_path)
        if index_path.exists():
            self.index = faiss.read_index(str(index_path))
            self.dimension = self.index.d

    def _write_index(self, records: list[IndexedRecord]) -> None:
        self.metadata = records
        metadata_path = Path(settings.faiss_metadata_path)
        if not records:
            self.index = None
            self.dimension = None
            Path(settings.faiss_index_path).unlink(missing_ok=True)
            metadata_path.write_text("[]")
            return

        metadata_path.write_text(json.dumps([asdict(item) for item in records], indent=2))
        if not self._can_use_vector_search():
            self.index = None
            self.dimension = None
            return

        vectors = np.vstack([self._embed(record.excerpt)[0] for record in records]).astype("float32")
        self.dimension = vectors.shape[1]
        index = faiss.IndexFlatIP(self.dimension)
        index.add(vectors)
        self.index = index
        faiss.write_index(index, settings.faiss_index_path)

    def _embed(self, text: str):
        if np is None:
            raise RuntimeError("NumPy is required for vector embeddings")

        if settings.embedding_provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings")
            if self._openai_client is None:
                self._openai_client = OpenAI(api_key=settings.openai_api_key)
            response = self._openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return np.array([response.data[0].embedding], dtype="float32")

        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is unavailable")
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(settings.embedding_model)
        embedding = self._embedding_model.encode(text, normalize_embeddings=True)
        return np.array([embedding], dtype="float32")

    def _vector_search(self, question: str, patient_id: UUID | None, top_k: int) -> list[RAGCitation]:
        if self.index is None:
            return []

        query_vector = self._embed(question)
        scores, indices = self.index.search(query_vector, min(max(top_k * 3, top_k), len(self.metadata)))
        results: list[RAGCitation] = []
        patient_filter = str(patient_id) if patient_id else None

        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx < 0:
                continue
            item = self.metadata[idx]
            if patient_filter and item.patient_id != patient_filter:
                continue
            results.append(
                RAGCitation(
                    record_id=UUID(item.record_id),
                    session_id=UUID(item.session_id),
                    excerpt=item.excerpt,
                    score=float(score),
                )
            )
            if len(results) >= top_k:
                break
        return results

    def _lexical_search(self, question: str, patient_id: UUID | None, top_k: int) -> list[RAGCitation]:
        patient_filter = str(patient_id) if patient_id else None
        query_tokens = self._tokenize(question)
        scored_items: list[tuple[float, IndexedRecord]] = []

        for item in self.metadata:
            if patient_filter and item.patient_id != patient_filter:
                continue
            excerpt_tokens = self._tokenize(item.excerpt)
            overlap = len(query_tokens & excerpt_tokens)
            coverage = overlap / max(len(query_tokens), 1)
            score = coverage + math.log(len(item.excerpt) + 1, 10) * 0.01
            if score <= 0:
                continue
            scored_items.append((score, item))

        scored_items.sort(key=lambda entry: entry[0], reverse=True)
        return [
            RAGCitation(
                record_id=UUID(item.record_id),
                session_id=UUID(item.session_id),
                excerpt=item.excerpt,
                score=float(score),
            )
            for score, item in scored_items[:top_k]
        ]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if token}

    def _can_use_vector_search(self) -> bool:
        if faiss is None or np is None:
            return False
        if settings.embedding_provider == "openai":
            return bool(settings.openai_api_key)
        return SentenceTransformer is not None

    def _answer_from_structured_history(
        self,
        db: Session,
        question: str,
        patient_id: UUID | None,
    ) -> RAGAnswer | None:
        focus = self._detect_focus(question)
        if patient_id is None or focus is None:
            return None

        records = list(
            db.scalars(
                select(Record)
                .where(Record.patient_id == patient_id)
                .order_by(Record.created_at.desc())
            ).all()
        )
        if not records:
            return RAGAnswer(answer="No grounded history was found for this patient.", citations=[])

        citations = [
            RAGCitation(
                record_id=record.id,
                session_id=record.session_id,
                excerpt=(record.rag_summary or record.raw_transcript or "")[:1500],
                score=1.0,
            )
            for record in records[:4]
            if (record.rag_summary or record.raw_transcript)
        ]
        answer = self._format_history_answer(records, focus)
        return RAGAnswer(answer=answer, citations=citations)

    @staticmethod
    def _detect_focus(question: str) -> str | None:
        normalized = question.lower()
        if any(token in normalized for token in ["symptom", "symptoms", "symtom", "symtoms", "complaint", "problem"]):
            return "symptoms"
        if any(token in normalized for token in ["medication", "medications", "medicine", "medicines", "drug", "prescribed"]):
            return "medications"
        if any(token in normalized for token in ["diagnosis", "diagnosed", "impression", "assessment", "condition"]):
            return "diagnosis"
        if any(token in normalized for token in ["duration", "how long", "since when", "onset", "from when"]):
            return "duration"
        if any(token in normalized for token in ["history", "past", "previous", "earlier", "last visit", "prior"]):
            return "overview"
        return None

    @staticmethod
    def _format_history_answer(records: list[Record], focus: str) -> str:
        if focus == "overview":
            lines = [
                RAGService._format_overview_line(record)
                for record in records
                if RAGService._format_overview_line(record)
            ]
            if not lines:
                return "No grounded clinical history was found for this patient."
            return "Grounded patient history: " + " ".join(lines[:4])

        labels = {
            "symptoms": "Past recorded symptoms",
            "medications": "Previously recorded medications",
            "diagnosis": "Previously recorded diagnoses",
            "duration": "Previously recorded durations",
        }

        details: list[str] = []
        for record in records:
            structured = StructuredClinicalData.model_validate(record.structured_data or {})
            value = RAGService._value_for_focus(structured, focus)
            if not value:
                continue
            details.append(f"{RAGService._format_date(record)}: {value}")

        if not details:
            return f"{labels[focus]} were not found in the stored patient history."
        return f"{labels[focus]}: " + "; ".join(details[:6]) + "."

    @staticmethod
    def _value_for_focus(structured: StructuredClinicalData, focus: str) -> str:
        if focus == "symptoms":
            return ", ".join(structured.symptoms)
        if focus == "medications":
            return ", ".join(structured.medications)
        if focus == "diagnosis":
            return structured.diagnosis
        if focus == "duration":
            return structured.duration
        return ""

    @staticmethod
    def _format_overview_line(record: Record) -> str:
        structured = StructuredClinicalData.model_validate(record.structured_data or {})
        parts = [
            f"symptoms {', '.join(structured.symptoms)}" if structured.symptoms else "",
            f"duration {structured.duration}" if structured.duration else "",
            f"diagnosis {structured.diagnosis}" if structured.diagnosis else "",
            f"medications {', '.join(structured.medications)}" if structured.medications else "",
        ]
        parts = [part for part in parts if part]
        if not parts:
            return ""
        return f"On {RAGService._format_date(record)}, " + "; ".join(parts) + "."

    @staticmethod
    def _format_date(record: Record) -> str:
        return record.created_at.strftime("%d %b %Y")
