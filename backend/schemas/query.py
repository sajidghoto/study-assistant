# backend/schemas/query.py

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
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
    label:      str    # answer | explain | summarise | compare | quiz
    confidence: float  # 0.0 – 1.0


class Source(BaseModel):
    chunk_id:      str
    document_name: str
    text:          str
    score:         float
    chunk_index:   int


class QuizData(BaseModel):
    """Structured MCQ returned when intent is quiz."""
    question:       str
    options:        dict   # {"A": str, "B": str, "C": str, "D": str}
    correct_answer: str    # "A" | "B" | "C" | "D"
    explanation:    str


class QueryResponseData(BaseModel):
    intent:               IntentResult
    answer:               str | None       # None when intent is quiz
    quiz:                 QuizData | None  # None when intent is not quiz
    sources:              list[Source]
    query_document_scope: str
    not_found:            bool = False     # True when confidence gate fires


class QueryResponse(BaseModel):
    success: bool = True
    data:    QueryResponseData


class ErrorDetail(BaseModel):
    code:    str
    message: str
    detail:  str


class ErrorResponse(BaseModel):
    success: bool = False
    error:   ErrorDetail