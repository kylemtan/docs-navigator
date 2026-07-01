from fastapi import APIRouter

from app.models.schemas import QueryRequest, QueryResponse, SourceChunk
from app.services.generator import generate_answer
from app.services.retriever import retrieve

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    chunks = retrieve(library=request.library, question=request.question)
    answer = generate_answer(question=request.question, chunks=chunks)
    sources = [
        SourceChunk(page_url=c["page_url"], section=c["section"], text=c["text"])
        for c in chunks
    ]
    return QueryResponse(answer=answer, sources=sources)
