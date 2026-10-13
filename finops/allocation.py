"""Cost allocation — turn a shared GPU bill into per-team accountability.

Maturity ladder (deck §10): visibility -> showback -> chargeback. Only enforce
chargeback once tag coverage is high enough (~>80%), else you bill noise.
"""
from __future__ import annotations
from collections import defaultdict


def cost_by_tag(rows, dim: str, cost_key: str = "cost") -> dict:
    """Sum cost grouped by a tag dimension (e.g. 'team' or 'project')."""
    out: dict = defaultdict(float)
    for r in rows:
        key = r.get(dim) or "(untagged)"
        out[key] += float(r.get(cost_key, 0.0))
    return dict(out)


def tag_coverage(rows, tag_keys) -> float:
    """Fraction of rows where every required tag is present and non-empty (0..1)."""
    rows = list(rows)
    if not rows:
        return 0.0
    tagged = 0
    for r in rows:
        if all(str(r.get(k, "")).strip() not in ("", "(untagged)", "nan", "None") for k in tag_keys):
            tagged += 1
    return tagged / len(rows)


def chargeback_ready(coverage: float, threshold: float = 0.80) -> bool:
    """Enforce chargeback only once tag coverage clears the threshold."""
    return coverage >= threshold


def to_focus_rows(rows, period_start: str = "2026-06-01", billing_account: str = "nimbusai-prod") -> list:
    """FOCUS-inspired synthetic records, NOT a certified FOCUS 1.2 export.

    Real invoice, contractual and amortization fields cannot be inferred
    from token usage alone. Do not mistake simulated amounts for billed costs.
    """
    from datetime import datetime, timedelta
    focus = []
    for idx, r in enumerate(rows):
        start = str(r.get("ts", period_start + "T00:00:00"))
        if "T" not in start:
            start += "T00:00:00"
        end = (datetime.fromisoformat(start) + timedelta(minutes=1)).isoformat()
        cost = round(float(r.get("cost", 0)), 8)
        focus.append({
            "BillingAccountId": billing_account, "BillingAccountName": "NimbusAI (simulated)",
            "BillingPeriodStart": period_start + "T00:00:00",
            "BillingPeriodEnd": "2026-07-01T00:00:00",
            "ChargePeriodStart": start, "ChargePeriodEnd": end,
            "ChargeCategory": "Usage", "ServiceCategory": "AI and Machine Learning",
            "ServiceName": r.get("service", "gpu-inference"),
            "ResourceId": r.get("resource_id") or f"simulated-request-{idx:04d}",
            "BilledCost": cost, "EffectiveCost": cost,
            "ContractedCost": cost, "ListCost": cost, "BillingCurrency": "USD",
            "Provider": "NimbusAI (simulated)", "InvoiceIssuer": "NimbusAI (simulated)",
            "Tags": {"team": r.get("team", ""), "project": r.get("project", "")},
        })
    return focus
