"""M1 — Efficiency Audit: MFU/MBU, the GPU-Util lie, and idle waste (deck §5).

Run: python missions/m1_efficiency_audit.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from collections import defaultdict
from missions._common import load_csv, num, catalog_by_type
from finops import metrics


def run(verbose: bool = True) -> dict:
    tel = load_csv("gpu_telemetry.csv")
    cat = catalog_by_type()

    # per-row MFU/MBU, then aggregate per GPU
    agg = defaultdict(lambda: {"util": [], "mfu": [], "mbu": [], "type": None, "idle_hours": 0, "memory": [], "achieved_flops": [], "achieved_bw": []})
    for r in tel:
        gtype = r["gpu_type"]
        peak_fp16 = num(cat[gtype]["peak_tflops_fp16"])
        peak_bw = num(cat[gtype]["peak_bw_tbs"])
        mfu = metrics.compute_mfu(num(r["achieved_tflops"]), peak_fp16)
        mbu = metrics.compute_mbu(num(r["achieved_bw_tbs"]), peak_bw)
        a = agg[r["gpu_id"]]
        a["type"] = gtype
        a["util"].append(num(r["gpu_util_pct"]))
        a["mfu"].append(mfu)
        a["mbu"].append(mbu)
        a["memory"].append(num(r["mem_used_gb"]))
        a["achieved_flops"].append(num(r["achieved_tflops"]))
        a["achieved_bw"].append(num(r["achieved_bw_tbs"]))
        if num(r["gpu_util_pct"]) < 10:  # effectively idle this interval (1h)
            a["idle_hours"] += 1

    summary = []
    for gid, a in agg.items():
        summary.append({
            "gpu_id": gid, "gpu_type": a["type"],
            "gpu_util_pct": round(sum(a["util"]) / len(a["util"]), 1),
            "mfu": round(sum(a["mfu"]) / len(a["mfu"]), 3),
            "mbu": round(sum(a["mbu"]) / len(a["mbu"]), 3),
            "idle_hours": a["idle_hours"],
            "memory_p95_gb": sorted(a["memory"])[int(0.95 * (len(a["memory"]) - 1))],
            "observed_flops": max(a["achieved_flops"]),
            "observed_bw": max(a["achieved_bw"]),
        })

    # Extension 2: screening candidates, not performance-validated replacements.
    # Low MBU alone does not establish a memory-bound workload. Require
    # sufficient VRAM, observed FLOPs and bandwidth with 10% headroom.
    right_size_suggestions = []
    for gpu in summary:
        if gpu["mfu"] >= 0.30 or not (gpu["gpu_util_pct"] >= 90 or gpu["idle_hours"] > 0):
            continue
        old = cat[gpu["gpu_type"]]
        old_hr = num(old["on_demand_hr"])
        candidates = []
        for gpu_type, candidate in cat.items():
            new_hr = num(candidate["on_demand_hr"])
            if gpu_type == gpu["gpu_type"] or new_hr >= old_hr:
                continue
            if num(candidate["hbm_gb"]) < 1.1 * gpu["memory_p95_gb"]:
                continue
            if num(candidate["peak_tflops_fp16"]) < 1.1 * gpu["observed_flops"]:
                continue
            if num(candidate["peak_bw_tbs"]) < 1.1 * gpu["observed_bw"]:
                continue
            candidates.append((new_hr / num(candidate["hbm_gb"]), gpu_type))
        if not candidates:
            continue
        _, replacement = min(candidates)
        active_hours = (24 - gpu["idle_hours"]) * 30
        right_size_suggestions.append({
            "gpu_id": gpu["gpu_id"], "current_gpu": gpu["gpu_type"],
            "proposed_gpu": replacement, "mbu": gpu["mbu"],
            "active_hours_month": active_hours,
            "monthly_savings": round((old_hr - num(cat[replacement]["on_demand_hr"])) * active_hours),
            "reason": "Screened by memory/FLOPs/bandwidth; benchmark and CUDA/ROCm compatibility required",
        })

    lies = metrics.flag_util_lies(summary)
    idle_waste = 0.0
    for s in summary:
        on_demand = num(catalog_by_type()[s["gpu_type"]]["on_demand_hr"])
        idle_waste += metrics.idle_waste_usd(s["idle_hours"], on_demand)

    if verbose:
        print("== M1 Efficiency Audit ==")
        print(f"{'GPU':14}{'type':7}{'util%':>7}{'MFU':>7}{'MBU':>7}{'idle_h':>8}")
        for s in sorted(summary, key=lambda x: x["mfu"]):
            print(f"{s['gpu_id']:14}{s['gpu_type']:7}{s['gpu_util_pct']:>7}{s['mfu']:>7}{s['mbu']:>7}{s['idle_hours']:>8}")
        print(f"\nGPU-Util LIES (util>=90% but MFU<30%): {[l['gpu_id'] for l in lies]}")
        print(f"Idle waste (1 day): ${idle_waste:,.2f}  ->  ${idle_waste*30:,.0f}/month")
        
        if right_size_suggestions:
            print(f"\n=== RIGHT-SIZING SUGGESTIONS (Memory-bound workloads) ===")
            print(f"{'GPU':14}{'Current':>10}{'Proposed':>10}{'MBU':>6}{'Monthly Savings':>16}{'Reason'}")
            for s in right_size_suggestions:
                print(f"{s['gpu_id']:14}{s['current_gpu']:>10}{s['proposed_gpu']:>10}{s['mbu']:>6.2f}{s['monthly_savings']:>16,.0f}{s['reason']}")

    return {
        "summary": summary, 
        "lies": lies, 
        "idle_waste_daily": round(idle_waste, 2),
        "right_size_suggestions": right_size_suggestions
    }


if __name__ == "__main__":
    run()
