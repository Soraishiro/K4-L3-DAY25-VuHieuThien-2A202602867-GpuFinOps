"""Generate transparent conditional cost reports and a waterfall plot."""
from __future__ import annotations


def build_report(baseline_usd: float, optimized_usd: float, levers: dict,
                 sustainability: dict | None = None, period: str = "monthly",
                 inference_metrics: dict | None = None,
                 assumptions: list[str] | None = None) -> str:
    savings = baseline_usd - optimized_usd
    pct = savings / baseline_usd * 100 if baseline_usd else 0.0
    lines = [
        "# NimbusAI — GPU FinOps (Synthetic Scenario)", "",
        "**Status:** Conditional projection, not verified savings",
        f"**Period:** {period}  ",
        f"**Baseline spend:** ${baseline_usd:,.0f}  ",
        f"**Optimized spend (conditional):** ${optimized_usd:,.0f}  ",
        f"**Projected savings (conditional):** ${savings:,.0f} (**{pct:.0f}%**)",
        "", "## Savings by lever", "",
        "| Lever | Conditional monthly saving (USD) |", "|---|---:|",
    ]
    for name, amount in levers.items():
        lines.append(f"| {name} | ${amount:,.0f} |")
    if inference_metrics:
        lines += [
            "", "## Inference unit economics",
            f"- Before: ${inference_metrics['baseline_per_m']:.3f}/1M-token",
            f"- After: ${inference_metrics['optimized_per_m']:.3f}/1M-token",
            f"- Simulated improvement: {inference_metrics['savings_pct']:.1f}%",
            "- Routing, cache and batch are evaluated jointly, not independently.",
        ]
    if sustainability:
        lines += [
            "", "## Sustainability",
            f"- Energy per simulated query: {sustainability.get('wh_per_query', 0):.2f} Wh",
            f"- Carbon per query (us-east-1): {sustainability.get('carbon_g', 0):.3f} gCO2e",
            f"- Lowest carbon-intensity assumption: {sustainability.get('cleanest_region', 'n/a')}",
            f"- Lowest electricity-price assumption: {sustainability.get('cheapest_region', 'n/a')}",
            "- Neither region comparison includes GPU prices, latency or capacity.",
        ]
    if assumptions:
        lines += ["", "## Scope and validation requirements", ""]
        lines.extend(f"- {note}" for note in assumptions)
    lines += [
        "", "_Synthetic June 2026 snapshot: re-baseline with invoices, measured throughput, latency and model quality._",
    ]
    return "\n".join(lines)


def savings_waterfall(levers: dict, path: str, baseline_usd: float | None = None) -> str:
    """Produce a genuine sequential waterfall (compatible with legacy calls)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return ""
    names, vals = list(levers.keys()), list(levers.values())
    fig, ax = plt.subplots(figsize=(11, 5.5))
    if baseline_usd is None:
        ax.bar(names, vals)
    else:
        labels = ["Baseline"] + names + ["Conditional optimized"]
        running = baseline_usd
        bottoms, heights = [0], [running]
        for amount in vals:
            running -= amount
            bottoms.append(running)
            heights.append(amount)
        bottoms.append(0)
        heights.append(running)
        ax.bar(range(len(labels)), heights, bottom=bottoms)
        ax.set_xticks(range(len(labels)), labels)
    ax.set_ylabel("USD / month (synthetic)")
    ax.set_title("Conditional GPU FinOps savings waterfall")
    plt.xticks(rotation=22, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path
