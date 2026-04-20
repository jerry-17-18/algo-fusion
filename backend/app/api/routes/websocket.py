import base64
import json
from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketState

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.enums import SessionStatus, UserRole
from app.models.session import ClinicalSession
from app.models.user import User
from app.schemas.session import PipelineUpdate
from app.services.runtime import asr_service, clinical_pipeline

router = APIRouter()


def _authenticate_websocket(token: str) -> User | None:
    with SessionLocal() as db:
        try:
            payload = decode_access_token(token)
            user_id = UUID(payload.get("sub"))
        except (TypeError, ValueError):
            return None
        user = db.get(User, user_id)
        if not user or not user.is_active or user.role != UserRole.doctor:
            return None
        return user


@router.websocket("/clinical")
async def clinical_stream(
    websocket: WebSocket,
    token: str = Query(...),
    session_id: UUID = Query(...),
) -> None:
    user = await run_in_threadpool(_authenticate_websocket, token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await websocket.send_json({"type": "connected", "session_id": str(session_id)})

    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            message_type = payload.get("type")

            if message_type == "stop":
                await websocket.send_json({"type": "stopped", "session_id": str(session_id)})
                break

            if message_type != "audio_chunk":
                await websocket.send_json({"type": "warning", "message": "Unsupported message type"})
                continue

            chunk_b64 = payload.get("data", "")
            mime_type = payload.get("mime_type", "audio/webm")
            audio_bytes = base64.b64decode(chunk_b64)

            asr_result = await run_in_threadpool(asr_service.transcribe_chunk, audio_bytes, mime_type)
            if not asr_result.text.strip():
                await websocket.send_json(
                    {
                        "type": "noise",
                        "message": "No clear speech detected in chunk",
                        "language": asr_result.language,
                    }
                )
                continue

            with SessionLocal() as db:
                session = db.get(ClinicalSession, session_id)
                if not session or session.status != SessionStatus.active:
                    await websocket.send_json({"type": "error", "message": "Session is not active"})
                    break

                update = await run_in_threadpool(
                    clinical_pipeline.append_transcript_chunk,
                    db,
                    session,
                    asr_result.text,
                    asr_result.language,
                )
                response = PipelineUpdate.model_validate(asdict(update)).model_dump(mode="json")
                await websocket.send_json({"type": "update", **response})

                try:
                    structured_update = await run_in_threadpool(
                        clinical_pipeline.refresh_structured_data,
                        db,
                        session,
                    )
                    structured_response = PipelineUpdate.model_validate(asdict(structured_update)).model_dump(
                        mode="json"
                    )
                    await websocket.send_json({"type": "update", **structured_response})
                except Exception:
                    await websocket.send_json(
                        {
                            "type": "warning",
                            "message": "Transcript updated, but structured extraction is still processing.",
                        }
                    )
    except WebSocketDisconnect:
        return
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close()
