#!/usr/bin/env python3
"""
Snowflake Setup Validation Script

This script validates your Snowflake connection setup for AI Analyst.

Usage:
    python scripts/validate_snowflake_setup.py

Prerequisites:
    - .env file with SNOWFLAKE_* variables set
    - snowflake-connector-python installed
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_env_vars():
    """Check if required environment variables are set."""
    print("=" * 60)
    print("STEP 1: Environment Variables")
    print("=" * 60)

    required_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
    ]

    optional_vars = [
        "SNOWFLAKE_ROLE",
        "SNOWFLAKE_SCHEMA",
        "DBT_PROJECT_PATH",
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask password
            display = "***" if "PASSWORD" in var else value
            print(f"  ✓ {var}: {display}")
        else:
            print(f"  ✗ {var}: NOT SET")
            missing.append(var)

    print("\nOptional:")
    for var in optional_vars:
        value = os.getenv(var)
        display = value if value else "(not set)"
        print(f"    {var}: {display}")

    if missing:
        print(f"\n❌ Missing required variables: {', '.join(missing)}")
        print("\nTo fix:")
        print("  1. Copy .env.example to .env")
        print("  2. Fill in your Snowflake credentials")
        print("  3. Run this script again")
        return False

    print("\n✅ All required environment variables are set")
    return True


def check_package():
    """Check if snowflake-connector-python is installed."""
    print("\n" + "=" * 60)
    print("STEP 2: Python Package")
    print("=" * 60)

    try:
        import snowflake.connector
        version = snowflake.connector.__version__
        print(f"  ✓ snowflake-connector-python installed (version {version})")
        return True
    except ImportError:
        print("  ✗ snowflake-connector-python NOT INSTALLED")
        print("\nTo fix:")
        print("  pip install snowflake-connector-python")
        return False


def test_connection():
    """Test the Snowflake connection."""
    print("\n" + "=" * 60)
    print("STEP 3: Connection Test")
    print("=" * 60)

    try:
        import snowflake.connector

        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            role=os.getenv("SNOWFLAKE_ROLE", "ANALYST"),
        )

        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()")
        row = cursor.fetchone()

        print(f"  ✓ Connected to Snowflake")
        print(f"    Version: {row[0]}")
        print(f"    Warehouse: {row[1]}")
        print(f"    Database: {row[2]}")

        cursor.close()
        conn.close()

        return True

    except Exception as exc:
        print(f"  ✗ Connection failed: {exc}")
        print("\nCommon fixes:")
        print("  - Check account format: account.region (e.g., xy12345.us-east-1)")
        print("  - Verify username and password")
        print("  - Confirm warehouse is running")
        print("  - Check network access (VPN, firewall)")
        return False


def check_schema():
    """Check if the analytics_prod schema exists and is accessible."""
    print("\n" + "=" * 60)
    print("STEP 4: Schema Validation")
    print("=" * 60)

    try:
        import snowflake.connector

        schema = os.getenv("SNOWFLAKE_SCHEMA", "analytics_prod")

        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            role=os.getenv("SNOWFLAKE_ROLE", "ANALYST"),
            schema=schema,
        )

        cursor = conn.cursor()

        # List tables in the schema
        cursor.execute(f"""
            SELECT table_name, row_count
            FROM {os.getenv('SNOWFLAKE_DATABASE')}.information_schema.tables
            WHERE table_schema = UPPER('{schema}')
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            LIMIT 20
        """)

        tables = cursor.fetchall()

        if tables:
            print(f"  ✓ Schema '{schema}' exists with {len(tables)} tables:")
            for table_name, row_count in tables[:10]:
                rc_str = f"{row_count:,}" if row_count else "unknown"
                print(f"    - {table_name} ({rc_str} rows)")

            if len(tables) > 10:
                print(f"    ... and {len(tables) - 10} more tables")
        else:
            print(f"  ⚠ Schema '{schema}' exists but has no tables")
            print("\nThis might be OK if:")
            print("  - You're setting up for the first time")
            print("  - Tables are in a different schema")

        cursor.close()
        conn.close()

        return True

    except Exception as exc:
        print(f"  ✗ Schema check failed: {exc}")
        print(f"\nMake sure schema '{schema}' exists and your role has SELECT permissions")
        return False


def check_dbt():
    """Check dbt integration if configured."""
    print("\n" + "=" * 60)
    print("STEP 5: dbt Integration (Optional)")
    print("=" * 60)

    dbt_path = os.getenv("DBT_PROJECT_PATH")

    if not dbt_path:
        print("  ⊘ DBT_PROJECT_PATH not set (skipping)")
        return True

    dbt_path = Path(dbt_path)

    if not dbt_path.exists():
        print(f"  ✗ dbt project not found at: {dbt_path}")
        return False

    dbt_yml = dbt_path / "dbt_project.yml"
    if not dbt_yml.exists():
        print(f"  ✗ dbt_project.yml not found in: {dbt_path}")
        return False

    print(f"  ✓ dbt project found at: {dbt_path}")

    # Check for models directory
    models_dir = dbt_path / "models"
    if models_dir.exists():
        model_count = len(list(models_dir.rglob("*.sql")))
        print(f"  ✓ Found {model_count} SQL models")

    return True


def check_dataset_config():
    """Check if dataset configuration exists."""
    print("\n" + "=" * 60)
    print("STEP 6: Dataset Configuration")
    print("=" * 60)

    dataset_dir = project_root / ".knowledge" / "datasets" / "analytics_prod"

    files = [
        "manifest.yaml",
        "schema.md",
        "quirks.md",
    ]

    all_exist = True
    for filename in files:
        filepath = dataset_dir / filename
        if filepath.exists():
            print(f"  ✓ {filename} exists")
        else:
            print(f"  ✗ {filename} NOT FOUND")
            all_exist = False

    if all_exist:
        print(f"\n✅ Dataset configuration is ready at:")
        print(f"   {dataset_dir}")
    else:
        print(f"\n❌ Some configuration files are missing")
        print(f"\nThey should have been created by the setup guide.")
        print(f"Check: {dataset_dir}")

    return all_exist


def main():
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("AI ANALYST PLUS — SNOWFLAKE SETUP VALIDATION")
    print("=" * 60)

    # Load .env if it exists
    try:
        from dotenv import load_dotenv
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✓ Loaded environment from {env_path}\n")
        else:
            print(f"⚠ No .env file found at {env_path}")
            print("  Copy .env.example to .env and fill in your credentials\n")
    except ImportError:
        print("⚠ python-dotenv not installed (pip install python-dotenv)")
        print("  Relying on system environment variables\n")

    checks = [
        ("Environment Variables", check_env_vars),
        ("Python Package", check_package),
        ("Connection", test_connection),
        ("Schema Access", check_schema),
        ("dbt Integration", check_dbt),
        ("Dataset Config", check_dataset_config),
    ]

    results = []
    for name, check_fn in checks:
        try:
            results.append(check_fn())
        except Exception as exc:
            print(f"\n❌ {name} check failed with error: {exc}")
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    for i, (name, _) in enumerate(checks):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"  {status} — {name}")

    print("\n" + "=" * 60)
    if passed == total:
        print("🎉 ALL CHECKS PASSED")
        print("\nYou're ready to use AI Analyst with Snowflake!")
        print("\nNext steps:")
        print("  1. In Claude Code: /switch-dataset analytics_prod")
        print("  2. Run: /data-profiling")
        print("  3. Try a test query: 'Show me the tables available'")
    else:
        print(f"⚠ {total - passed} CHECK(S) FAILED")
        print("\nReview the failures above and fix them before proceeding.")
        print("\nFor help, see: SETUP_SNOWFLAKE.md")

    print("=" * 60 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
