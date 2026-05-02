import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import TicketContext
from constants import HARD_ESCALATE_KEYWORDS, SOFT_ESCALATE_SIGNALS

logger = logging.getLogger(__name__)


def _check_tier1(context: TicketContext) -> str:
    """
    Tier 1: Deterministic keyword rules. No LLM needed.
    Returns escalation reason string if should escalate, else empty string.
    """
    combined = f"{context.ticket.subject or ''} {context.ticket.issue}".lower()

    for keyword in HARD_ESCALATE_KEYWORDS:
        if keyword.lower() in combined:
            return f"Hard escalation keyword detected: '{keyword}'"

    return ""


def _check_tier2(context: TicketContext) -> str:
    combined = f"{context.ticket.subject or ''} {context.ticket.issue}".lower()

    # Vague "site is down" type reports — can't answer without more info
    vague_patterns = [
        "site is down",
        "nothing is working", 
        "everything is broken",
        "can't access anything",
        "pages are not accessible",
        "none of the pages",
    ]
    for pattern in vague_patterns:
        if pattern in combined:
            return f"Vague outage report — insufficient detail to answer safely: '{pattern}'"

    for signal in SOFT_ESCALATE_SIGNALS:
        if signal.lower() in combined:
            if context.classification and context.classification.risk_level == "high":
                return f"Soft escalation signal + high risk: '{signal}'"

    if context.classification and context.classification.risk_level == "high":
        issue_len = len(context.ticket.issue.strip())
        if issue_len < 50:
            return "High risk ticket with insufficient detail"

    return ""


def check_escalation(context: TicketContext) -> TicketContext:
    """
    Escalation Gate — two tiers:
    Tier 1: instant rule-based (fraud/legal/safety keywords)
    Tier 2: risk-based (high risk + soft signals)

    If escalated: sets escalation_reason, pipeline skips retrieval+generation.
    If not escalated: context passes through unchanged.
    """
    # Tier 1 — always check first, no LLM needed
    reason = _check_tier1(context)
    if reason:
        logger.info(f"Tier 1 escalation: {reason}")
        context.escalation_reason = reason
        return context

    # Tier 2 — soft signals + classification risk
    reason = _check_tier2(context)
    if reason:
        logger.info(f"Tier 2 escalation: {reason}")
        context.escalation_reason = reason
        return context

    logger.debug("No escalation triggered")
    return context