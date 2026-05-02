# HackerRank Orchestrate — Support Triage Agent

A multi-stage AI pipeline that triages support tickets across HackerRank, Claude, and Visa using hybrid RAG architecture.

## Architecture
Input Ticket
↓
[Stage 1] Input Sanitizer     — Prompt injection detection (rule-based, no LLM)
↓
[Stage 2] Company Resolver    — Keyword-based company inference for company=None tickets
↓
[Stage 3] Escalation Gate T1  — Hard keyword rules (fraud/legal/safety) → instant escalate
↓
[Stage 4] Corpus Retriever    — TF-IDF top-20 → Sentence-transformer semantic rerank top-3
↓
[Stage 5] Combined Classifier — Single Groq/OpenRouter call: classify + generate response
↓
[Stage 6] Output Validator    — Pydantic v2 enforces exact field values
↓
output.csv

## Key Design Decisions

**Why two-stage retrieval?** TF-IDF catches keyword matches fast; sentence-transformers catch semantic matches (e.g. "card compromised" → "unauthorized access"). Together they give precision neither achieves alone.

**Why rule-based escalation before LLM?** Fraud/legal/safety tickets are escalated instantly via keyword rules — zero LLM cost, zero hallucination risk on sensitive cases.

**Why single combined LLM call?** Reduces API calls from 2 per ticket to 1, staying within free tier rate limits while maintaining quality.

**Anti-hallucination:** Three layers — (1) minimum relevance score threshold before generation, (2) LLM instructed to return INSUFFICIENT_CONTEXT if docs don't cover the issue, (3) Pydantic validation rejects malformed outputs.

## Setup

```bash
cd code
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env
```

Required keys in `.env`:
GROQ_API_KEY=your_groq_key        # https://console.groq.com (free)
OPENROUTER_API_KEY=your_key       # https://openrouter.ai (free)

## Run

```bash
cd code
python main.py
```

Processes all tickets in `support_tickets/support_tickets.csv` and writes `support_tickets/output.csv`.

First run builds the TF-IDF index (~2s) and downloads the sentence-transformer model (~80MB, cached). Subsequent runs use cached index.

## Tech Stack

| Component | Choice | Why |
|---|---|---|
| Classification + Generation | Groq Llama 3.3 70B / OpenRouter Gemma 31B | Free tier, fast, reliable |
| Retrieval Stage 1 | scikit-learn TF-IDF | Fast, local, cached to disk |
| Retrieval Stage 2 | sentence-transformers all-MiniLM-L6-v2 | Semantic reranking, CPU-friendly |
| Validation | Pydantic v2 | Enforces exact output field values |
| Config | pydantic-settings | Secrets from env vars only |

## Output Format

| Field | Values |
|---|---|
| `status` | `replied` or `escalated` |
| `request_type` | `product_issue`, `feature_request`, `bug`, `invalid` |
| `product_area` | Company-specific support category |
| `response` | Grounded answer (empty if escalated) |
| `justification` | Internal reasoning trace |