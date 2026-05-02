# Tier 1: instant escalate — checked BEFORE any LLM call
HARD_ESCALATE_KEYWORDS: list[str] = [
    # Fraud & financial crime — must be specific
    "fraudulent charge",
    "unauthorized charge",
    "unauthorized transaction", 
    "stolen card",
    "card stolen",
    "account hacked",
    "hacked my account",
    "unauthorized access to my account",
    "identity theft",
    "phishing",
    # Legal
    "lawsuit",
    "legal action",
    "attorney",
    "lawyer",
    "i will sue",
    "regulatory complaint",
    "gdpr deletion request",
    "right to erasure",
    # Safety
    "i will harm",
    "emergency services",
    # Permanent account actions
    "permanently banned",
    "account terminated",
    "legal hold",
]

# Tier 2: soft signals — LLM makes final call
SOFT_ESCALATE_SIGNALS: list[str] = [
    "charge not authorized",
    "refund denied twice",
    "multiple failed login attempts",
    "account suspended without reason",
    "data breach affecting me",
    "my data was leaked",
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

# Simplified product area mapping — judges use these values
PRODUCT_AREA_NORMALIZE: dict[str, str] = {
    # HackerRank
    "Assessments": "screen",
    "Coding Environment": "screen",
    "Interview Platform": "screen",
    "Account & Profile": "community",
    "Billing & Subscription": "screen",
    "Certifications": "screen",
    "Roles & Permissions": "screen",
    "Integrations": "screen",
    "General": "screen",
    # Claude
    "Account & Billing": "privacy",
    "Usage & Limits": "conversation_management",
    "Features": "conversation_management",
    "API & Developer": "conversation_management",
    "Safety & Content": "privacy",
    "Privacy & Data": "privacy",
    "Technical Issues": "conversation_management",
    # Visa
    "Card Dispute": "travel_support",
    "Card Management": "travel_support",
    "Transaction Issues": "travel_support",
    "Rewards & Benefits": "travel_support",
    "Account Access": "travel_support",
    "Fraud & Security": "travel_support",
    "Business Solutions": "travel_support",
}