---
name: maintain-context
description: Create or revise a business guide, reviewed query, semantic model, relationship or metric in the configured context store. Use for context authoring and migration; use improve-context for diagnosing evaluation failures and comparing changes.
---

# Maintain context

Read `docs/CONNECTED-CONTEXT.md` for the implemented commands and storage contract.
Resolve the actual context source, inspect its catalog and look for existing resources before adding another.

1. Clarify audience, meaning, scope, source and owner. Ask about missing business rules rather than
   inventing policy. Guides explain meaning; queries give reviewed examples; models/metrics supply
   supported executable relationships and calculations.
   Keep guide prose in business terms: populations, qualifying behavior, units, time rules,
   exclusions and limitations. Plain-language formulas are appropriate. Physical table/column
   mappings belong in dataset documentation or semantic models; keys/joins in models and
   relationships; executable expressions in metrics or reviewed SQL. Do not expand a guide
   into a technical recipe just to make an evaluation pass. This is our architecture choice,
   not a universal restriction on all context products.
2. Read `templates/semantic/<kind>.yaml` for a model, metric or relationship;
   use `templates/guide.yaml` or `templates/query.yaml` for guides or approved SQL entries.
   Scaffold a draft without overwriting: `python -m helpers.connected_context --dataset DATASET scaffold KIND ID`.
   Do not create a duplicate source document by default. Models, metrics and relationships are separate resources
   within one semantic layer, stored in `datasets/DATASET/semantic/{models,metrics,relationships}/`.
   Measures and dimensions belong inside models. Only add relationships when models need to join.
   Query entries reference reviewed SQL files, not saved metric requests; call metrics directly.
3. Fill the draft and typed references. A guide can be the owner-reviewed business definition itself.
   If based on an existing company document, keep that document in its original system and record
   optional `source_references` with its title, URL, owner, actual reviewed_on date and version if known.
   These citations are not automatically fetched or monitored; never invent a source or inspection.
   In guides, use `refs` for required local dependencies (or an empty list) and
   `implementations` for optional metric/query links; business approval does not approve the linked code.
   Calculations implementing a guide reference it through `refs`; review the guide before its models
   and metrics. The guide's optional reverse implementation link is not a dependency cycle.
   Reuse model/metric IDs. Keep evaluator expected outputs out of
   context. Review calculations independently and ask before executing queries if not already authorized.
4. Run the installed `validate` command. Show meaning and implementation changes separately and stop
   for the user's review. Passing tests do not approve a business policy.
   Before review, inspect the actual guide prose for field mappings, join instructions or code.
   Verify complete business meaning survived and implementation links are accurate. Validation
   alone does not check this separation. Preserve displaced technical facts in their proper
   resources, and never report old evaluation passes as evidence for revised guide content.
5. Only after explicit approval, use `review KIND ID --reviewer PERSON --approval-note NOTE
   --reviewed-on DATE --review-after DATE`. Record the real decision; do not fabricate a reviewer or
   note to make a draft executable. Review dependencies first. No publishing without authorization.
6. Test the resource and a nearby question where its rule does not apply. Preserve earlier results.
   Distinguish observed use, correctness and regression evidence; live/model tests need authority.

For migration, preview first and inspect legacy callers. Preserve the Session 7 definition and personal
context. Source/formula edits invalidate dependent reviews: do not silently refresh hashes. Unapproved
resources stay draft. Existing context improvements and before/after evals use `/improve-context`.
