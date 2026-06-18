# Verb: /north-star inputs

**Specialist:** Designer (`agents/north-star/designer.md`, inputs mode)
**Guardrail:** `helpers/north_star/input_tree.py` (hard gate — runs every time)
**Wiki reads:** inputs.md, input-tests-greenfield-and-roadmap.md, the BDEF heuristic

## Purpose

Build the **input tree** (metric tree) for an *already-chosen* North Star: the small
set of independent drivers that move it. Uses the Breadth / Depth / Efficiency /
Frequency heuristic, then **proves against the data that no input restates the NSM**.

This verb exists because of a real defect: it is easy to pick a North Star (e.g.
"Weekly Active Buyers") and then list "Breadth = active buyers" as an input — which
is the North Star wearing a different hat, not a driver. The cardinal rule (wiki
`inputs.md`): *an input must be a driver of the NSM, never a restatement of it.* This
verb enforces that mechanically so the skill can never emit a degenerate tree.

## Pre-requisites

- An audited NSM. Read `profile.nsm.current.statement`. If none, tell the user to run
  `/north-star audit "<candidate>"` first (or pass a candidate inline).
- A connected dataset (`/datasets` shows an active source). The Designer needs data to
  compute each candidate input's series and run the guardrail.

## Workflow

### 1. Classify the NSM shape

Read the NSM statement. Is it a **throughput count/rate** (orders, nights booked,
messages sent, value moments) or a **headcount** (active users/buyers)?

- Throughput → BDEF factors are genuine, independent drivers. Proceed.
- Headcount → warn: "Breadth will restate this NSM." Offer two honest paths:
  (a) re-cast the NSM as the throughput it implies (e.g. *active buyers* →
  *completed orders*), or (b) decompose the headcount by **Acquisition (new) +
  Retention (returning)** instead of BDEF. Do not silently emit Breadth = the NSM.

### 2. Designer proposes the input tree

Read `agents/north-star/designer.md` (inputs mode). For the chosen NSM, propose 3–5
inputs using BDEF, each with BOTH a pithy name AND a precise definition
(`inputs.md` decision rule). For each input, state **how to compute it from the
active dataset** (the column/aggregation or SQL).

State the combination form: `product` (NSM = i1 × i2 × …) or `sum`.

### 3. Compute the series + run the guardrail (REQUIRED — never skip)

Compute the NSM and each input as a per-period series from the data (monthly or
weekly, same periods, same order). Then validate:

```bash
echo '{"nsm": [...], "inputs": {"Breadth": [...], "Frequency": [...], ...}, "how": "product"}' \
  | python3 -m helpers.north_star check-input-tree
```

The verdict (`InputTreeVerdict`) returns:
- `ok` — True only if the tree **reconciles** to the NSM AND **no input is a restatement**.
- `inputs[].status` — `"driver"` or `"restatement"` per input, with `ratio_cov`.
- `reconciles` / `recon_error` — do the inputs actually combine back to the NSM.
- `message` — the human-readable verdict.

### 4. Gate on the verdict

- **If any input is a `restatement`:** STOP. Do NOT emit the tree. Show the offending
  input + its note, and return the user to Step 1 path (a) or (b). This is the whole
  point of the verb — a restatement is a hard refuse, not a warning.
- **If `reconciles` is False:** the decomposition is incomplete or wrong-shaped. Tell
  the user which form was tried and that the inputs don't multiply/sum back to the NSM.
- **If `ok`:** proceed to emit.

### 5. Validate scope (Greenfield test)

For each surviving input, apply the Greenfield test (`input-tests-greenfield-and-roadmap.md`):
can the team brainstorm ≥ a handful of ways to move it in two minutes? Too few → too
narrow; too many vague ones → too broad. Note any input that fails scope as WEAK (not a
hard reject).

### 6. Emit the input tree

Render the metric tree: NSM at the root, each validated input with its definition,
current value/trend from the data, and its share of the NSM's recent movement. Write to
the profile (`nsm.inputs`) and offer the report (`/north-star report` or the data→report
flow).

## Failure modes

| Failure | Response |
|---|---|
| Input restates the NSM (guardrail) | Hard refuse; route to re-cast NSM or Acquisition/Retention split |
| Tree doesn't reconcile | Surface recon_error; Designer revises the factor set |
| No active dataset | Can't compute series → can't run guardrail → tell user to `/connect-data` |
| Headcount NSM | Warn before designing; don't emit Breadth = NSM |

## Example

```
$ /north-star inputs            # NSM in profile: "weekly completed orders"

Input tree (validated against data/practice, Jan–Dec 2024):
  Completed Orders = Breadth × Frequency × Efficiency        [reconciles, error 0.0%]
    • Breadth     — weekly active buyers           driver (ratio CoV 0.71%)   +99% of growth
    • Frequency   — orders per buyer               driver (ratio CoV 57%)      +2%
    • Efficiency  — checkout completion rate       driver (ratio CoV 59%)      −1%
  Depth (AOV) tracked as a value guardrail, not a driver of order count.

✓ No input restates the North Star.
```
