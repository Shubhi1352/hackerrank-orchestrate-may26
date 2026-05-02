import json
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import TicketContext, ClassificationResult
from constants import PRODUCT_AREAS
from utils.llm import groq_json_call

logger = logging.getLogger(__name__)

COMBINED_PROMPT = """You are a support triage agent. Analyze this ticket and return ONLY valid JSON.

Company: {company}
Valid product areas: {product_areas}
Subject: {subject}
Issue: {issue}

Return ONLY this JSON:
{{
  "request_type": "product_issue" | "feature_request" | "bug" | "invalid",
  "product_area": "<one of the valid areas above>",
  "risk_level": "low" | "medium" | "high",
  "primary_issue": "<one sentence summary>",
  "should_escalate": true | false,
  "escalate_reason": "<reason if escalating, else empty string>",
  "response": "<if not escalating: 2-3 sentence helpful response grounded only in the docs below. If escalating: empty string>"
}}

Support docs:
{chunks}

Rules:
- should_escalate=true ONLY for: fraud, legal threats, account hacked, safety threats, truly vague issues
- should_escalate=false for: FAQ, how-to, feature questions, out-of-scope (just mark invalid)  
- invalid = off-topic, spam, thank you messages, celebrity questions, nonsensical
- response must be grounded in the support docs above, not invented
- If docs don't cover the issue → should_escalate=true
- high risk = fraud/legal/hacked; medium = payment/access issues; low = everything else

Return ONLY the JSON."""


async def classify_and_respond(context: TicketContext) -> dict:
    """Single LLM call that classifies AND generates response."""
    company = context.resolved_company or "Unknown"
    product_areas = PRODUCT_AREAS.get(company, ["General"])

    chunks_text = ""
    # Build chunks text — no backslash in f-string (Python 3.11 fix)
    if context.chunks:
        chunk_parts = []
        for c in context.chunks[:3]:
            source_name = c.source.replace('\\', '/').split('/')[-1]
            chunk_parts.append(f"[{source_name}]\n{c.content}")
        chunks_text = "\n\n".join(chunk_parts)
    else:
        chunks_text = "No specific documentation found for this query."

    prompt = COMBINED_PROMPT.format(
        company=company,
        product_areas=", ".join(product_areas),
        subject=context.ticket.subject or "(none)",
        issue=context.ticket.issue[:800],
        chunks=chunks_text[:2000],
    )

    result = await groq_json_call(prompt)

    if not result:
        return {
            "request_type": "product_issue",
            "product_area": "General",
            "risk_level": "medium",
            "primary_issue": context.ticket.issue[:100],
            "should_escalate": True,
            "escalate_reason": "Classification failed",
            "response": ""
        }

    # Validate
    valid_types = {"product_issue", "feature_request", "bug", "invalid"}
    if result.get("request_type") not in valid_types:
        result["request_type"] = "product_issue"

    return result