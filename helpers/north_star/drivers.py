"""Driver decomposition + report for /north-star drivers.

Deterministic engine behind the `drivers` verb. Given a throughput North Star
(default: weekly completed orders) and a time window, it decomposes growth into
its multiplicative drivers — Completed = Breadth x Frequency x Efficiency — with
Depth (AOV) reported as a value guardrail, and renders a self-contained report
(markdown + Economist-styled HTML with a diverging chart).

WHY THIS EXISTS: a freehand "decompose what drove the year" prompt gives the right
*story* but drifts on the exact numbers (it picks its own window) and doesn't
auto-produce the report/chart. This pins the window + definitions so the output is
identical every run — what you put on a slide is what shows up live.

The window is parameterized. Default = first full month to last full month of the
data. Pass start/end to use a different window (e.g. exclude an end-of-year spike
with Feb -> Nov). The report label comes from the active dataset (`--name`), not
hardcoded.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import pandas as pd

# repo_root/data/practice  (helper lives at repo_root/helpers/north_star/)
DEFAULT_DATA = Path(__file__).resolve().parents[2] / "data" / "practice"


def _full_months(o: pd.DataFrame) -> pd.PeriodIndex:
    """Months with a plausibly-complete set of days (drops a trailing stray like
    a single 2025-01-01 row). A month counts as full if it has >= 20 distinct days
    of orders."""
    days = o.groupby("month").order_timestamp.apply(lambda s: s.dt.normalize().nunique())
    return days[days >= 20].index


def compute(data_dir: Path = DEFAULT_DATA, start: str | None = None,
            end: str | None = None, nsm: str = "weekly completed orders",
            name: str | None = None) -> dict:
    o = pd.read_csv(Path(data_dir) / "orders.csv", parse_dates=["order_timestamp"])
    o["month"] = o.order_timestamp.dt.to_period("M")
    o["week"] = o.order_timestamp.dt.to_period("W").dt.start_time
    full = _full_months(o)
    o = o[o.month.isin(full)]
    comp = o[o.status == "completed"].copy()

    # Monthly driver series. Completed = Breadth x Frequency x Efficiency.
    m = pd.DataFrame({
        "completed": comp.groupby("month").order_id.count(),
        "placed": o.groupby("month").order_id.count(),
        "buyers": comp.groupby("month").user_id.nunique(),
        "gmv": comp.groupby("month").total_amount.sum(),
    }).sort_index()
    m["freq"] = m.placed / m.buyers          # orders placed per buyer
    m["eff"] = m.completed / m.placed        # checkout completion rate
    m["aov"] = m.gmv / m.completed           # Depth: value per completed order

    # Resolve window (default: first -> last full month)
    sp = pd.Period(start, "M") if start else m.index.min()
    ep = pd.Period(end, "M") if end else m.index.max()
    if sp not in m.index or ep not in m.index:
        raise ValueError(f"window {sp}..{ep} not in available full months {list(m.index)}")
    f, l = m.loc[sp], m.loc[ep]

    tot = math.log(l.completed / f.completed)
    share = lambda k: round(math.log(l[k] / f[k]) / tot * 100)

    # peak week within the window
    wk = comp[(comp.month >= sp) & (comp.month <= ep)].groupby("week").order_id.count()
    peak_week, peak_val = wk.idxmax(), int(wk.max())

    # root-cause levers (over the window)
    win = comp[(comp.month >= sp) & (comp.month <= ep)]
    per_user = win.groupby("user_id").order_id.count()
    repeat_rate = (per_user > 1).mean()
    plus_users = set(win[win.is_plus_member_order].user_id)
    win = win.assign(is_plus_user=win.user_id.isin(plus_users))
    freq_plus = win[win.is_plus_user].order_id.count() / max(len(plus_users), 1)
    non_n = win[~win.is_plus_user].user_id.nunique()
    freq_non = win[~win.is_plus_user].order_id.count() / max(non_n, 1)
    plus_share = win.is_plus_member_order.mean()

    return dict(
        nsm=nsm, year=str(sp.year),
        start_mon=sp.strftime("%b"), end_mon=ep.strftime("%b"),
        window=f"{sp.strftime('%b')}–{ep.strftime('%b')} {sp.year}",
        nsm_x=round(l.completed / f.completed, 1),
        orders_start=int(f.completed), orders_end=int(l.completed),
        peak_week=peak_week.date().isoformat(), peak_val=peak_val,
        breadth_share=share("buyers"), freq_share=share("freq"), eff_share=share("eff"),
        buyers_start=int(f.buyers), buyers_end=int(l.buyers),
        freq_min=round(m.freq.min(), 2), freq_max=round(m.freq.max(), 2),
        eff_min=round(m.eff.min() * 100, 1), eff_max=round(m.eff.max() * 100, 1),
        aov_start=round(f.aov, 0), aov_end=round(l.aov, 0),
        aov_chg_pct=round((l.aov - f.aov) / f.aov * 100),
        repeat_rate=round(repeat_rate * 100, 1),
        plus_share=round(plus_share * 100, 1),
        freq_plus=round(freq_plus, 2), freq_non=round(freq_non, 2),
        name=name or "your dataset",
        # the exact driver series, so the verb can run the input-tree guardrail
        _series=dict(completed=list(m.completed), buyers=list(m.buyers),
                     freq=list(m.freq), eff=list(m.eff)),
    )


def render_md(s: dict) -> str:
    nsm_title = s["nsm"].title()
    return f"""# North Star Report — {s['name']} ({s['window']})

