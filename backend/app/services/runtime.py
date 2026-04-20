from app.services.asr import ASRService
from app.services.clinical_pipeline import ClinicalPipelineService
from app.services.extraction import ClinicalLLMService
from app.services.rag import RAGService

llm_service = ClinicalLLMService()
asr_service = ASRService()
clinical_pipeline = ClinicalPipelineService(llm_service=llm_service)
rag_service = RAGService(llm_service=llm_service)

