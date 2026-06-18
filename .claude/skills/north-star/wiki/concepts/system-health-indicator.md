---
title: System Health Indicator — A Specialized Input for Non-Feature Factors
type: concept
schema_version: 1
sources:
  - definitions/definition-p057-l0332-system-health-indicator.md
  - concepts/concept-p057-l0341-system-health-as-balance.md
  - principles/principle-p057-l0360-reframe-tech-debt-as-drag.md
related:
  - wiki/concepts/inputs.md
  - wiki/concepts/squad-organization.md
playbook_pages: [57]
tier: 1
confidence: medium
confidence_derivation: "Anchor definition singleton (1/1); supporting concept 2/2; principle 1/1 singleton → degraded to medium per singleton-prevalence."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# System Health Indicator — A Specialized Input for Non-Feature Factors

## TL;DR
A system health indicator is a specific kind of input metric that captures non-feature factors users don't directly experience but that indirectly affect product quality and team effectiveness — uptime, cycle times, deployment process, tooling, ramp-up time. Troy Magennis frames system health as a balance across six areas: value, consistency, quality, speed, quantity, sustainability. The NSM already covers value; an effective health-input is typically a composite spanning sustainability, quality, and consistency.

## Decision rule
- Include a system health indicator input in the NSF when non-feature factors (uptime, cycle times, deployment process, tooling, ramp-up time) materially affect product quality [definition-p057-l0332-system-health-indicator].
- Treat system health as a BALANCE across six dimensions, not as any single metric [concept-p057-l0341-system-health-as-balance].
- The NSM covers "value" — the health input should focus on sustainability, quality, and consistency, with speed and quantity as early indicators of drag.
- Reframe technical debt work as "drag on value" so engineering hygiene becomes legible inside the framework [principle-p057-l0360-reframe-tech-debt-as-drag].

## Detail
**Definition.** "This is why we often suggest that teams include a system health indicator input in their North Star. This input can cover critical, non-feature factors that users might not directly experience but that indirectly affect your product's overall quality and your engineering and design teams' ability to work effectively" [definition-p057-l0332-system-health-indicator]. The system health indicator is a SPECIALIZED kind of input — most NSF inputs measure customer behavior; the system health indicator measures the engineering and design system that produces customer behavior.

**Health is a balance, not a single number.** "Most important is that health is a balance. It is not just one thing... Troy describes six areas to consider when thinking about health indicators: Value: Do the right stuff; Consistency: Do it predictably; Quality: Do it right; Speed: Do it fast; Quantity: Do lots; Sustainability: Keep doing it" [concept-p057-l0341-system-health-as-balance].

The six Magennis health areas:

1. **Value** — Do the right stuff (covered by the NSM)
2. **Consistency** — Do it predictably
3. **Quality** — Do it right
4. **Speed** — Do it fast
5. **Quantity** — Do lots
6. **Sustainability** — Keep doing it

Because the NSM already covers (1), the playbook recommends building the system health input as a composite spanning (6), (3), and (2) — sustainability, quality, consistency — with (4) and (5) as early indicators of drag rather than primary targets. Optimizing only speed or only quantity produces the classic feature-factory failure mode visible from the engineering side.

**Tech-debt reframe.** "Reframe technical debt as drag on value to emphasize how it limits impact and affects business results" [principle-p057-l0360-reframe-tech-debt-as-drag]. The naming change matters: "tech debt" sounds like an engineering internal concern; "drag on value" connects directly to the NSM. Engineering hygiene work becomes a legitimate L2 opportunity that ladders up to the system health indicator input.

System health indicators are the framework's mechanism for making non-feature engineering work first-class. Without one, engineering hygiene competes for backlog slots against customer-facing features — and tends to lose.

## yaml-rules
```yaml
system_health_indicator:
  is: specialized_input_metric
  measures: non_feature_factors_affecting_quality
  examples:
    - uptime
    - cycle_times
    - deployment_process
    - tooling
    - ramp_up_time
  include_when: non_feature_factors_materially_affect_quality
six_health_areas_magennis:
  value: do_the_right_stuff
  consistency: do_it_predictably
  quality: do_it_right
  speed: do_it_fast
  quantity: do_lots
  sustainability: keep_doing_it
composite_input_recommendation:
  nsm_already_covers: value
  health_input_should_emphasize: [sustainability, quality, consistency]
  health_input_early_indicators: [speed, quantity]
tech_debt_reframe:
  rename_to: drag_on_value
  surfaces_as: l2_opportunity_against_health_input
```

## Related
- [Inputs](inputs.md)
- [Squad Organization](squad-organization.md)
