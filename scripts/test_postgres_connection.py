#!/usr/bin/env python3
"""
Test script for Postgres connection setup.
Run this to verify your database connection is configured correctly.

Usage:
    python scripts/test_postgres_connection.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ psycopg2 not installed. Install it with:")
    print("   pip install psycopg2-binary")
    sys.exit(1)

def test_connection():
    """Test connection to Postgres database."""
    
    # Read connection details from environment or prompt
    host = os.getenv('POSTGRES_HOST', input("Enter Postgres host: "))
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DATABASE', input("Enter database name: "))
    user = os.getenv('POSTGRES_USER', input("Enter username: "))
    password = os.getenv('POSTGRES_PASSWORD', input("Enter password: "))
    
    print(f"\n🔌 Connecting to {host}:{port}/{database}...")
    
    try:
        # Attempt connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        
        print("✅ Connection successful!")
        
        # Test query - list tables in public schema
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        print(f"\n📊 Found {len(tables)} tables in public schema:")
        for table in tables[:10]:  # Show first 10
            print(f"   - {table[0]}")
        
        if len(tables) > 10:
            print(f"   ... and {len(tables) - 10} more")
        
        # Test camelCase column detection
        if tables:
            sample_table = tables[0][0]
            print(f"\n🔍 Checking column naming in '{sample_table}':")
            
            cursor.execute(sql.SQL("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = %s
                LIMIT 5;
            """), (sample_table,))
            
            columns = cursor.fetchall()
            has_camelcase = False
            
            for col_name, col_type in columns:
                print(f"   - {col_name} ({col_type})")
                # Check if column has camelCase (lowercase start, contains uppercase)
                if col_name[0].islower() and any(c.isupper() for c in col_name):
                    has_camelcase = True
            
            if has_camelcase:
                print("\n✅ Confirmed: This database uses camelCase column names")
                print("   Remember to quote column names in SQL queries!")
            else:
                print("\n⚠️  No camelCase columns detected in sample table")
                print("   Verify with your backend team about naming convention")
        
        cursor.close()
        conn.close()
        
        print("\n✅ All checks passed!")
        print("\n📝 Next steps:")
        print("   1. Update .knowledge/datasets/company_postgres/manifest.yaml with connection details")
        print("   2. Set POSTGRES_PASSWORD environment variable")
        print("   3. Document your tables in .knowledge/datasets/company_postgres/schema.md")
        print("   4. Run /switch-dataset company_postgres to make it active")
        
    except psycopg2.Error as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Verify host and port are correct")
        print("   - Check that your IP is whitelisted")
        print("   - Confirm username and password")
        print("   - Ensure the database name is correct")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
