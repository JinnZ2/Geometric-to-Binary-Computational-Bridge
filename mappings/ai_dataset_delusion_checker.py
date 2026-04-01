# ai_dataset_delusion_checker.py
# Detect common systemic assumptions in AI datasets

from collections import Counter
import re

# ---------------------------
# Define conceptual delusions
# ---------------------------
DELUSION_PATTERNS = {
    "hierarchy": [
        r"\btop[- ]?down\b", r"\bmanagement\b", r"\bchain of command\b"
    ],
    "corporation": [
        r"\bcompany\b", r"\bcorporation\b", r"\bshareholder\b"
    ],
    "efficiency": [
        r"\befficien(?:cy|t)\b", r"\bmaxim(?:ize|ization)\b"
    ],
    "optimization": [
        r"\boptimi[sz]e\b", r"\bperformance\b", r"\bthroughput\b"
    ],
    "productivity": [
        r"\bproductivit(?:y|ies)\b", r"\boutput\b", r"\bworkload\b"
    ]
}

# ---------------------------
# Extract and score delusions
# ---------------------------

def extract_delusions(text: str) -> Counter:
    """Return counts of conceptual delusions in a text."""
    text = text.lower()
    counts = Counter()
    for concept, patterns in DELUSION_PATTERNS.items():
        for pat in patterns:
            matches = re.findall(pat, text)
            counts[concept] += len(matches)
    return counts

# ---------------------------
# Analyze dataset
# ---------------------------

def analyze_dataset(dataset: list[str]) -> dict:
    """
    Input: list of text strings (e.g., dataset entries)
    Output: aggregated delusion counts
    """
    total_counts = Counter()
    for entry in dataset:
        total_counts += extract_delusions(entry)
    return dict(total_counts)

# ---------------------------
# Example usage
# ---------------------------

if __name__ == "__main__":
    sample_dataset = [
        "The company optimized its supply chain for maximum efficiency.",
        "Management insists on top-down decision making.",
        "Productivity increased through automation and performance tracking.",
        "The shareholder value was maximized through cost-cutting measures."
    ]

    result = analyze_dataset(sample_dataset)
    from pprint import pprint
    pprint(result)
