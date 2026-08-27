---
name: guardrails
description: |
  Ensure every success metric is paired with guardrail metrics and check for trade-offs before presenting improvements as wins. Guardrails protect against winning the metric game while losing the business game. Apply this skill whenever you define a metric, create a metric spec, document a KPI, report positive findings, present an improvement, analyze metric changes, investigate metric lifts, share good news about metrics, celebrate wins, or present results showing any metric increased. This skill is CRITICAL for preventing false wins where one metric improves at the expense of another (e.g., conversion rate up but average order value down, signup rate up but activation down, resolution time down but customer satisfaction down). Use this skill automatically when you see phrases like "X improved", "X is up", "X increased", "better performance on X", "we're seeing gains in X", or any analysis showing positive metric movement. Also apply when defining metrics alongside the metric-spec skill to ensure guardrails are specified upfront. Never present a metric improvement without running the guardrail check — an improvement with a degraded guardrail is a trade-off or net negative, not a win.
---

# Skill: Guardrails Awareness

## Purpose
Ensure that every success metric is paired with at least one guardrail metric, and that positive findings are checked for trade-offs before being presented as wins.

## When to Use
Apply this skill in two situations:
1. **When defining metrics** — after using the Metric Spec skill, check whether the metric has a guardrail pair
2. **When reporting positive findings** — before presenting any improvement, check whether a related guardrail metric degraded

## Instructions

### What Are Guardrails?

A **guardrail metric** is a metric you don't want to degrade while optimizing a success metric. Guardrails protect against winning the metric game while losing the business game.

```
SUCCESS METRIC:  The metric you're trying to improve
GUARDRAIL:       The metric that must not get worse
```

**The rule:** Never celebrate an improvement on a success metric without checking its guardrail(s). An improvement with a degraded guardrail is a trade-off, not a win.

### Common Guardrail Pairs

| Success Metric | Guardrail(s) | Why |
|---------------|-------------|-----|
| Conversion rate | Average order value, Return rate | Aggressive discounts inflate conversion but erode margin and invite returns |
| Signup rate | Activation rate, 7-day retention | Lowering the signup bar brings in unqualified users who churn immediately |
| Revenue per user | User satisfaction (NPS/CSAT), Support ticket volume | Monetization pressure degrades experience |
| Feature adoption | Core workflow completion, Session duration | Forcing feature usage may disrupt existing workflows |
| Time to complete (speed) | Error rate, Quality score | Rushing degrades accuracy |
| Cost reduction | Quality, Customer satisfaction | Cutting costs can degrade service |
| Engagement (DAU, sessions) | Revenue per user, Churn rate | Engagement tricks (notifications, dark patterns) don't translate to value |
| Support resolution time | Customer satisfaction, Reopen rate | Fast close ≠ good close if tickets reopen |

### How to Apply

#### When Defining Metrics

After specifying a metric using the Metric Spec skill, add a guardrail section:

```markdown
### Guardrails
| Guardrail Metric | Acceptable Range | Check Frequency |
|-----------------|-----------------|-----------------|
| [guardrail 1] | [must stay above X / must not increase by >Y%] | [same cadence as success metric] |
| [guardrail 2] | [threshold] | [cadence] |
```

**Rules for selecting guardrails:**
1. At least one guardrail per success metric
2. The guardrail should measure a different dimension of value (e.g., if success is quantity, guardrail is quality)
3. The guardrail must be measurable with available data
4. If no obvious guardrail exists, use customer satisfaction or support ticket volume as defaults

**Guardrail selection framework:** When choosing guardrails, think about what could go wrong if you optimize the success metric aggressively. Ask yourself:

- **Quality vs. Quantity:** If the success metric measures volume (signups, orders, sessions), check quality metrics (conversion rate, AOV, retention)
- **Speed vs. Accuracy:** If the success metric measures speed (time to resolution, checkout time), check accuracy/quality (error rate, reopen rate, customer satisfaction)
- **Revenue vs. Experience:** If the success metric measures revenue (RPU, monetization rate), check experience metrics (NPS, support tickets, churn)
- **Short-term vs. Long-term:** If the success metric measures immediate outcomes, check long-term health (retention, LTV, repeat purchase rate)

