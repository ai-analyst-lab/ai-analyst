# Operator guide

1. Review `system-manifest.yaml`, `autonomy-policy.yaml`, and `LIMITATIONS.md`.
2. Copy `request.example.json` and change only the request ID and bounded question.
3. From the AI Analyst repository, prompt Claude to inspect the package and run `python -m helpers.operations.operator examples/analyst-v1/system-manifest.yaml YOUR_REQUEST.json`.
4. Inspect the receipt in `working/operator-receipts/`.
5. Do not share the result unless the required evaluation and human review are complete.

If a request is blocked, do not weaken the policy. Record the missing access or approval and escalate to the owner.
