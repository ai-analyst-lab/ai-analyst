"""
Unit tests for helpers/validation/structural_validator.py.

20 test cases across 6 test classes covering all public functions:
validate_schema, validate_primary_key, validate_completeness,
validate_date_range, validate_referential_integrity, validate_value_domain,
validate_row_count, and run_structural_checks.

All tests use synthetic in-memory DataFrames -- no external files needed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from helpers.validation.structural_validator import (
    validate_schema,
    validate_primary_key,
    validate_completeness,
    validate_date_range,
    validate_referential_integrity,
    validate_value_domain,
    validate_row_count,
    run_structural_checks,
)


# ============================================================
# Test data factories
# ============================================================

def _make_users(n: int = 50) -> pd.DataFrame:
    """Deterministic user DataFrame."""
    return pd.DataFrame({
        "user_id": range(1, n + 1),
        "name": [f"User {i}" for i in range(1, n + 1)],
        "signup_date": pd.date_range("2024-01-01", periods=n, freq="D"),
        "plan": np.random.default_rng(42).choice(
            ["free", "pro", "enterprise"], size=n,
        ),
    })


def _make_orders(n: int = 100, max_user: int = 50) -> pd.DataFrame:
    """Deterministic order DataFrame."""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "order_id": range(1, n + 1),
        "user_id": rng.integers(1, max_user + 1, size=n),
        "order_date": pd.date_range("2024-01-01", periods=n, freq="6h"),
        "amount": np.round(rng.lognormal(3.5, 1.0, n), 2),
        "status": rng.choice(
            ["completed", "cancelled", "pending"], size=n,
        ),
    })


# ============================================================
# TestValidateSchema
# ============================================================

class TestValidateSchema:

    def test_valid_schema_passes(self):
        df = _make_users()
        result = validate_schema(
            df,
            expected_columns=["user_id", "name", "signup_date", "plan"],
        )
        assert result["ok"] is True
        assert result["issues"] == []
        assert result["missing_columns"] == []

    def test_missing_column_fails(self):
        df = _make_users()
        result = validate_schema(
            df,
            expected_columns=["user_id", "email", "nonexistent"],
        )
        assert result["ok"] is False
        assert "email" in result["missing_columns"]
        assert "nonexistent" in result["missing_columns"]
        assert len(result["issues"]) == 2

    def test_extra_columns_ok(self):
        df = _make_users()
        result = validate_schema(
            df,
            expected_columns=["user_id"],
        )
        assert result["ok"] is True
        # Extra columns are informational, not failures
        assert "name" in result["extra_columns"]
        assert "signup_date" in result["extra_columns"]

    def test_wrong_type_warns(self):
        df = _make_users()
        result = validate_schema(
            df,
            expected_types={"user_id": "object"},  # actually int64
        )
        assert result["ok"] is True  # type mismatch is a warning, not an issue
        assert len(result["warnings"]) >= 1
        assert len(result["dtype_mismatches"]) >= 1
        assert result["severity"] == "WARNING"

    def test_empty_df_passes_schema(self):
        df = pd.DataFrame({"a": pd.Series(dtype="int64"),
                           "b": pd.Series(dtype="object")})
        result = validate_schema(df, expected_columns=["a", "b"])
        assert result["ok"] is True
        assert result["missing_columns"] == []


# ============================================================
# TestValidatePrimaryKey
# ============================================================

class TestValidatePrimaryKey:

    def test_unique_pk_passes(self):
        df = _make_users()
        result = validate_primary_key(df, key_columns=["user_id"])
        assert result["ok"] is True
        assert result["duplicate_count"] == 0
        assert result["null_count"] == 0

    def test_duplicate_pk_fails(self):
        df = pd.DataFrame({
            "id": [1, 2, 3, 3, 4],
            "val": ["a", "b", "c", "d", "e"],
        })
        result = validate_primary_key(df, key_columns=["id"])
        assert result["ok"] is False
        assert result["duplicate_count"] >= 1
        assert len(result["duplicate_sample"]) > 0

    def test_composite_pk(self):
        df = pd.DataFrame({
            "a": [1, 1, 2, 2],
            "b": ["x", "y", "x", "y"],
            "val": [10, 20, 30, 40],
        })
        result = validate_primary_key(df, key_columns=["a", "b"])
        assert result["ok"] is True
        assert result["duplicate_count"] == 0

    def test_null_in_pk_fails(self):
        df = pd.DataFrame({
            "id": [1, 2, None, 4],
            "val": ["a", "b", "c", "d"],
        })
        result = validate_primary_key(df, key_columns=["id"])
        assert result["ok"] is False
        assert result["null_count"] >= 1
        assert result["severity"] == "BLOCKER"


# ============================================================
# TestValidateCompleteness
# ============================================================

class TestValidateCompleteness:

    def test_complete_data_passes(self):
        df = _make_users()
        result = validate_completeness(
            df,
            required_columns=["user_id", "name"],
            threshold=0.95,
        )
        assert result["ok"] is True
        for stat in result["column_stats"]:
            assert stat["passes_threshold"] is True
            assert stat["null_rate"] == 0.0

    def test_null_column_fails_threshold(self):
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "b": [1, None, None, None, None, None, None, None, None, None],
        })
        result = validate_completeness(
            df,
            required_columns=["a", "b"],
            threshold=0.95,
        )
        assert result["ok"] is False
        b_stat = next(s for s in result["column_stats"] if s["name"] == "b")
        assert b_stat["passes_threshold"] is False
        assert b_stat["null_rate"] == 0.9

    def test_custom_threshold(self):
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5, 6, 7, 8, 9, None],  # 10% nulls
        })
        # With threshold 0.80 (20% nulls allowed), this should pass
        result_pass = validate_completeness(df, required_columns=["a"], threshold=0.80)
        a_stat = next(s for s in result_pass["column_stats"] if s["name"] == "a")
        assert a_stat["passes_threshold"] is True

        # With threshold 0.95 (only 5% nulls allowed), this should fail
        result_fail = validate_completeness(df, required_columns=["a"], threshold=0.95)
        a_stat2 = next(s for s in result_fail["column_stats"] if s["name"] == "a")
        assert a_stat2["passes_threshold"] is False

    def test_all_null_column(self):
        df = pd.DataFrame({
            "a": [None, None, None, None, None],
        })
        result = validate_completeness(df, required_columns=["a"])
        assert result["ok"] is False
        a_stat = next(s for s in result["column_stats"] if s["name"] == "a")
        assert a_stat["null_rate"] == 1.0
        assert a_stat["passes_threshold"] is False
        assert a_stat["severity"] == "BLOCKER"


# ============================================================
# TestValidateDateRange
# ============================================================

class TestValidateDateRange:

    def test_valid_date_range(self):
        df = pd.DataFrame({
            "event_date": pd.date_range("2024-01-01", periods=30, freq="D"),
        })
        result = validate_date_range(
            df,
            date_column="event_date",
            expected_start="2024-01-01",
            expected_end="2024-01-30",
        )
        assert result["ok"] is True
        assert result["actual_start"] == "2024-01-01"
        assert result["actual_end"] == "2024-01-30"
        assert result["gaps"] == []

    def test_gap_detection(self):
        # Create dates with a 5-day gap
        dates = list(pd.date_range("2024-01-01", "2024-01-10", freq="D"))
        dates += list(pd.date_range("2024-01-16", "2024-01-20", freq="D"))
        df = pd.DataFrame({"event_date": dates})
        result = validate_date_range(
            df,
            date_column="event_date",
            max_gap_days=2,
        )
        assert result["ok"] is False
        assert len(result["gaps"]) >= 1
        # The gap should be around 5 days (Jan 10 -> Jan 16)
        assert result["gaps"][0]["gap_days"] >= 5

    def test_out_of_range_dates(self):
        df = pd.DataFrame({
            "event_date": pd.date_range("2024-03-01", periods=10, freq="D"),
        })
        result = validate_date_range(
            df,
            date_column="event_date",
            expected_start="2024-01-01",
            expected_end="2024-02-28",
        )
        assert result["ok"] is False
        assert len(result["issues"]) >= 1
        # Data starts after expected end
        assert any("2024-03-01" in issue for issue in result["issues"])


# ============================================================
# TestValidateReferentialIntegrity
# ============================================================

class TestValidateReferentialIntegrity:

    def test_valid_fk_passes(self):
        users = _make_users(50)
        orders = _make_orders(100, max_user=50)
        result = validate_referential_integrity(
            df_child=orders,
            df_parent=users,
            child_key="user_id",
            parent_key="user_id",
        )
        assert result["ok"] is True
        assert result["orphan_count"] == 0
        assert result["orphan_sample"] == []

    def test_orphan_records_fails(self):
        users = pd.DataFrame({"user_id": [1, 2, 3]})
        orders = pd.DataFrame({
            "order_id": [1, 2, 3],
            "user_id": [1, 2, 999],  # 999 does not exist in users
        })
        result = validate_referential_integrity(
            df_child=orders,
            df_parent=users,
            child_key="user_id",
            parent_key="user_id",
        )
        assert result["ok"] is False
        assert result["orphan_count"] >= 1
        assert 999 in result["orphan_sample"]


# ============================================================
# TestRunStructuralChecks
# ============================================================

class TestRunStructuralChecks:

    def test_orchestrator_runs_all(self):
        users = _make_users(50)
        orders = _make_orders(100, max_user=50)
        result = run_structural_checks(
            orders,
            config={
                "expected_columns": ["order_id", "user_id", "order_date",
                                     "amount", "status"],
                "primary_key": ["order_id"],
                "required_columns": ["order_id", "user_id", "amount"],
                "completeness_threshold": 0.95,
                "date_column": "order_date",
                "parent_df": users,
                "child_key": "user_id",
                "parent_key": "user_id",
                "min_rows": 1,
                "max_rows": 10000,
                "value_domain": {
                    "column": "status",
                    "valid_values": ["completed", "cancelled", "pending"],
                },
            },
        )
        assert result["checks_run"] >= 6
        assert result["overall_ok"] is True
        assert result["checks_passed"] == result["checks_run"]
        assert result["checks_failed"] == 0
        # All detail keys present
        assert "schema" in result["details"]
        assert "primary_key" in result["details"]
        assert "completeness" in result["details"]
        assert "date_range" in result["details"]
        assert "referential_integrity" in result["details"]
        assert "value_domain" in result["details"]
        assert "row_count" in result["details"]

    def test_orchestrator_with_config(self):
        df = pd.DataFrame({
            "id": [1, 2, 2],
            "val": [10, 20, 30],
        })
        result = run_structural_checks(
            df,
            config={
                "primary_key": ["id"],
                "min_rows": 1,
            },
        )
        assert result["overall_ok"] is False
        assert result["checks_failed"] >= 1
        pk_detail = result["details"]["primary_key"]
        assert pk_detail["ok"] is False
        assert pk_detail["duplicate_count"] >= 1