**When guardrail data is unavailable:**
1. **First priority:** Check if the guardrail can be proxied (e.g., if CSAT data doesn't exist, use support ticket volume or product return rate as a quality signal)
2. **Second priority:** Document the missing guardrail as a known risk and recommend tracking it for future iterations
3. **Do NOT skip the guardrail check entirely** — use whatever quality signals are available, even if imperfect
4. **Example:** "Conversion rate improved 20%, but we lack return rate data to confirm quality. As a partial guardrail check, AOV increased 5% (suggesting legitimate demand, not discount-driven conversions). Recommend adding return rate tracking."

#### When Reporting Positive Findings

Before presenting any statement like "[metric] improved by X%," run this check:

```
GUARDRAIL CHECK
□ Identified guardrail metric(s) for [success metric]
□ Computed guardrail metric(s) over the same time period
□ Compared guardrail to baseline / acceptable range
□ Result: [CLEAR / TRADE-OFF / DEGRADED]
```

**Verdicts:**

| Verdict | Guardrail Status | How to Present |
|---------|-----------------|----------------|
| **CLEAR** | Guardrail stable or improved | Present the improvement as a win |
| **TRADE-OFF** | Guardrail slightly degraded (<10% relative) | Present the improvement AND the trade-off: "Conversion improved 15%, but AOV decreased 5%. Net revenue impact is +8%." |
| **DEGRADED** | Guardrail significantly degraded (>10% relative) | Do NOT present as a win. Present as: "Conversion improved 15%, but return rate doubled. The net impact may be negative — further investigation needed." |

**Note on thresholds:** The 10% threshold is a starting point, not a universal rule. Adjust based on context:
- **High-impact guardrails** (e.g., customer churn, security incidents): Even 5% degradation may be DEGRADED
- **Volatile guardrails** (e.g., daily engagement metrics): 10-15% degradation may be normal variance, use TRADE-OFF
- **Revenue-critical guardrails** (e.g., AOV, margin): Compute absolute dollar impact to determine severity, not just percentages
- **When in doubt**: Err on the side of caution — flag smaller degradations and let stakeholders decide if the trade-off is acceptable

### Guardrail Escalation

When a guardrail is degraded:

1. **Quantify both sides** — compute the success metric gain AND the guardrail loss in the same units (usually dollars or users)
2. **Compute net impact** — is the gain larger than the loss?
3. **Flag uncertainty** — guardrail degradation often has delayed effects (e.g., returns take weeks to materialize, churn shows up months later). Note this.
4. **Recommend investigation** — "The conversion improvement looks positive, but the return rate increase warrants investigation before concluding this is a net win."

### Output Format

When guardrails are checked, add this section to the analysis report:

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| [metric] | +X% | [guardrail 1] | [no change / +Y% / -Z%] | CLEAR / TRADE-OFF / DEGRADED |
| | | [guardrail 2] | [change] | [verdict] |

**Net assessment:** [The improvement is real / The improvement comes with a trade-off / The improvement may be net negative]
```

## Examples

### Example 1: Clear Win

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| Checkout conversion | +12% | Avg order value | +2% (stable) | CLEAR |
| | | Return rate | -1% (improved) | CLEAR |

**Net assessment:** The conversion improvement is a genuine win. Both guardrails are stable or improving.
```

### Example 2: Trade-Off

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| Signup rate | +25% | 7-day activation | -8% | TRADE-OFF |
| | | 30-day retention | -3% (within normal range) | CLEAR |

**Net assessment:** The signup rate improvement is partially offset by lower activation. The new signups are less qualified. Recommend segmenting the new signups to identify which acquisition channel is bringing lower-quality users.
```

### Example 3: Degraded Guardrail

```markdown
## Guardrail Check

| Success Metric | Change | Guardrail | Change | Verdict |
|---------------|--------|-----------|--------|---------|
| Resolution time | -40% (faster) | Reopen rate | +85% | DEGRADED |
| | | CSAT score | -22% | DEGRADED |

**Net assessment:** The faster resolution time is coming at the cost of quality. Tickets are being closed prematurely and reopened, and customer satisfaction has dropped significantly. This is NOT a net improvement. Recommend reverting the process change and investigating sustainable ways to reduce resolution time.
```

## Anti-Patterns

1. **Never report a success metric improvement without checking guardrails** — a 20% conversion lift with a 30% return rate increase is not a win
2. **Never define a metric without at least one guardrail** — every metric can be gamed; guardrails prevent it
3. **Never dismiss a small guardrail degradation** — small degradations compound and may have delayed effects (churn shows up months later)
4. **Never use the same metric as both success and guardrail** — they must measure different dimensions of value
5. **Never skip the net impact calculation** — "conversion up, returns up" is not actionable without knowing which effect is larger
