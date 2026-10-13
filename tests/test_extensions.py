"""Regression tests for conditional-cost assumptions and lab extensions."""
import csv
import os
from finops import pricing
from missions import m1_efficiency_audit, m3_purchasing, m4_allocation, m5_report
from missions._common import ROOT


def test_reserved_commitment_horizon():
    assert pricing.recommend_tier(24, False, job_days=30) == "on_demand"
    assert pricing.recommend_tier(24, False, job_days=30,
                                  existing_reserved_capacity=True) == "reserved"
    assert pricing.recommend_tier(24, False, job_days=365) == "reserved"
    assert pricing.commitment_total_cost(2.0, 1, 30, 1) == 17520
    assert pricing.commitment_total_cost(1.4, 3, 366, 1) == 36792
    assert pricing.commitment_total_cost(2.0, 1, 366, 1) < pricing.commitment_total_cost(1.4, 3, 366, 1)


def test_gpu_type_affects_expected_spot_cost():
    assert pricing.recommend_tier(8, True, gpu_type="H100",
                                  spot_hr=0.93, on_demand_hr=1.0) == "spot"
    assert pricing.recommend_tier(8, True, gpu_type="B200",
                                  spot_hr=0.93, on_demand_hr=1.0) == "on_demand"


def test_rightsize_excludes_idle_hours():
    result = m1_efficiency_audit.run(verbose=False)
    suggestions = result["right_size_suggestions"]
    assert suggestions
    for s in suggestions:
        source = next(x for x in result["summary"] if x["gpu_id"] == s["gpu_id"])
        assert s["active_hours_month"] == (24 - source["idle_hours"]) * 30
        assert s["monthly_savings"] >= 0
        assert s["cost_per_gb_after"] < s["cost_per_gb_before"]
        assert s["bandwidth_after"] > 0


def test_new_commitment_not_recommended_for_short_jobs():
    result = m3_purchasing.run(verbose=False, existing_reserved_capacity=False)
    assert all(r["tier"] != "reserved" for r in result["recommendations"])


def test_focus_export_has_all_requests():
    m4_allocation.run(verbose=False)
    with open(os.path.join(ROOT, "outputs", "focus_export.csv")) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2400
    assert len({r["ResourceId"] for r in rows}) == 2400
    assert all(r["EffectiveCost"] and r["ChargePeriodEnd"] for r in rows)


def test_report_marks_uncertain_additivity():
    result = m5_report.run(verbose=False)
    assert result["scenario_only"] is True
    with open(os.path.join(ROOT, "outputs", "report.md")) as f:
        content = f.read()
    assert "not verified savings" in content
    assert "1M-token" in content
    assert "do not overlap" in content
