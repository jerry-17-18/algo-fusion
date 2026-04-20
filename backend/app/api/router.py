from fastapi import APIRouter

from app.api.routes import auth, patients, rag, records, sessions, websocket

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(records.router, prefix="/records", tags=["records"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])

