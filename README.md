# Voice-Driven Clinical AI

Production-grade full-stack scaffold for a browser-based clinical copilot that captures live consultation audio, streams it over WebSockets, transcribes multilingual speech, extracts strict structured medical JSON, stores records in PostgreSQL, and supports grounded RAG queries over prior encounters.

## Stack

- Frontend: React + TypeScript + Tailwind + Vite
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL
- Realtime transport: WebSockets
- ASR: `faster-whisper` with OpenAI Whisper fallback
- LLM extraction: Ollama with OpenAI fallback
- Vector search: FAISS
- Containers: Docker Compose

## Folder Structure

```text
.
├── backend
│   ├── alembic
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── db
│   │   ├── models
│   │   ├── schemas
│   │   └── services
│   ├── sample_data
│   └── scripts
├── frontend
│   ├── src
│   │   ├── components
│   │   ├── context
│   │   ├── hooks
│   │   ├── lib
│   │   └── pages
├── .env.example
└── docker-compose.yml
```

## Core Capabilities

- JWT login with `doctor` role
- Doctor dashboard for patient selection and start/stop recording
- Browser audio chunking every 1.5 seconds with WebSocket streaming
- Incremental transcription updates in the UI
- Multilingual handling for English, Hindi, and Marathi, including code-switched chunks
- Strict JSON extraction into:

```json
{
  "symptoms": [],
  "duration": "",
  "diagnosis": "",
  "medications": []
}
```

- Retry path for malformed JSON responses from the LLM
- PostgreSQL persistence across `patients`, `sessions`, `records`, and `users`
- FAISS-backed patient-history retrieval for grounded clinical Q&A
- Doctor Assist panel for likely diagnosis and missing-field awareness
- Medication normalization for a small set of common drug aliases
- Dockerized backend, frontend, PostgreSQL, and Ollama services

## Backend Architecture

### API Surface

- `POST /api/v1/auth/login`
- `GET /api/v1/patients`
- `POST /api/v1/patients`
- `POST /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/sessions/{session_id}/stop`
- `GET /api/v1/records/patient/{patient_id}`
- `POST /api/v1/rag/query`
- `WS /api/v1/ws/clinical?token=...&session_id=...`
- Swagger docs: `/docs`

### Services

- `ASRService`: local `faster-whisper` first, OpenAI fallback on failure
- `ClinicalLLMService`: Ollama-first extraction, doctor assist, and grounded answer generation
- `ClinicalPipelineService`: transcript aggregation, structured extraction, record upsert
- `MedicationValidatorService`: lightweight normalization and dedupe of common drug names
- `RAGService`: embedding, FAISS index persistence, retrieval, and grounded answering

## Frontend Experience

- Secure doctor login
- Patient selector
- Start/stop consultation recording
- Live transcript stream with detected language badges
- Structured medical data panel
- Doctor Assist panel
- RAG chatbot for querying prior patient history

## Environment Setup

1. Copy the template:

```bash
cp .env.example .env
```

For standalone local app runs, you can also copy:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Set any secrets or provider overrides you need:

- `SECRET_KEY`
- `OPENAI_API_KEY` for fallback LLM/ASR/embeddings
- `OLLAMA_MODEL` if you want a different local model
- `ASR_PROVIDER=openai` if you prefer remote transcription

## Run With Docker

```bash
docker compose up --build
```

The stack exposes:

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:8000](http://localhost:8000)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- PostgreSQL: `localhost:5432`
- Ollama: `localhost:11434`

### Ollama Model Pull

After the Ollama container starts, pull the configured model:

```bash
docker compose exec ollama ollama pull llama3.1:8b
```

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Deploy To Vercel

This repo is configured for a Vercel multi-service deployment:

- `frontend/` serves the React + Vite app at `/`
- `api/index.py` serves FastAPI at `/api`

Key files:

- `vercel.json`
- `.vercelignore`
- `api/index.py`
- `api/requirements.txt`

### Required Vercel project settings

In the Vercel dashboard, set the Framework Preset to `Services`.

### Required environment variables

Set these in Vercel Project Settings:

- `DATABASE_URL`
- `SECRET_KEY`
- `SARVAM_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-4o-mini`
- `ASR_PROVIDER=sarvam`
- `EMBEDDING_PROVIDER=openai`
- `FAISS_INDEX_PATH=/tmp/clinical.index`
- `FAISS_METADATA_PATH=/tmp/clinical-meta.json`
- `SEED_DEMO_DATA=true`
- `DEMO_DOCTOR_USERNAME=doctor`
- `DEMO_DOCTOR_PASSWORD=doctor123`

Recommended for Vercel:

- Use hosted PostgreSQL such as Neon or Supabase
- Use OpenAI for extraction/embeddings instead of local Ollama
- Keep `OLLAMA_BASE_URL` unset or harmless; the backend will fall back to OpenAI when Ollama is unavailable

### Deploy commands

```bash
vercel login
vercel link
vercel --prod
```

## Demo Credentials

- Username: `doctor`
- Password: `doctor123`

Demo patients are seeded automatically from [backend/sample_data/patients.json](/Users/ritik.nehra.18/Documents/New%20project/backend/sample_data/patients.json).

For local development, both `localhost` and `127.0.0.1` origins are supported for the frontend dev server so browser login requests do not fail on CORS.

## WebSocket Payload Contract

The frontend sends base64-encoded audio chunks:

```json
{
  "type": "audio_chunk",
  "session_id": "uuid",
  "mime_type": "audio/webm;codecs=opus",
  "data": "<base64>"
}
```

The backend returns live updates:

```json
{
  "type": "update",
  "session_id": "uuid",
  "transcript_chunk": "patient says the pain started two days ago",
  "full_transcript": "....",
  "detected_languages": ["english", "hindi"],
  "structured_data": {
    "symptoms": ["stomach pain"],
    "duration": "2 days",
    "diagnosis": "",
    "medications": ["paracetamol"]
  },
  "doctor_assist": {
    "suggested_diagnosis": "Needs more assessment",
    "missing_fields": ["diagnosis", "allergies", "vitals"],
    "red_flags": []
  }
}
```

## Database Schema

- `users`: doctor accounts and auth metadata
- `patients`: patient master data
- `sessions`: encounter lifecycle, transcript, language tracking
- `records`: structured clinical output, doctor assist state, RAG summaries

## Notes and Assumptions

- Browser capture uses `MediaRecorder` with `audio/webm` chunks, which `ffmpeg` in the backend container decodes for Whisper.
- Local ASR and embeddings are optimized for deployability rather than GPU-only performance.
- FAISS persistence is file-backed under `backend/data` inside the container volume.
- RAG indexing is refreshed on startup and after session stop.
- The current medication validator is intentionally lightweight and should be extended for real drug dictionaries or formulary integrations.

## Recommended Next Steps

- Add automated tests for the WebSocket pipeline and API auth flows
- Add PHI-safe audit logging and observability sinks
- Integrate a production-grade drug knowledge base
- Add encrypted object storage for raw audio retention if needed
- Expand role model beyond doctors