_North Star: **{nsm_title}** · window {s['window']} · deterministic (`/north-star drivers`)_

## Headline

{nsm_title} grew **{s['nsm_x']}×** — from **{s['orders_start']:,}** to **{s['orders_end']:,}**
orders/month ({s['start_mon']} → {s['end_mon']} {s['year']}; Black Friday peak **{s['peak_val']:,}** in a week).
On the surface: a great year.

## What actually drove it

`Completed Orders = Breadth × Frequency × Efficiency`. Decomposing the growth:

| Driver | Input | trend | Share of growth |
|--------|-------|-------|-----------------|
| **Breadth** | Active buyers | {s['buyers_start']:,} → {s['buyers_end']:,}/mo | **{s['breadth_share']:+d}%** |
| **Frequency** | Orders per buyer | {s['freq_min']}–{s['freq_max']} | {s['freq_share']:+d}% |
| **Efficiency** | Checkout completion | {s['eff_min']}–{s['eff_max']}% | {s['eff_share']:+d}% |

**Depth guardrail** — Avg order value moved **{s['aov_chg_pct']:+d}%** (${s['aov_start']:.0f} → ${s['aov_end']:.0f}).
Depth drives revenue-per-order, not order count, so it's a guardrail, not a growth driver.

## Root cause

Growth is **{s['breadth_share']}% Breadth** — new-buyer acquisition. Frequency and Efficiency
are flat. There's no repeat-purchase engine: the annual repeat rate is just **{s['repeat_rate']}%**.
Plus membership is **{s['plus_share']}%** of orders, and Plus buyers order **{s['freq_plus']}** vs
non-Plus **{s['freq_non']}** — no lift.

## Recommendation

1. **Move Frequency, not acquisition** — repeat purchase is the untapped lever.
2. **Treat Plus as broken, not the answer** — {s['plus_share']}% adoption, ~zero lift.
3. **Guardrail: AOV** — Depth moved {s['aov_chg_pct']:+d}%; don't buy orders by shrinking baskets.

