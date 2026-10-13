"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing

DAYS = 30


def run(verbose: bool = True, existing_reserved_capacity: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        days = num(j["days"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * days * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        # Pass additional parameters for enhanced tier recommendation
        tier = pricing.recommend_tier(hpd, interruptible, gpu_type=gtype, job_days=int(days),
                                     existing_reserved_capacity=existing_reserved_capacity,
                                     reserved_discount=1 - num(c["reserved_1yr_hr"]) / od,
                                     spot_hr=num(c["spot_hr"]), on_demand_hr=od)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(
                gpu_hours, num(c["spot_hr"]), od,
                interrupt_rate=pricing.SPOT_INTERRUPTION_RATE.get(gtype, 0.05))
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            if existing_reserved_capacity:
                # Existing unused coverage: allocate only the sampled usage
                # at its amortized 1-year rate; not a new purchase.
                opt_cost = gpu_hours * num(c["reserved_1yr_hr"])
            else:
                # New commitment: pay the ENTIRE contracted term(s) regardless
                # of how few GPU-hours are used by this job.
                r1 = pricing.commitment_total_cost(
                    num(c["reserved_1yr_hr"]), 1, int(days), ngpu)
                r3 = pricing.commitment_total_cost(
                    num(c["reserved_3yr_hr"]), 3, int(days), ngpu)
                opt_cost = min(r1, r3)
                if opt_cost >= on_demand_cost:
                    tier, opt_cost = "on_demand", on_demand_cost
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"Reserved: {'existing unused coverage' if existing_reserved_capacity else 'new commitment requires >= 365 days'}")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")

    return {"recommendations": recs,
            "reserved_assumption": "existing unused coverage" if existing_reserved_capacity else "new commitment requires >=365 days",
            "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1)}


if __name__ == "__main__":
    run()
