import logging
import sys
from pathlib import Path
from agent.escalation_gate import check_escalation
from agent.retriever import retrieve

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import SupportTicket, TriageOutput, TicketContext
from agent.input_sanitizer import sanitize
from agent.company_resolver import resolve_company
from agent.intent_classifier import classify
from agent.escalation_gate import check_escalation
from agent.retriever import retrieve
from agent.response_generator import generate_response
from config import settings

logger = logging.getLogger(__name__)

MALICIOUS_RESPONSE = (
    "We were unable to process your request as it appears to contain "
    "content that violates our support policies. Please submit a new "
    "ticket with a clear description of your issue."
)


class TriageOrchestrator:
    """
    Coordinates all pipeline stages for a single ticket.
    Stateless — safe to use concurrently across many tickets.
    """

    async def process(self, ticket: SupportTicket) -> TriageOutput:
        try:
            return await self._process_inner(ticket)
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return TriageOutput(
                status="escalated",
                request_type="product_issue",
                product_area="General",
                response="",
                justification=f"Pipeline error: {str(e)[:200]}",
            )

    async def _process_inner(self, ticket: SupportTicket) -> TriageOutput:

        # Stage 1: Input sanitization
        ctx: TicketContext = sanitize(ticket)
        if ctx.is_malicious:
            return TriageOutput(
                status="replied",
                request_type="invalid",
                product_area="General",
                response=MALICIOUS_RESPONSE,
                justification=ctx.escalation_reason,
            )

        # Stage 2: Company resolution
        ctx = resolve_company(ctx)

        # Stage 3: Tier 1 escalation (rule-based, no LLM)
        ctx = check_escalation(ctx)
        if ctx.escalation_reason:
            return TriageOutput(
                status="escalated",
                request_type="product_issue",
                product_area="General",
                response="",
                justification=ctx.escalation_reason,
            )

        # Stage 4: Retrieve corpus chunks
        combined_query = f"{ticket.subject or ''} {ticket.issue}"[:500]
        company_filter = ctx.resolved_company if ctx.resolved_company != "Unknown" else None
        ctx.chunks = retrieve(combined_query, company=company_filter)

        # Stage 5: Single LLM call — classify + generate together
        from agent.combined_classifier import classify_and_respond
        result = await classify_and_respond(ctx)

        if result.get("should_escalate"):
            return TriageOutput(
                status="escalated",
                request_type=result.get("request_type", "product_issue"),
                product_area=result.get("product_area", "General"),
                response="",
                justification=result.get("escalate_reason", "Escalated by agent"),
            )

        response = result.get("response", "")
        if not response:
            return TriageOutput(
                status="escalated",
                request_type=result.get("request_type", "product_issue"),
                product_area=result.get("product_area", "General"),
                response="",
                justification="No grounded response could be generated",
            )

        return TriageOutput(
            status="replied",
            request_type=result.get("request_type", "product_issue"),
            product_area=result.get("product_area", "General"),
            response=response,
            justification=(
                f"Classified as {result.get('request_type')} | "
                f"Risk: {result.get('risk_level')} | "
                f"Primary: {result.get('primary_issue', '')[:100]}"
            ),
        )