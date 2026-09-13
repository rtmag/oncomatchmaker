"""Report-brand hints only; never infer specimen or diagnosis from vendor."""

import re


def classify_report(text):
    rules = [
        ("Foundation Medicine", r"FoundationOne|Foundation Medicine"),
        ("Tempus", r"Tempus"),
        ("Caris", r"Caris"),
        ("TSO500/PierianDx", r"TruSight Oncology|TSO\s*500|PierianDx"),
    ]
    vendors = [name for name, pattern in rules if re.search(pattern, text, re.I)]
    return {
        "vendor": vendors[0] if len(vendors) == 1 else "UNKNOWN",
        "candidates": vendors,
    }
