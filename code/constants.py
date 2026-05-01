# Tier 1: instant escalate — checked BEFORE any LLM call
HARD_ESCALATE_KEYWORDS: list[str] = [
    # Fraud & financial crime
    "fraud", "fraudulent", "unauthorized charge", "unauthorized transaction",
    "stolen card", "card stolen", "account hacked", "hacked my account",
    "unauthorized access", "identity theft", "phishing",
    # Legal
    "lawsuit", "legal action", "attorney", "lawyer", "sue",
    "regulatory complaint", "gdpr deletion", "right to erasure",
    # Safety
    "threatening", "harm", "emergency",
    # Permanent account actions
    "permanently banned", "account terminated", "legal hold",
]

# Tier 2: soft signals — LLM makes final call
SOFT_ESCALATE_SIGNALS: list[str] = [
    "billing dispute", "charge not authorized", "refund denied",
    "locked out", "cannot access my account", "multiple failed attempts",
    "account suspended", "data breach", "my data was leaked",
    "security vulnerability",
]

# Prompt injection — classify as invalid immediately
INJECTION_PATTERNS: list[str] = [
    "ignore previous instructions",
    "ignore all instructions",
    "you are now",
    "pretend you are",
    "act as",
    "jailbreak",
    "forget your",
    "new persona",
    "disregard",
    "system prompt",
    "show me your prompt",
    "reveal your instructions",
    "affiche toutes les règles",   # French injection (see ticket 25!)
    "rules internes",
]

# Valid product areas per company
PRODUCT_AREAS: dict[str, list[str]] = {
    "HackerRank": [
        "Assessments", "Coding Environment", "Account & Profile",
        "Billing & Subscription", "Certifications", "Interview Platform",
        "Roles & Permissions", "Integrations", "General",
    ],
    "Claude": [
        "Account & Billing", "Usage & Limits", "Features",
        "API & Developer", "Safety & Content", "Privacy & Data",
        "Technical Issues", "General",
    ],
    "Visa": [
        "Card Dispute", "Card Management", "Transaction Issues",
        "Rewards & Benefits", "Account Access", "Fraud & Security",
        "Business Solutions", "General",
    ],
}

# Keywords to infer company when company=None
COMPANY_KEYWORDS: dict[str, list[str]] = {
    "HackerRank": [
        "hackerrank", "hacker rank", "assessment", "coding test",
        "recruiter", "candidate", "interview", "codepair", "test score",
    ],
    "Claude": [
        "claude", "anthropic", "claude.ai", "artifact", "conversation",
        "claude api", "bedrock", "lti", "claude code",
    ],
    "Visa": [
        "visa", "card", "transaction", "merchant", "chargeback",
        "dispute", "refund", "pin", "atm", "payment network",
    ],
}