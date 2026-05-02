import logging
import pandas as pd
from pathlib import Path
from models.schemas import SupportTicket, TriageOutput

logger = logging.getLogger(__name__)


def load_tickets(csv_path: str) -> list[SupportTicket]:
    """Load support_tickets.csv → list of SupportTicket."""
    df = pd.read_csv(csv_path, encoding='utf-8')
    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    tickets = []
    for i, row in df.iterrows():
        try:
            company = str(row.get('company', '')).strip()
            if company.lower() in ('none', 'nan', ''):
                company = None

            ticket = SupportTicket(
                issue=str(row.get('issue', '')).strip(),
                subject=str(row.get('subject', '')).strip(),
                company=company,
            )
            tickets.append(ticket)
        except Exception as e:
            logger.warning(f"Skipping row {i}: {e}")

    logger.info(f"Loaded {len(tickets)} tickets from {csv_path}")
    return tickets


def write_outputs(outputs: list[TriageOutput], csv_path: str) -> None:
    """Write list of TriageOutput → output.csv."""
    rows = []
    for o in outputs:
        rows.append({
            'status': o.status,
            'product_area': o.product_area,
            'response': o.response,
            'justification': o.justification,
            'request_type': o.request_type,
        })

    df = pd.DataFrame(rows)
    output_path = Path(csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"Wrote {len(rows)} rows to {csv_path}")