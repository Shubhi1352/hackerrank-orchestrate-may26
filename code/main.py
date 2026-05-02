import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from agent.orchestrator import TriageOrchestrator
from models.schemas import SupportTicket, TriageOutput
from utils.csv_handler import load_tickets, write_outputs
from corpus.index import get_index
from config import settings

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

console = Console()

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='HackerRank Orchestrate — Support Triage Agent')
    parser.add_argument('--input', default=settings.INPUT_CSV, help='Input CSV path')
    parser.add_argument('--output', default=settings.OUTPUT_CSV, help='Output CSV path')
    return parser.parse_args()


async def run_all(tickets: list[SupportTicket]) -> list[TriageOutput]:
    orchestrator = TriageOrchestrator()
    semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT)
    results: list[TriageOutput | None] = [None] * len(tickets)

    async def process_one(i: int, ticket: SupportTicket) -> None:
        async with semaphore:
            results[i] = await orchestrator.process(ticket)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Processing tickets..."),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("", total=len(tickets))

        async def process_and_update(i: int, ticket: SupportTicket) -> None:
            await process_one(i, ticket)
            progress.advance(task)
            await asyncio.sleep(2.0)  # gentle throttle between tickets

        await asyncio.gather(*[
            process_and_update(i, t)
            for i, t in enumerate(tickets)
        ])

    return [r for r in results if r is not None]


def print_summary(outputs: list[TriageOutput]) -> None:
    replied = sum(1 for o in outputs if o.status == "replied")
    escalated = sum(1 for o in outputs if o.status == "escalated")

    table = Table(title="Triage Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Total tickets", str(len(outputs)))
    table.add_row("Replied", str(replied))
    table.add_row("Escalated", str(escalated))

    type_counts: dict[str, int] = {}
    for o in outputs:
        type_counts[o.request_type] = type_counts.get(o.request_type, 0) + 1
    for rt, count in sorted(type_counts.items()):
        table.add_row(f"  {rt}", str(count))

    console.print(table)


def main() -> None:
    console.print("\n[bold green]🤖 HackerRank Orchestrate — Support Triage Agent[/bold green]\n")

    # Pre-load corpus index at startup (uses cache)
    console.print("[dim]Loading corpus index...[/dim]")
    get_index()
    console.print("[dim]Index ready.[/dim]\n")
    args = parse_args()

    # Load tickets
    tickets = load_tickets(args.input)
    console.print(f"[bold]Loaded {len(tickets)} tickets from:[/bold] {settings.INPUT_CSV}\n")

    # Process all tickets concurrently
    start = time.time()
    outputs = asyncio.run(run_all(tickets))
    elapsed = time.time() - start

    # Write output
    write_outputs(outputs, args.output)

    console.print(f"\n[bold green]✅ Done in {elapsed:.1f}s[/bold green]")
    console.print(f"[bold]Output written to:[/bold] {settings.OUTPUT_CSV}\n")
    print_summary(outputs)


if __name__ == "__main__":
    main()