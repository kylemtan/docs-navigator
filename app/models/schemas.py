from pydantic import BaseModel


class QueryRequest(BaseModel):
    library: str
    question: str


class SourceChunk(BaseModel):
    page_url: str
    section: str
    text: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
