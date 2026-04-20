from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from typing import Any

import httpx
from openai import OpenAI
import structlog
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings
from app.schemas.record import DoctorAssistResponse, RAGAnswer, RAGCitation, StructuredClinicalData


class ClinicalLLMService:
    def __init__(self) -> None:
        self._openai_client: OpenAI | None = None
        self._logger = structlog.get_logger(__name__)
        self._ollama_start_attempted = False
        self._resolved_ollama_model: str | None = None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def extract_structured_data(self, transcript: str) -> StructuredClinicalData:
        if not transcript.strip():
            return StructuredClinicalData()

        prompt = f"""
You are a multilingual clinical documentation extractor.
Return strict JSON with exactly these keys and no markdown:
{{
  "symptoms": [],
  "duration": "",
  "diagnosis": "",
  "medications": []
}}

Rules:
- Summarize only information directly present in the transcript.
- First understand the transcript fully, even when it is English, Hindi, Marathi, or code-switched mid-sentence.
- Then translate the extracted medical meaning into ENGLISH ONLY.
- Do not copy transcript phrases verbatim unless they are already clean English clinical terms.
- Do not output Hindi, Marathi, Hinglish, or mixed-language text in any JSON value.
- Normalize and summarize the medical facts instead of quoting the conversation.
- Symptoms must be short English terms such as "fever", "cough", "abdominal pain".
- Duration must be normalized English such as "2 days", "1 week", "since yesterday".
- Diagnosis must be an English clinical impression such as "viral upper respiratory infection".
- Medications must be English generic names where possible, such as "paracetamol".
- If a value is unknown, use an empty string or empty array.
- Normalize drug names when obvious, but do not invent.
- Fill "diagnosis" when the doctor says or implies diagnosis using phrases such as:
  "diagnosis is", "impression is", "assessment is", "doctor suspects",
  "likely", "probable", "diagnosed with", "लगता है", "निदान", "संभावना",
  "वाटते", "निदान", or equivalent Hindi/Marathi clinical wording.
- If the transcript only contains symptoms and no clinician assessment, keep diagnosis empty.

Transcript:
{transcript}
        """.strip()

        raw_response = self._generate_json(prompt)
        structured_data = StructuredClinicalData.model_validate(self._extract_json(raw_response))
        structured_data = self._normalize_to_english(structured_data)
        return self._merge_structured_data(structured_data, self.fallback_structured_data(transcript))

    def doctor_assist(
        self,
        transcript: str,
        structured_data: StructuredClinicalData,
    ) -> DoctorAssistResponse:
        if not transcript.strip():
            return self._fallback_assist(structured_data)

        prompt = f"""
You are a doctor-assist copilot reviewing a live consultation transcript.
Return strict JSON with exactly this structure:
{{
  "suggested_diagnosis": "",
  "missing_fields": [],
  "red_flags": []
}}

Use only grounded information from the transcript and extracted data.
If diagnosis certainty is low, say "Needs more assessment".
Missing fields should focus on clinically relevant gaps such as onset, severity, vitals, allergies, and medication history.

Extracted data:
{structured_data.model_dump_json(indent=2)}

Transcript:
{transcript}
        """.strip()

        try:
            raw_response = self._generate_json(prompt)
            parsed = self._extract_json(raw_response)
            return DoctorAssistResponse.model_validate(parsed)
        except Exception:
            return self._fallback_assist(structured_data)

    def answer_with_context(
        self,
        question: str,
        citations: list[RAGCitation],
    ) -> RAGAnswer:
        if not citations:
            return RAGAnswer(answer="No grounded history was found for this query.", citations=[])

        context = "\n\n".join(
            f"[Record {citation.record_id}] Score={citation.score:.3f}\nExcerpt: {citation.excerpt}"
            for citation in citations
        )
        prompt = f"""
Answer the doctor's question using only the provided grounded clinical history.
If the answer is not supported by the context, say so clearly.
Be concise and clinically neutral.

Question:
{question}

Context:
{context}
        """.strip()

        answer = self._generate_text(prompt)
        return RAGAnswer(answer=answer.strip(), citations=citations)

    def _generate_json(self, prompt: str) -> str:
        try:
            return self._generate_with_ollama(prompt, json_mode=True)
        except Exception as exc:
            self._logger.warning("ollama_json_generation_failed", error=str(exc))
            return self._generate_with_openai(prompt, json_mode=True)

    def _generate_text(self, prompt: str) -> str:
        try:
            return self._generate_with_ollama(prompt, json_mode=False)
        except Exception as exc:
            self._logger.warning("ollama_text_generation_failed", error=str(exc))
            return self._generate_with_openai(prompt, json_mode=False)

    def _generate_with_ollama(self, prompt: str, json_mode: bool) -> str:
        model_name = self._ensure_ollama_model()
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        if json_mode:
            payload["format"] = "json"

        response = httpx.post(f"{settings.ollama_base_url}/api/generate", json=payload, timeout=120)
        response.raise_for_status()
        content = response.json().get("response", "")
        if not content.strip():
            raise RuntimeError(f"Ollama model '{model_name}' returned an empty response")
        return content

    def fallback_structured_data(self, transcript: str) -> StructuredClinicalData:
        normalized_transcript = self._translate_common_clinical_terms(transcript)
        normalized_transcript = normalized_transcript.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
        normalized_text = normalized_transcript.lower()

        symptom_map = {
            "fever": ["fever", "temperature", "viral fever"],
            "cough": ["cough"],
            "cold": ["cold", "common cold"],
            "sore throat": ["sore throat", "throat pain"],
            "abdominal pain": ["abdominal pain", "stomach pain"],
            "headache": ["headache"],
            "vomiting": ["vomiting", "vomit"],
            "diarrhea": ["diarrhea", "loose motion", "loose motions"],
            "weakness": ["weakness", "fatigue"],
            "dizziness": ["dizziness"],
            "body ache": ["body ache", "body pain", "body aches"],
            "shortness of breath": ["shortness of breath", "breathlessness"],
        }

        symptoms: list[str] = []
        for canonical, aliases in symptom_map.items():
            if any(self._contains_phrase(normalized_text, alias) for alias in aliases):
                symptoms.append(canonical)

        medications = self._extract_medications(normalized_text)
        duration = self._extract_duration(normalized_transcript)
        diagnosis = self._infer_diagnosis_from_transcript(transcript)

        fallback = StructuredClinicalData(
            symptoms=symptoms,
            duration=duration,
            diagnosis=diagnosis,
            medications=medications,
        )
        return self._normalize_to_english(fallback)

    def _ensure_ollama_model(self) -> str:
        self._ensure_ollama_server()
        available_models = self._list_ollama_models()
        if not available_models:
            raise RuntimeError("Ollama is running but no local models are available")

        configured_model = settings.ollama_model.strip()
        if configured_model in available_models:
            self._resolved_ollama_model = configured_model
            return configured_model

        configured_base = configured_model.split(":", 1)[0]
        base_match = next(
            (model for model in available_models if model == configured_base or model.startswith(f"{configured_base}:")),
            None,
        )
        if base_match:
            self._resolved_ollama_model = base_match
            self._logger.warning(
                "configured_ollama_model_missing_using_closest_match",
                configured_model=configured_model,
                selected_model=base_match,
            )
            return base_match

        preferred_models = ("llama3.2:3b", "llama3.2", "llama3.1:8b", "mistral", "qwen2.5")
        for preferred in preferred_models:
            match = next(
                (model for model in available_models if model == preferred or model.startswith(f"{preferred}:")),
                None,
            )
            if match:
                self._resolved_ollama_model = match
                self._logger.warning(
                    "configured_ollama_model_missing_using_fallback",
                    configured_model=configured_model,
                    selected_model=match,
                )
                return match

        self._resolved_ollama_model = available_models[0]
        self._logger.warning(
            "configured_ollama_model_missing_using_first_available",
            configured_model=configured_model,
            selected_model=available_models[0],
        )
        return available_models[0]

    def _ensure_ollama_server(self) -> None:
        if self._ollama_is_available():
            return
        if not shutil.which("ollama"):
            raise RuntimeError("Ollama binary is not installed")
        if not self._ollama_start_attempted:
            self._ollama_start_attempted = True
            self._logger.warning("starting_ollama_server", base_url=settings.ollama_base_url)
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self._ollama_is_available():
                return
            time.sleep(0.5)
        raise RuntimeError(f"Ollama is not reachable at {settings.ollama_base_url}")

    def _ollama_is_available(self) -> bool:
        try:
            response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _list_ollama_models(self) -> list[str]:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models", [])
        return [
            model.get("name", "").strip()
            for model in models
            if isinstance(model, dict) and model.get("name", "").strip()
        ]

    @staticmethod
    def _infer_diagnosis_from_transcript(transcript: str) -> str:
        patterns = [
            r"(?:diagnosis|assessment|impression)\s*(?:is|:)?\s*([A-Za-z][A-Za-z\s\-\/]+?)(?:[.।,;]|$)",
            r"(?:doctor\s+suspects|suspected|likely|probable|diagnosed\s+with)\s+([A-Za-z][A-Za-z\s\-\/]+?)(?:[.।,;]|$)",
            r"(?:निदान|संभावना|लगता है)\s*(?:है|:)?\s*([\u0900-\u097F\w\s\-\/]+?)(?:[.।,;]|$)",
            r"(?:निदान|शक्यता|वाटते)\s*(?:आहे|:)?\s*([\u0900-\u097F\w\s\-\/]+?)(?:[.।,;]|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, transcript, flags=re.IGNORECASE)
            if not match:
                continue
            diagnosis = " ".join(match.group(1).split()).strip(" -:/")
            if diagnosis:
                return ClinicalLLMService._translate_common_clinical_terms(diagnosis)[:120]
        return ""

    @classmethod
    def _normalize_to_english(cls, structured_data: StructuredClinicalData) -> StructuredClinicalData:
        structured_data.symptoms = [
            cls._clean_english_phrase(cls._translate_common_clinical_terms(symptom)).lower()
            for symptom in structured_data.symptoms
            if cls._clean_english_phrase(cls._translate_common_clinical_terms(symptom))
        ]
        structured_data.duration = cls._normalize_duration(
            cls._clean_english_phrase(cls._translate_common_clinical_terms(structured_data.duration))
        )
        structured_data.diagnosis = cls._clean_english_phrase(
            cls._translate_common_clinical_terms(structured_data.diagnosis)
        )
        structured_data.medications = [
            cls._normalize_medication_name(
                cls._clean_english_phrase(cls._translate_common_clinical_terms(medication))
            )
            for medication in structured_data.medications
            if cls._clean_english_phrase(cls._translate_common_clinical_terms(medication))
        ]
        structured_data.symptoms = cls._unique_preserve_order(structured_data.symptoms)
        structured_data.medications = cls._unique_preserve_order(structured_data.medications)
        return structured_data

    @classmethod
    def _translate_common_clinical_terms(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if not normalized:
            return ""

        replacements = {
            "बुखार": "fever",
            "ताप": "fever",
            "खांसी": "cough",
            "खोकला": "cough",
            "सर्दी": "cold",
            "जुकाम": "cold",
            "गले में दर्द": "sore throat",
            "घसा दुखणे": "sore throat",
            "पेट दर्द": "abdominal pain",
            "पोटदुखी": "abdominal pain",
            "सर दर्द": "headache",
            "सिर दर्द": "headache",
            "डोकेदुखी": "headache",
            "उल्टी": "vomiting",
            "दस्त": "diarrhea",
            "जुलाब": "diarrhea",
            "कमजोरी": "weakness",
            "अशक्तपणा": "weakness",
            "चक्कर": "dizziness",
            "वायरल बुखार": "viral fever",
            "वायरल ताप": "viral fever",
            "वायरल इन्फेक्शन": "viral infection",
            "ऊपरी श्वसन संक्रमण": "upper respiratory infection",
            "श्वसन संक्रमण": "respiratory infection",
            "गैस्ट्राइटिस": "gastritis",
            "अम्लपित्त": "gastritis",
            "पैरासिटामोल": "paracetamol",
            "क्रोसिन": "paracetamol",
            "डोलो": "paracetamol",
            "ओमेप्राजोल": "omeprazole",
            "अज़िथ्रोमाइसिन": "azithromycin",
        }

        for source, target in replacements.items():
            normalized = re.sub(re.escape(source), target, normalized, flags=re.IGNORECASE)
        return normalized.strip()

    @staticmethod
    def _clean_english_phrase(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return ""

        normalized = re.sub(r"[\u0900-\u097F]+", " ", normalized)
        normalized = re.sub(r"[^A-Za-z0-9,\-\/ ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip(" ,-/")
        return normalized

    @staticmethod
    def _unique_preserve_order(values: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = value.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(value)
        return unique

    @staticmethod
    def _normalize_medication_name(value: str) -> str:
        normalized = value.strip().lower()
        normalized = re.sub(r"\b(?:tablet|tablets|tab|capsule|capsules|cap|syrup)\b", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        aliases = {
            "crocin": "paracetamol",
            "crossin": "paracetamol",
            "crosin": "paracetamol",
            "dolo": "paracetamol",
            "acetaminophen": "paracetamol",
            "combiflam": "ibuprofen",
        }
        return aliases.get(normalized, normalized)

    @classmethod
    def _normalize_duration(cls, value: str) -> str:
        normalized = value.strip()
        replacements = {
            "दो दिन": "2 days",
            "२ दिन": "2 days",
            "दोन दिवस": "2 days",
            "तीन दिन": "3 days",
            "३ दिन": "3 days",
            "तीन दिवस": "3 days",
            "एक हफ्ता": "1 week",
            "एक सप्ताह": "1 week",
            "एक आठवडा": "1 week",
            "कल से": "since yesterday",
            "कालपासून": "since yesterday",
        }
        for source, target in replacements.items():
            normalized = re.sub(re.escape(source), target, normalized, flags=re.IGNORECASE)
        return normalized

    @staticmethod
    def _contains_phrase(text: str, phrase: str) -> bool:
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in phrase.split()) + r"\b"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    @classmethod
    def _extract_duration(cls, transcript: str) -> str:
        normalized = cls._translate_common_clinical_terms(transcript)
        normalized = normalized.translate(str.maketrans("०१२३४५६७८९", "0123456789"))

        patterns = [
            r"(?:for|since)\s+(\d+\s+(?:day|days|week|weeks|month|months|year|years))\b",
            r"\b(\d+\s+(?:day|days|week|weeks|month|months|year|years))\b",
            r"\b(since yesterday|since today|today morning|this morning)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                return cls._normalize_duration(match.group(1).lower())
        return ""

    @classmethod
    def _extract_medications(cls, normalized_text: str) -> list[str]:
        medication_aliases = {
            "paracetamol": ["paracetamol", "crocin", "crossin", "crosin", "dolo", "acetaminophen"],
            "ibuprofen": ["ibuprofen", "combiflam"],
            "azithromycin": ["azithromycin"],
            "amoxicillin": ["amoxicillin"],
            "metformin": ["metformin"],
            "cetirizine": ["cetirizine"],
            "omeprazole": ["omeprazole"],
        }

        medications: list[str] = []
        for canonical, aliases in medication_aliases.items():
            if any(cls._contains_phrase(normalized_text, alias) for alias in aliases):
                medications.append(canonical)
        return medications

    @staticmethod
    def _merge_structured_data(
        structured_data: StructuredClinicalData,
        fallback_data: StructuredClinicalData,
    ) -> StructuredClinicalData:
        return StructuredClinicalData(
            symptoms=ClinicalLLMService._unique_preserve_order(
                structured_data.symptoms + fallback_data.symptoms
            ),
            duration=structured_data.duration or fallback_data.duration,
            diagnosis=structured_data.diagnosis or fallback_data.diagnosis,
            medications=ClinicalLLMService._unique_preserve_order(
                structured_data.medications + fallback_data.medications
            ),
        )

    def _generate_with_openai(self, prompt: str, json_mode: bool) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI fallback requested but OPENAI_API_KEY is missing")
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=settings.openai_api_key)

        kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": "You are a precise clinical AI assistant."},
                {"role": "user", "content": prompt},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._openai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    @staticmethod
    def _extract_json(raw_response: str) -> dict[str, Any]:
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    @staticmethod
    def _fallback_assist(structured_data: StructuredClinicalData) -> DoctorAssistResponse:
        missing_fields: list[str] = []
        if not structured_data.symptoms:
            missing_fields.append("symptoms")
        if not structured_data.duration:
            missing_fields.append("duration")
        if not structured_data.diagnosis:
            missing_fields.append("diagnosis")
        if not structured_data.medications:
            missing_fields.append("medications")
        missing_fields.extend(["allergies", "vitals"])

        return DoctorAssistResponse(
            suggested_diagnosis=structured_data.diagnosis or "Needs more assessment",
            missing_fields=missing_fields,
            red_flags=[],
        )
