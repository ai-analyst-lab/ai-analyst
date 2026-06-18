---
title: "Workflows Index"
type: workflow-index
schema_version: 1
build_label: amplitude-pre-read-v1
workflow_scope: mvp_3
created: 2026-05-26
updated: 2026-05-26
---

# Workflows Index

Operational workflows derived from the Amplitude North Star Playbook. Each workflow ships as a pair: a narrative `.md` (human-readable) and an `_steps/{id}.yaml` (machine contract consumed by `get_workflow_steps()` at runtime).

## v1 MVP Workflows (shipped)

| Workflow | When to use | Steps | Est. time |
|----------|-------------|-------|-----------|
| [Cold Start](cold-start.md) | You have a product but no documented NSM | 8 | ~90-115 min |
| [Audit](audit.md) | You have an existing NSM and want to validate it against the 7-checklist | 7 | ~30 min |
| [Vanity Triage](vanity-triage.md) | You have a list of candidate metrics and need to sort signal from vanity | 4 | ~15 min |

## How to choose

- **No NSM yet?** → [Cold Start](cold-start.md)
- **NSM exists, need to defend or remediate?** → [Audit](audit.md)
- **Multiple candidates competing for the NSM seat?** → [Vanity Triage](vanity-triage.md), then [Cold Start](cold-start.md) on the shortlist
- **Audit failed ≥3 of 7?** → Re-run [Cold Start](cold-start.md) rather than patch
- **Cold Start produced an NSM?** → Run [Audit](audit.md) on it before socializing

## v1.1 Candidates (deferred — not in v1 wiki)

These workflows have step atoms extracted but are out of scope for v1 (`workflow_scope: mvp_3`). They will ship in a later build.

| Workflow | Source atom(s) | Why deferred |
|----------|----------------|--------------|
| `nsm-evolution` | `workflow-step-p045-l1052-nsm-evolution-step-1-detect-divergence` + 2 more | Tracks evolution after launch; needs temporal-tracker agent (also deferred) |
| `workshop-facilitation` | `workflow-step-p010-l0216-workshop-step-1-convene` + 1 more | Facilitation-specific; out of v1 scope |
| `make-it-stick` | `workflow-step-p044-l1032-make-it-stick-step-1-secure-sponsor` | Post-launch socialization; covered narratively in `concepts/make-the-nsm-stick.md` |
| `share-your-work` | `workflow-step-p033-l0736-share-your-work-step-1-socialize-broadly` | One-step "workflow"; folded into Audit Step 2 narrative |
| `present-thinking-check` | `workflow-step-p047-l1099-present-check-step-1-questions` | Belongs in the `gap-thinking-vs-present-thinking` concept |
| `start-small` | `workflow-step-p042-l0976-start-small-step-1-pick-impactable-scope` | One-step "workflow"; covered in Cold Start Step 8 (Greenfield)|

Atoms remain in `raw/atoms/workflow-steps/` for the v1.1 build.

## Machine contract

The runtime `/north-star` skill calls `get_workflow_steps(workflow_id)` and parses `wiki/workflows/_steps/{workflow_id}.yaml` directly. The narrative `.md` is for human browsing and skill explanations. If the two disagree, the YAML is canonical.

Schema: `wiki/SCHEMAS/WorkflowDefinition.yaml` (machine) and `wiki/SCHEMAS/WorkflowArticle.yaml` (narrative).
