# backend/schemas/query.py
#
# Pydantic models for the query endpoint.
# QueryRequest validates what the frontend sends.
# QueryResponse defines exactly what the frontend receives.

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    Body for POST /session/{session_id}/query.

    document_id is optional:
      - None   → search across ALL documents in session (default)
      - string → filter retrieval to that specific document only
    """
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The student's natural language question"
    )
    document_id: str | None = Field(
        default=None,
        description="If set, restricts retrieval to this document only"
    )


class IntentResult(BaseModel):
    """Classifier output: detected intent label and confidence score."""
    label:      str    # "answer" | "summarise" | "out-of-scope"
    confidence: float  # 0.0 – 1.0


class Source(BaseModel):
    """A single retrieved chunk returned alongside the answer."""
    chunk_id:      str
    document_name: str
    text:          str
    score:         float  # cosine similarity: 0.0 – 1.0
    chunk_index:   int


class QueryResponseData(BaseModel):
    """The 'data' payload inside a successful query response."""
    intent:               IntentResult
    answer:               str
    sources:              list[Source]
    query_document_scope: str  # "all" | document_name if filtered


class QueryResponse(BaseModel):
    """Full query response envelope."""
    success: bool = True
    data:    QueryResponseData


class ErrorDetail(BaseModel):
    """Structured error returned on failure."""
    code:    str
    message: str
    detail:  str


class ErrorResponse(BaseModel):
    """Standard error envelope used for all 4xx and 5xx responses."""
    success: bool = False
    error:   ErrorDetail