"""Tests for the input-tree restatement guardrail.

Anchored on a real headcount-NSM bug: when the NSM is a headcount (Weekly Active
Buyers), BDEF's Breadth lever IS that headcount, so the decomposition is
degenerate. The skill must reject it. When the NSM is a throughput count (Weekly
Completed Orders), Breadth = buyers is a genuine driver and must pass.
"""

import pytest

from helpers.north_star.input_tree import check_input_tree, _cov


# Real-shaped monthly series (Jan..Dec, full year), rounded.
BUYERS = [985, 1374, 1779, 2225, 2545, 2669, 3114, 3506, 3939, 4417, 5682, 5833]
FREQ = [1.22, 1.23, 1.22, 1.24, 1.23, 1.25, 1.26, 1.24, 1.24, 1.25, 1.26, 1.26]
EFF = [0.866, 0.858, 0.851, 0.853, 0.85, 0.849, 0.847, 0.851, 0.85, 0.852, 0.84, 0.838]

# Completed orders reconstructed from the three drivers (the real identity).
ORDERS = [b * f * e for b, f, e in zip(BUYERS, FREQ, EFF)]


def test_orders_nsm_with_distinct_drivers_passes():
    """NSM = Weekly Completed Orders, inputs = Breadth x Frequency x Efficiency.
    No input restates the NSM; the tree reconciles. Must be OK."""
    v = check_input_tree(
        ORDERS,
        {"Breadth": BUYERS, "Frequency": FREQ, "Efficiency": EFF},
        how="product",
    )
    assert v.ok, v.message
    assert v.reconciles
    assert not v.restatements
    assert all(i.status == "driver" for i in v.inputs)


def test_breadth_equal_to_nsm_is_rejected():
    """THE BUG: NSM = Weekly Active Buyers, and Breadth = active buyers. Breadth
    is a scaled copy of the NSM (ratio == 1.0 every period) → restatement → REJECT."""
    v = check_input_tree(
        BUYERS,                      # NSM is the buyer count itself
        {"Breadth": BUYERS},         # ...and Breadth restates it
        how="product",
    )
    assert not v.ok
    assert len(v.restatements) == 1
    assert v.restatements[0].name == "Breadth"
    assert v.restatements[0].ratio_cov == pytest.approx(0.0, abs=1e-9)


def test_scaled_copy_is_restatement():
    """An input that is a constant multiple of the NSM (e.g. NSM in thousands)
    is still a restatement, not a driver."""
    nsm = [x / 1000 for x in ORDERS]
    v = check_input_tree(nsm, {"Orders(k)": ORDERS}, how="product")
    assert not v.ok
    assert v.restatements[0].name == "Orders(k)"


def test_nonreconciling_tree_is_rejected():
    """Inputs that don't multiply back to the NSM are a fictional decomposition."""
    v = check_input_tree(
        ORDERS,
        {"Breadth": BUYERS, "Frequency": FREQ},  # missing Efficiency
        how="product",
    )
    assert not v.reconciles
    assert not v.ok


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        check_input_tree(ORDERS, {"Breadth": BUYERS[:-1]}, how="product")


def test_empty_inputs_raise():
    with pytest.raises(ValueError):
        check_input_tree(ORDERS, {}, how="product")


def test_cov_flat_series_is_zero():
    assert _cov([5, 5, 5, 5]) == 0.0
    assert _cov([1, 2, 3, 4]) > 0
