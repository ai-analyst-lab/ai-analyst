"""Input-tree validation for /north-star inputs.

The cardinal rule of the North Star Framework: an input must be a *driver* of the
North Star, never a *restatement* of it (wiki: inputs.md decision rule, anti-pattern
`inputs-wrong-granularity`). Before this module, nothing enforced that — the skill
could happily emit "Breadth = active buyers" for an NSM that *is* active buyers,
producing a degenerate decomposition where one input equals the metric.

This module makes that a hard, data-driven guardrail so the skill can't ship it.

How "restatement" is detected (and why correlation is the WRONG test):
  A legitimate driver can be highly *correlated* with the NSM — buyer count and
  order count both grow together, but buyers is still a real driver of orders.
  Correlation would false-positive on it. The true signal of a restatement is that
  the input is a *scaled copy* of the NSM: input_t = k * NSM_t for a constant k,
  i.e. the ratio (input / NSM) has ~zero variance. When the NSM literally IS the
  input, that ratio is 1.0 every period. When the input is a genuine factor, the
  ratio moves with the OTHER factors. So we test the coefficient of variation of
  the per-period ratio, not correlation.

Pure-Python (lists + math) so it's lightweight and dependency-free on the hot path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence


# An input is a restatement iff it is the NSM *rescaled* — input_t = k * NSM_t for a
# single fixed k, so the per-period ratio (input/NSM) is constant to machine
# precision. We must test EXACTNESS, not "approximately constant": a genuine
# dominant driver can have a near-constant ratio purely because the OTHER drivers
# were flat that period (e.g. a buyers/orders ratio can wobble only ~0.4% because
# frequency and efficiency barely moved — yet buyers is a real driver, not a copy).
# Only an exact/rescaled copy gets a ratio CoV at the floating-point floor.
RESTATEMENT_COV = 1e-6

# Multiplicative/additive reconciliation tolerance: the inputs must actually
# combine back to the NSM, else the "decomposition" is fiction.
RECON_TOL = 0.02


@dataclass(frozen=True)
class InputVerdict:
    name: str
    status: str  # "driver" | "restatement"
    ratio_cov: Optional[float]  # coefficient of variation of input/NSM
    note: str


@dataclass(frozen=True)
class InputTreeVerdict:
    ok: bool
    reconciles: bool
    recon_error: Optional[float]
    how: str
    inputs: tuple[InputVerdict, ...]
    message: str

    @property
    def restatements(self) -> tuple[InputVerdict, ...]:
        return tuple(v for v in self.inputs if v.status == "restatement")


def _cov(xs: Sequence[float]) -> float:
    """Coefficient of variation (std/|mean|) of a sequence. 0 == perfectly flat."""
    n = len(xs)
    if n == 0:
        return 0.0
    mean = sum(xs) / n
    if mean == 0:
        return float("inf")
    var = sum((x - mean) ** 2 for x in xs) / n
    return math.sqrt(var) / abs(mean)


def check_input_tree(
    nsm: Sequence[float],
    inputs: dict[str, Sequence[float]],
    how: str = "product",
    restatement_cov: float = RESTATEMENT_COV,
    recon_tol: float = RECON_TOL,
) -> InputTreeVerdict:
    """Validate a proposed NSM input tree against the per-period data.

    Args:
        nsm: the NSM value per period (e.g. monthly completed orders).
        inputs: {input_name: per-period series}. Same length/order as nsm.
        how: "product" (NSM = i1*i2*...) or "sum" (NSM = i1+i2+...). Most BDEF
            decompositions are multiplicative.
        restatement_cov: ratio-CoV at/below which an input is judged a restatement.
        recon_tol: max allowed relative error when recombining inputs into the NSM.

    Returns:
        InputTreeVerdict. `ok` is True iff the tree reconciles AND no input is a
        restatement of the NSM.

    Raises:
        ValueError: if inputs is empty, lengths mismatch, or `how` is unknown.
    """
    if not inputs:
        raise ValueError("no inputs provided to validate")
    n = len(nsm)
    if n == 0:
        raise ValueError("nsm series is empty")
    for name, series in inputs.items():
        if len(series) != n:
            raise ValueError(f"input {name!r} length {len(series)} != nsm length {n}")
    if how not in ("product", "sum"):
        raise ValueError(f"how must be 'product' or 'sum', got {how!r}")

    # 1. Reconciliation — do the inputs actually combine back to the NSM?
    recon_err = 0.0
    for t in range(n):
        if how == "product":
            combined = 1.0
            for series in inputs.values():
                combined *= series[t]
        else:
            combined = sum(series[t] for series in inputs.values())
        if nsm[t] != 0:
            recon_err = max(recon_err, abs(combined - nsm[t]) / abs(nsm[t]))
    reconciles = recon_err <= recon_tol

    # 2. Distinctness — is any input a scaled copy of the NSM (a restatement)?
    verdicts = []
    for name, series in inputs.items():
        ratios = [series[t] / nsm[t] for t in range(n) if nsm[t] != 0]
        cov = _cov(ratios) if ratios else 0.0
        if cov <= restatement_cov:
            verdicts.append(InputVerdict(
                name=name, status="restatement", ratio_cov=cov,
                note=(f"'{name}' IS the North Star rescaled (input/NSM is a fixed "
                      f"constant, CoV={cov:.1e}). It restates the metric instead of "
                      f"driving it. Pick a North Star this input is a genuine factor "
                      f"of (e.g. a throughput count), or replace this input."),
            ))
        else:
            verdicts.append(InputVerdict(
                name=name, status="driver", ratio_cov=cov,
                note=f"genuine driver (input/NSM varies, CoV={cov:.2f}).",
            ))

    restatements = [v for v in verdicts if v.status == "restatement"]
    ok = reconciles and not restatements
    if restatements:
        msg = ("REJECTED — an input restates the North Star: "
               + "; ".join(v.name for v in restatements)
               + ". An input must be a driver, never a relabel of the metric.")
    elif not reconciles:
        msg = (f"REJECTED — inputs do not reconcile to the North Star "
               f"(max error {recon_err:.1%} > {recon_tol:.0%}). The decomposition "
               f"is incomplete or wrong-shaped.")
    else:
        msg = f"OK — {len(verdicts)} distinct drivers reconcile to the North Star."

    return InputTreeVerdict(
        ok=ok, reconciles=reconciles, recon_error=recon_err, how=how,
        inputs=tuple(verdicts), message=msg,
    )
