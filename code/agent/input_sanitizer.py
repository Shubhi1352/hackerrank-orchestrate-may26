import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import SupportTicket, TicketContext
from constants import INJECTION_PATTERNS

logger = logging.getLogger(__name__)


def sanitize(ticket: SupportTicket) -> TicketContext:
    """
    Stage 1: Detect prompt injection and malicious input.
    Runs BEFORE any LLM call — purely rule-based, instant.
    If malicious → mark context, pipeline short-circuits to invalid reply.
    """
    combined = f"{ticket.subject or ''} {ticket.issue}".lower()

    for pattern in INJECTION_PATTERNS:
        if pattern.lower() in combined:
            logger.warning(f"Injection detected: '{pattern}' in ticket")
            return TicketContext(
                ticket=ticket,
                is_malicious=True,
                resolved_company=ticket.company or "Unknown",
                escalation_reason=f"Prompt injection detected: '{pattern}'",
            )

    # Check for completely empty or nonsensical input
    issue_clean = ticket.issue.strip()
    if len(issue_clean) < 10:
        logger.info("Ticket too short to process")
        return TicketContext(
            ticket=ticket,
            is_malicious=True,
            resolved_company=ticket.company or "Unknown",
            escalation_reason="Issue too short or empty to process",
        )

    return TicketContext(
        ticket=ticket,
        is_malicious=False,
        resolved_company=ticket.company or "",
    )