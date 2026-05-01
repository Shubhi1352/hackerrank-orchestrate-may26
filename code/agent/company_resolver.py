import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import TicketContext
from constants import COMPANY_KEYWORDS

logger = logging.getLogger(__name__)

VALID_COMPANIES = {"HackerRank", "Claude", "Visa"}


def resolve_company(context: TicketContext) -> TicketContext:
    """
    Stage 2: Resolve company=None tickets by keyword matching.
    If company already set and valid → pass through unchanged.
    If None → score each company by keyword hits → pick winner.
    If no clear winner → default to 'Unknown' (will use all corpus).
    """
    company = context.ticket.company

    # Already resolved and valid
    if company in VALID_COMPANIES:
        context.resolved_company = company
        return context

    # Need to infer from issue + subject
    combined = f"{context.ticket.subject or ''} {context.ticket.issue}".lower()

    scores: dict[str, int] = {c: 0 for c in VALID_COMPANIES}
    for company_name, keywords in COMPANY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in combined:
                scores[company_name] += 1

    best = max(scores, key=lambda k: scores[k])

    if scores[best] > 0:
        logger.info(f"Company resolved: None → {best} (score={scores[best]})")
        context.resolved_company = best
    else:
        logger.info("Company unresolved — using 'Unknown'")
        context.resolved_company = "Unknown"

    return context