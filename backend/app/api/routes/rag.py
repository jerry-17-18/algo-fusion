from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_doctor, get_db
from app.models.user import User
from app.schemas.record import RAGAnswer, RAGQueryRequest
from app.services.runtime import rag_service

router = APIRouter()


@router.post("/query", response_model=RAGAnswer)
def query_rag(
    payload: RAGQueryRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_doctor),
) -> RAGAnswer:
    return rag_service.answer_question(
        db=db,
        question=payload.question,
        patient_id=payload.patient_id,
        top_k=payload.top_k,
    )