_The headline said "great year." The decomposition said "single-threaded growth with a broken
retention lever." The metric didn't tell you that — the judgment did._
"""


def render_html(s: dict) -> str:
    """Self-contained Economist-editorial HTML with a zero-centered diverging chart."""
    mx = max(abs(s["breadth_share"]), abs(s["freq_share"]), abs(s["eff_share"]), 1)

    def drow(label, sub, sh):
        w = abs(sh) / mx * 100
        cell = f'<div class="dfill" style="width:{w}%;background:{"var(--red)" if sh < 0 else "var(--blue)"}"></div>'
        neg, pos = (cell, "") if sh < 0 else ("", cell)
        vcolor = "var(--red)" if sh < 0 else "var(--blue)"
        return (f'<div class="drow"><span class="dlbl">{label}<em>{sub}</em></span>'
                f'<div class="neg">{neg}</div><div class="pos">{pos}</div>'
                f'<span class="dval" style="color:{vcolor}">{sh:+d}%</span></div>')

    bars = (drow("Breadth", "buyers", s["breadth_share"])
            + drow("Frequency", "orders/buyer", s["freq_share"])
            + drow("Efficiency", "completion", s["eff_share"]))
    nsm_title = s["nsm"].title()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>North Star Report — {s['name']} {s['window']}</title>
<style>
  :root {{ --bg:#F5F4EE; --surface:#FBFAF5; --rule:#1A1A1A; --text:#1A1A1A;
    --sec:#5A5A55; --muted:#8A8580; --red:#C8102E; --blue:#006BA2; --green:#2D8659;
    --gray-l:#E5E3DC; --serif:'Charter','Georgia',serif;
    --sans:'Inter',-apple-system,'Helvetica Neue',Arial,sans-serif; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text); font:16px/1.55 var(--sans); }}
  .wrap {{ max-width:760px; margin:0 auto; padding:0 28px 80px; }}
  .toptab {{ width:54px; height:11px; background:var(--red); margin:40px 0 18px; }}
  .eyebrow {{ font-size:11px; letter-spacing:.16em; text-transform:uppercase; font-weight:700; color:var(--red); }}
  h1 {{ font-family:var(--serif); font-size:34px; font-weight:700; margin:4px 0 4px; letter-spacing:-.01em; }}
  .src {{ color:var(--muted); font-size:13px; padding-bottom:20px; border-bottom:2px solid var(--rule); margin-bottom:26px; }}
  .hero {{ margin-bottom:30px; }}
  .big {{ font-family:var(--serif); font-size:58px; font-weight:700; line-height:1; letter-spacing:-.02em; }}
  .big .x {{ color:var(--red); }}
  .hero p {{ color:var(--sec); margin:14px 0 0; font-size:16.5px; max-width:62ch; }}
  h2 {{ font-size:12px; letter-spacing:.1em; text-transform:uppercase; color:var(--text); font-weight:700;
    margin:36px 0 6px; padding-bottom:7px; border-bottom:1px solid var(--rule); }}
  .eq {{ font-family:monospace; font-size:13px; color:var(--sec); margin:14px 0 8px; }}
  .eq b {{ color:var(--blue); }}
  .dchart {{ margin:10px 0 6px; }}
  .drow {{ display:grid; grid-template-columns:130px 1fr 1fr 52px; align-items:center; height:34px; }}
  .dlbl {{ font-size:13px; font-weight:700; color:var(--text); padding-right:12px; }}
  .dlbl em {{ display:block; font-style:normal; font-weight:400; font-size:11px; color:var(--muted); }}
  .neg {{ display:flex; justify-content:flex-end; border-right:2px solid var(--rule); }}
  .pos {{ display:flex; justify-content:flex-start; }}
  .dfill {{ height:18px; min-width:2px; }}
  .dval {{ font-size:14px; font-weight:700; text-align:right; font-variant-numeric:tabular-nums; }}
  .axis {{ display:grid; grid-template-columns:130px 1fr 1fr 52px; font-size:10.5px; color:var(--muted);
    text-transform:uppercase; letter-spacing:.08em; margin-top:2px; }}
  .axis .l {{ grid-column:2; text-align:right; padding-right:6px; }}
  .axis .r {{ grid-column:3; padding-left:6px; }}
  .guard {{ margin-top:16px; padding:12px 16px; background:var(--surface); border:1px solid var(--gray-l);
    border-left:3px solid var(--red); font-size:14px; color:var(--sec); }}
  .guard b {{ color:var(--text); }}
  .card {{ border-left:3px solid var(--red); padding:4px 0 4px 18px; margin:16px 0; color:var(--sec);
    font-size:15.5px; max-width:64ch; }}
  .card b {{ color:var(--text); }}
  ol {{ padding-left:20px; max-width:64ch; }} li {{ margin-bottom:11px; color:var(--sec); }} li b {{ color:var(--text); }}
  .kicker {{ font-family:var(--serif); font-size:18px; line-height:1.5; margin-top:34px; padding-top:22px;
    border-top:2px solid var(--rule); color:var(--text); max-width:64ch; }}
  .kicker b {{ color:var(--red); font-style:italic; font-weight:700; }}
</style></head><body><div class="wrap">
  <div class="toptab"></div>
  <div class="eyebrow">North Star Report</div>
  <h1>{s['name']} — {s['window']}</h1>
  <div class="src">Generated by <code>/north-star drivers</code> · North Star: <b>{nsm_title}</b> · window {s['window']}</div>

  <div class="hero">
    <div class="big">{s['nsm_x']}<span class="x">×</span> growth</div>
    <p>{nsm_title} climbed from <b>{s['orders_start']:,}</b> to <b>{s['orders_end']:,}</b> per month
    ({s['start_mon']} → {s['end_mon']} {s['year']}; Black Friday peak <b>{s['peak_val']:,}</b> in a week). On the surface: a great year.</p>
  </div>

  <h2>What actually drove the growth</h2>
  <div class="eq">Completed Orders = <b>Breadth</b> × <b>Frequency</b> × <b>Efficiency</b> &nbsp;— three drivers, none equal to the North Star</div>
  <div class="dchart">{bars}</div>
  <div class="axis"><span class="l">drag ◄</span><span class="r">► lift</span></div>
  <div class="guard"><b>Depth guardrail —</b> avg order value moved <b>{s['aov_chg_pct']:+d}%</b>
    (${s['aov_start']:.0f} → ${s['aov_end']:.0f}). Depth drives revenue-per-order, not order count, so it's a
    guardrail, not a growth driver.</div>

  <h2>Root cause</h2>
  <div class="card">Order growth is <b>{s['breadth_share']}% Breadth</b> — new-buyer acquisition. Frequency and
    Efficiency are flat. There's <b>no repeat-purchase engine</b>: the annual repeat rate is just
    <b>{s['repeat_rate']}%</b>. If paid channels slow, the North Star stalls.</div>
  <div class="card">The obvious retention lever isn't working: <b>Plus membership is {s['plus_share']}%</b> of orders,
    and Plus buyers order <b>{s['freq_plus']}</b> vs non-Plus <b>{s['freq_non']}</b> — no lift.</div>

  <h2>Recommendation</h2>
  <ol>
    <li><b>Move Frequency, not acquisition.</b> The highest-leverage driver left is repeat purchase.</li>
    <li><b>Treat Plus as broken, not the answer.</b> {s['plus_share']}% adoption, ~zero frequency lift.</li>
    <li><b>Guardrail: AOV.</b> Depth moved {s['aov_chg_pct']:+d}% — don't buy orders by shrinking baskets.</li>
  </ol>

  <div class="kicker">The headline said “great year.” The decomposition said
    <b>single-threaded growth with a broken retention lever.</b> The metric didn't tell you
    that — the judgment did. That's the whole job.</div>
</div></body></html>"""
