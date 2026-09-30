"""Additional process restrictions for SQL experiments.

This denies configured local answer stores and non-data network destinations.
It is not a guarantee against references copied to an unlisted host location.
Use a separate container/VM for adversarial or held-out evaluations.
"""
from pathlib import Path


def sql_worker_settings(reference_roots: list[Path]) -> dict:
    roots = [str(path.expanduser().resolve()) for path in reference_roots]
    if not roots:
        raise ValueError("declare the evaluator/reference directories before running SQL experiments")
    return {
        "permissions": {"deny": [f"Read(/{root}/**)" for root in roots]},
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "allowUnsandboxedCommands": False,
            "autoAllowBashIfSandboxed": True,
            "filesystem": {"denyRead": roots},
            "network": {
                "strictAllowlist": True,
                "allowedDomains": ["*.snowflakecomputing.com"],
            },
        },
    }
