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
    agg = defaultdict(lambda: {"util": [], "mfu": [], "mbu": [], "type": None, "idle_hours": 0})
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
        })

    # --- Extension 2: Right-sizing based on MBU (memory-bound workloads) ---
    cat = catalog_by_type()
    right_size_suggestions = []
    
    # Calculate $/GB-VRAM cost for each GPU type
    cost_by_gb_vram = {}
    for gtype, data in cat.items():
        hbm_gb = num(data["hbm_gb"])
        on_demand_hr = num(data["on_demand_hr"])
        if hbm_gb > 0:
            cost_by_gb_vram[gtype] = on_demand_hr / hbm_gb
        else:
            cost_by_gb_vram[gtype] = float('inf')
    
    # Sort GPUs by cost efficiency (lower is better)
    sorted_gpus = sorted(cost_by_gb_vram.items(), key=lambda x: x[1] if x[1] != float('inf') else float('inf'))
    
    for s in summary:
        gtype = s["gpu_type"]
        mbu = s["mbu"]
        
        # If workload is memory-bound (MBU < 0.3), consider right-sizing
        if mbu < 0.3:
            # Find best GPU for memory-bound workload
            best_gtype = sorted_gpus[0][0]  # GPU with lowest $/GB-VRAM
            best_cost = cost_by_gb_vram[best_gtype]
            current_cost = cost_by_gb_vram.get(gtype, float('inf'))
            
            # Suggest right-sizing if current GPU is significantly more expensive
            if current_cost > best_cost * 1.5:  # 50% cost difference threshold
                on_demand_hr_current = num(cat[gtype]["on_demand_hr"])
                on_demand_hr_best = num(cat[best_gtype]["on_demand_hr"])
                
                # Calculate monthly savings (assuming typical 720 hours/month)
                monthly_cost_current = on_demand_hr_current * 720
                monthly_cost_best = on_demand_hr_best * 720
                monthly_savings = monthly_cost_current - monthly_cost_best
                
                right_size_suggestions.append({
                    "gpu_id": s["gpu_id"],
                    "current_gpu": gtype,
                    "proposed_gpu": best_gtype,
                    "mbu": mbu,
                    "reason": f"Memory-bound workload (MBU={mbu:.2f}), {gtype} overpriced vs {best_gtype}",
                    "monthly_savings": max(0, monthly_savings)
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
