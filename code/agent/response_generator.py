import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import TicketContext, RetrievedChunk
from utils.llm import gemini_text_call

logger = logging.getLogger(__name__)

INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"

RESPONSE_PROMPT = """Support agent for {company}. Answer using ONLY these docs. 
If docs don't cover it, reply: INSUFFICIENT_CONTEXT

Docs:
{chunks}

Issue: {issue}

Reply in 2-3 sentences max. Be direct and helpful."""

OUT_OF_SCOPE_RESPONSE = (
    "Thank you for reaching out. Your query appears to be outside the scope "
    "of our support services for {company}. We handle support related to "
    "{company} products and services only. For this type of request, we "
    "recommend contacting the appropriate service provider. If you have a "
    "{company}-related question, we're happy to help!"
)


async def generate_response(context: TicketContext) -> tuple[str, str]:
    """
    Stage 6: Generate grounded response using Gemini.
    Returns (response_text, justification).
    Returns ("", justification) if INSUFFICIENT_CONTEXT → caller escalates.
    """
    company = context.resolved_company or "Unknown"
    classification = context.classification

    # Handle invalid/out-of-scope tickets without LLM call
    if classification and classification.request_type == "invalid":
        response = OUT_OF_SCOPE_RESPONSE.format(company=company)
        justification = (
            f"Ticket classified as invalid/out-of-scope for {company}. "
            f"Primary issue: {classification.primary_issue[:100]}"
        )
        return response, justification

    # Build chunks text for prompt
    if not context.chunks:
        return "", "No relevant corpus chunks found — cannot generate grounded response"

    chunks_text = "\n\n---\n\n".join([
        f"[Source: {c.source}]\n{c.content}"
        for c in context.chunks
    ])

    primary_issue = (
        classification.primary_issue
        if classification else context.ticket.issue[:300]
    )

    prompt = RESPONSE_PROMPT.format(
        company=company,
        chunks=chunks_text,
        issue=primary_issue,
    )

    response = await gemini_text_call(prompt)

    if not response:
        return "", "Gemini call failed — escalating to human agent"

    if INSUFFICIENT_CONTEXT in response:
        return "", f"Gemini returned INSUFFICIENT_CONTEXT for: {primary_issue[:100]}"

    justification = (
        f"Responded using {len(context.chunks)} corpus chunk(s) from "
        f"{company} documentation. "
        f"request_type={classification.request_type if classification else 'unknown'}, "
        f"product_area={classification.product_area if classification else 'unknown'}"
    )

    return response, justification