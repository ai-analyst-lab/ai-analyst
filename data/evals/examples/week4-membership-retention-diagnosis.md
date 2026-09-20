# Course-provided Week 4 diagnosis fallback

**Status:** supplied labeled evidence, not student execution  
**Use only when:** the student's Session 6 diagnosis is missing, incomplete, or unsuitable for a context change

## Observed problem

A general membership-retention context trace supplies both the current membership-retention definition and a stale archived-dashboard definition. The current task does not ask for a historical or archived metric.

## Classification

- Problem type: context delivery
- Target workflow: membership-retention analysis
- Observed risk: two incompatible definitions are eligible for the same current-metric request
- What is not established: whether every engine selects the stale definition, how often the failure occurs, or whether changing delivery improves unrelated cases

## Evidence to inspect

- Current context: `.knowledge/datasets/novamart/metrics/membership_retention.yaml`
- Legacy context: `.knowledge/datasets/novamart/proposals/conflicting-retention-definition.yaml`
- Proposed change record: `data/context-examples/session-8-retention-proposal.yaml`
- Target evaluation case: `membership-retention-current`
- Regression cases: `completed-revenue` and `historical-active-members`

## Week 4 question

Can the system restrict the legacy definition to explicitly historical, archived, or month-end-dashboard intent while preserving the current definition and the two named regression behaviors?

Do not treat this file as a completed student diagnosis or proof that the proposed change works. It is a course-provided starting point whose evidence must still be inspected.
