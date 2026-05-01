from pydantic import BaseModel, field_validator, model_validator
from typing import Literal, Optional

class SupportTicket(BaseModel):
    """One input row from support_tickets.csv"""
    issue: str
    subject: Optional[str] = ""
    company: Optional[str] = None  # "HackerRank" | "Claude" | "Visa" | "None" | None

    @model_validator(mode="after")
    def normalize_company(self) -> "SupportTicket":
        # CSV sometimes has "None" as string — normalize to Python None
        if self.company in ("None", "none", "", " "):
            self.company = None
        return self


class TriageOutput(BaseModel):
    """One output row for output.csv — field names must match exactly"""
    status: Literal["replied", "escalated"]
    request_type: Literal["product_issue", "feature_request", "bug", "invalid"]
    product_area: str
    response: str  # must be "" if escalated
    justification: str

    @field_validator("response", mode="before")
    @classmethod
    def empty_response_if_escalated(cls, v: str, info) -> str:
        if info.data.get("status") == "escalated":
            return ""
        return v


class RetrievedChunk(BaseModel):
    """A single chunk returned by the retriever"""
    content: str
    source: str    # filename in corpus
    score: float
    company: str


class ClassificationResult(BaseModel):
    """Output of Stage 3 — IntentClassifier"""
    request_type: Literal["product_issue", "feature_request", "bug", "invalid"]
    product_area: str
    risk_level: Literal["low", "medium", "high"]
    resolved_company: str   # company we determined (even if input was None)
    primary_issue: str      # cleaned, one-sentence summary


class TicketContext(BaseModel):
    """Full context passed between pipeline stages"""
    ticket: SupportTicket
    is_malicious: bool = False
    resolved_company: str = ""
    classification: Optional[ClassificationResult] = None
    chunks: list[RetrievedChunk] = []
    escalation_reason: str = ""