from pathlib import Path

import yaml

from helpers.knowledge.context_workshop import scaffold_context_store, validate_context_store


def test_scaffold_is_sparse_and_idempotent(tmp_path: Path):
    root = tmp_path / "context"
    first = scaffold_context_store(root)
    second = scaffold_context_store(root)

    assert first["status"] == "created"
    assert second["status"] == "existing"
    assert yaml.safe_load((root / "metrics" / "index.yaml").read_text()) == []


def test_sparse_scaffold_is_valid_with_teaching_warnings(tmp_path: Path):
    root = tmp_path / "context"
    scaffold_context_store(root)
    result = validate_context_store(root)

    assert result["valid"] is True
    assert "the store contains no registered metric contracts" in result["warnings"]
    assert result["counts"]["metrics"] == 0


def test_validator_accepts_reviewed_minimal_context(tmp_path: Path):
    root = tmp_path / "context"
    scaffold_context_store(root)
    metric = {
        "id": "membership_retention",
        "name": "Membership retention",
        "aliases": ["retention rate"],
        "means": "Share of membership records currently active at period end",
        "grain": "membership",
        "numerator": "Membership records where is_current is true",
        "denominator": "All membership records",
        "window": "End of available period",
        "filters": [],
        "rejected": ["active users divided by all users"],
        "status": "reviewed",
        "owner": "membership-analytics",
        "source": "reviewed membership policy",
        "last_reviewed": "2026-09-06",
    }
    (root / "metrics" / "membership_retention.yaml").write_text(yaml.safe_dump(metric, sort_keys=False))
    (root / "metrics" / "index.yaml").write_text(
        yaml.safe_dump([{"id": "membership_retention", "path": "membership_retention.yaml"}], sort_keys=False)
    )
    entities = yaml.safe_load((root / "semantic" / "entities.yaml").read_text())
    entities["entities"].append(
        {
            "entity": "membership", "table": "memberships", "primary_key": "membership_id",
            "grain": "one row per membership record", "status": "reviewed",
            "owner": "data-platform", "last_reviewed": "2026-09-06",
        }
    )
    (root / "semantic" / "entities.yaml").write_text(yaml.safe_dump(entities, sort_keys=False))
    result = validate_context_store(root)

    assert result["valid"] is True
    assert result["counts"]["metrics"] == 1
    assert result["counts"]["entities"] == 1


def test_validator_rejects_metric_without_rejected_interpretation(tmp_path: Path):
    root = tmp_path / "context"
    scaffold_context_store(root)
    (root / "metrics" / "index.yaml").write_text("- id: retention\n")
    (root / "metrics" / "retention.yaml").write_text("id: retention\nname: Retention\nstatus: reviewed\n")

    result = validate_context_store(root)

    assert result["valid"] is False
    assert any("rejected interpretation" in error for error in result["errors"])


def test_validator_preserves_relationship_join_expression(tmp_path: Path):
    root = tmp_path / "context"
    scaffold_context_store(root)
    relationships = yaml.safe_load((root / "semantic" / "relationships.yaml").read_text())
    relationships["relationships"].append(
        {
            "id": "memberships_to_users",
            "left": "memberships",
            "right": "users",
            "on": "memberships.user_id = users.user_id",
            "cardinality": "many_to_one",
            "status": "reviewed",
            "owner": "data-platform",
            "last_reviewed": "2026-09-06",
        }
    )
    (root / "semantic" / "relationships.yaml").write_text(
        yaml.safe_dump(relationships, sort_keys=False)
    )

    result = validate_context_store(root)

    assert not any("relationship 'memberships_to_users' is missing: on" in error for error in result["errors"])
