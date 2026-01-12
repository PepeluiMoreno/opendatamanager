#!/usr/bin/env python
"""
Script to apply execution settings migration directly via SQL.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal

def apply_migration():
    """Apply the execution settings migration"""
    session = SessionLocal()

    try:
        print("📝 Applying execution settings migration...")

        # Read SQL file
        sql_file = os.path.join(os.path.dirname(__file__), 'add_execution_settings.sql')
        with open(sql_file, 'r') as f:
            sql_content = f.read()

        # Split by semicolon and execute each statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

        for statement in statements:
            if statement:
                print(f"  Executing: {statement[:50]}...")
                session.execute(statement)

        session.commit()
        print("✅ Migration applied successfully!")
        print("\n📊 Verifying columns...")

        # Verify columns exist
        result = session.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_schema = 'opendata'
            AND table_name = 'resource'
            AND column_name IN ('max_workers', 'timeout_seconds', 'retry_attempts', 'retry_delay_seconds', 'execution_priority')
            ORDER BY column_name;
        """)

        columns = result.fetchall()
        if len(columns) == 5:
            print("✅ All 5 columns verified:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (default: {col[2]})")
        else:
            print(f"⚠️  Warning: Only {len(columns)} columns found")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    apply_migration()
