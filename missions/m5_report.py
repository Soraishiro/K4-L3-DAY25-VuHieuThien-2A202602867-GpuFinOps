"""M5: explicitly conditional savings across synthetic cost scenarios.

API invoices, purchasing jobs and telemetry GPUs have no shared billing IDs:
their independence is unverified. Combined savings are a hypothetical upper
scenario, not a guaranteed saving or a reconciled billing forecast.
Within telemetry, remove idle hours from right-sizing to avoid double count.
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import os
from missions._common import ROOT
from finops import report, sustainability
from missions import m1_efficiency_audit, m2_inference_levers, m3_purchasing

DAYS = 30


def run(verbose: bool = True) -> dict:
    r1 = m1_efficiency_audit.run(verbose=False)
    r2 = m2_inference_levers.run(verbose=False)
    r3 = m3_purchasing.run(verbose=False)

    inference_savings = round((r2["baseline_daily"] - r2["optimized_daily"]) * DAYS)
    purchasing_savings = r3["on_demand_monthly"] - r3["optimized_monthly"]
    rightsize_savings = sum(s["monthly_savings"] for s in r1["right_size_suggestions"])
    idle_savings = round(r1["idle_waste_daily"] * DAYS)
    levers = {
        "Inference (routing/cache/batch)": inference_savings,
        "Purchasing (spot/covered reserved)": purchasing_savings,
        "GPU replacement candidates (unverified)": rightsize_savings,
        "Idle-hours opportunity": idle_savings,
    }
    baseline = r2["baseline_daily"] * DAYS + r3["on_demand_monthly"]
    scenario_savings = sum(levers.values())
    optimized = baseline - scenario_savings
    pct = scenario_savings / baseline * 100 if baseline else 0.0

    wh = sustainability.wh_per_query(800)
    sust = {
        "wh_per_query": wh,
        "carbon_g": sustainability.carbon_g(wh, "us-east-1"),
        "cleanest_region": min(sustainability.REGION_CARBON,
                               key=sustainability.REGION_CARBON.get),
        "cheapest_region": min(sustainability.REGION_PRICE_KWH,
                              key=sustainability.REGION_PRICE_KWH.get),
    }
    notes = [
        "All source data are synthetic. No real provider savings have occurred.",
        "Combined scenario assumes external token billing, GPU job costs and telemetry fleet do not overlap; their independence has NOT been proven.",
        "No linkage connects the 11 telemetry GPUs to the eight purchasing jobs; exclude cross-ledger savings until billing can be reconciled.",
        "Right-sizing is capacity screening, not a performance-validated replacement. Remove idle hours before estimating right-size savings.",
        "Reserved pricing assumes existing unused committed capacity; 30-day jobs alone cannot justify new one-year commitments.",
        "Purchasing-only scenario: USD {:,.0f} to USD {:,.0f} ({}% saving).".format(
            r3["on_demand_monthly"], r3["optimized_monthly"], r3["savings_pct"]),
    ]
    md = report.build_report(baseline, optimized, levers, sustainability=sust,
                             inference_metrics=r2, assumptions=notes)
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    with open(os.path.join(ROOT, "outputs", "report.md"), "w", encoding="utf-8") as f:
        f.write(md)
    chart = report.savings_waterfall(levers, os.path.join(ROOT, "outputs", "savings.png"),
                                     baseline_usd=baseline)
    if verbose:
        print("== M5 Conditional Optimization Scenario ==")
        print(md)
        print("Written: outputs/report.md" + (" + outputs/savings.png" if chart else ""))
    return {
        "baseline_monthly": round(baseline), "optimized_monthly": round(optimized),
        "levers": levers, "total_savings_pct": round(pct, 1),
        "scenario_only": True,
    }


if __name__ == "__main__":
    run()
