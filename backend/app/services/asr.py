from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import settings


@dataclass
class ASRResult:
    text: str
    language: str
    confidence: float


class ASRService:
    def __init__(self) -> None:
        self._whisper_model = None
        self._openai_client: OpenAI | None = None
        self._sarvam_client = None

    def transcribe_chunk(self, audio_bytes: bytes, mime_type: str) -> ASRResult:
        if settings.asr_provider == "openai" and settings.openai_api_key:
            return self._transcribe_with_openai(audio_bytes, mime_type)
        try:
            return self._transcribe_with_faster_whisper(audio_bytes, mime_type)
        except Exception:
            if settings.openai_api_key:
                return self._transcribe_with_openai(audio_bytes, mime_type)
            raise

    def transcribe_consultation(
        self,
        audio_bytes: bytes,
        filename: str,
        mime_type: str,
        language_hint: str | None = None,
    ) -> ASRResult:
        if settings.sarvam_api_key:
            return self._transcribe_with_sarvam(audio_bytes, filename, mime_type, language_hint)
        return self.transcribe_chunk(audio_bytes, mime_type)

    def _transcribe_with_faster_whisper(self, audio_bytes: bytes, mime_type: str) -> ASRResult:
        from faster_whisper import WhisperModel

        if self._whisper_model is None:
            self._whisper_model = WhisperModel(
                settings.whisper_model_size,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )

        suffix = self._suffix_for_mime(mime_type)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        try:
            segments, info = self._whisper_model.transcribe(
                str(tmp_path),
                beam_size=1,
                vad_filter=True,
                multilingual=True,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return ASRResult(
                text=text,
                language=self._normalize_language(getattr(info, "language", None)),
                confidence=float(getattr(info, "language_probability", 0.0) or 0.0),
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def _transcribe_with_openai(self, audio_bytes: bytes, mime_type: str) -> ASRResult:
        if self._openai_client is None:
            self._openai_client = OpenAI(api_key=settings.openai_api_key)

        response = self._openai_client.audio.transcriptions.create(
            model=settings.openai_whisper_model,
            file=("audio_chunk.webm", audio_bytes, mime_type),
            response_format="verbose_json",
        )
        return ASRResult(
            text=getattr(response, "text", "").strip(),
            language=self._normalize_language(getattr(response, "language", None)),
            confidence=1.0,
        )

    def _transcribe_with_sarvam(
        self,
        audio_bytes: bytes,
        filename: str,
        mime_type: str,
        language_hint: str | None,
    ) -> ASRResult:
        from sarvamai import SarvamAI

        if self._sarvam_client is None:
            self._sarvam_client = SarvamAI(api_subscription_key=settings.sarvam_api_key)

        safe_filename = Path(filename or "consultation.webm").name
        suffix = Path(safe_filename).suffix or self._suffix_for_mime(mime_type)

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / f"consultation{suffix}"
            audio_path.write_bytes(audio_bytes)

            job = self._sarvam_client.speech_to_text_job.create_job(
                model=settings.sarvam_asr_model,
                mode=settings.sarvam_asr_mode,
                language_code=self._sarvam_language_code(language_hint),
            )
            job.upload_files([str(audio_path)], timeout=120)
            job.start()
            status = job.wait_until_complete(
                poll_interval=settings.sarvam_asr_poll_interval_seconds,
                timeout=settings.sarvam_asr_timeout_seconds,
            )
            if status.job_state.lower() != "completed":
                raise RuntimeError(f"Sarvam transcription job failed: {status.error_message or status.job_state}")

            file_results = job.get_file_results()
            if file_results["failed"]:
                first_error = file_results["failed"][0]
                raise RuntimeError(
                    first_error.get("error_message")
                    or f"Sarvam transcription failed for {first_error.get('file_name', 'audio file')}"
                )

            job.download_outputs(tmpdir)
            output_path = Path(tmpdir) / f"{audio_path.name}.json"
            payload = json.loads(output_path.read_text())
            transcript = self._extract_sarvam_transcript(payload)
            return ASRResult(
                text=transcript,
                language=self._normalize_language(payload.get("language_code")),
                confidence=float(payload.get("language_probability") or 1.0),
            )

    @staticmethod
    def _extract_sarvam_transcript(payload: dict[str, Any]) -> str:
        transcript = payload.get("transcript")
        if isinstance(transcript, str) and transcript.strip():
            return transcript.strip()

        diarized = payload.get("diarized_transcript")
        if isinstance(diarized, list):
            parts = [
                entry.get("transcript", "").strip()
                for entry in diarized
                if isinstance(entry, dict) and entry.get("transcript")
            ]
            if parts:
                return " ".join(parts).strip()

        raise RuntimeError("Sarvam did not return a transcript")

    @staticmethod
    def _suffix_for_mime(mime_type: str) -> str:
        normalized = mime_type.split(";", 1)[0].strip().lower()
        mapping = {
            "audio/webm": ".webm",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mp4": ".mp4",
            "audio/m4a": ".m4a",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/ogg": ".ogg",
            "audio/aiff": ".aiff",
            "audio/x-aiff": ".aiff",
        }
        return mapping.get(normalized, ".webm")

    @staticmethod
    def _sarvam_audio_codec(mime_type: str, filename: str) -> str:
        normalized = mime_type.split(";", 1)[0].strip().lower()
        mapping = {
            "audio/webm": "webm",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/mp4": "mp4",
            "audio/m4a": "x-m4a",
            "audio/mpeg": "mp3",
            "audio/mp3": "mp3",
            "audio/ogg": "ogg",
            "audio/aiff": "aiff",
            "audio/x-aiff": "x-aiff",
        }
        if normalized in mapping:
            return mapping[normalized]

        extension = Path(filename).suffix.lower()
        extension_mapping = {
            ".webm": "webm",
            ".wav": "wav",
            ".mp4": "mp4",
            ".m4a": "x-m4a",
            ".mp3": "mp3",
            ".ogg": "ogg",
            ".aiff": "aiff",
        }
        return extension_mapping.get(extension, "webm")

    @staticmethod
    def _sarvam_language_code(language: str | None) -> str:
        normalized = (language or "unknown").strip().lower()
        mapping = {
            "english": "en-IN",
            "en": "en-IN",
            "en-in": "en-IN",
            "hindi": "hi-IN",
            "hi": "hi-IN",
            "hi-in": "hi-IN",
            "marathi": "mr-IN",
            "mr": "mr-IN",
            "mr-in": "mr-IN",
        }
        return mapping.get(normalized, "unknown")

    @staticmethod
    def _normalize_language(language: str | None) -> str:
        if not language:
            return "unknown"
        normalized = language.lower()
        if normalized in {"en", "en-in", "english"}:
            return "english"
        if normalized in {"hi", "hi-in", "hindi"}:
            return "hindi"
        if normalized in {"mr", "mr-in", "marathi"}:
            return "marathi"
        return normalized
