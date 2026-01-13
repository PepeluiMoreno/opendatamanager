"""
Script to verify that the dataset system migration was successful.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect
from app.database import engine

def verify_tables():
    """Verify that all expected tables exist in opendata schema"""
    inspector = inspect(engine)

    # Get all tables in opendata schema
    tables = inspector.get_table_names(schema='opendata')

    print("Tables in opendata schema:")
    for table in sorted(tables):
        print(f"  [OK] {table}")

    # Check for expected new tables
    expected_tables = [
        'resource_execution',
        'dataset',
        'dataset_subscription',
        'application_notification'
    ]

    print("\nChecking for new dataset system tables:")
    for table in expected_tables:
        if table in tables:
            print(f"  [OK] {table} - EXISTS")
        else:
            print(f"  [MISSING] {table}")

    # Check columns in resource table
    print("\nColumns in resource table:")
    resource_columns = inspector.get_columns('resource', schema='opendata')
    for col in resource_columns:
        print(f"  - {col['name']}: {col['type']}")

    # Check if new fields were added
    resource_col_names = [col['name'] for col in resource_columns]
    new_resource_fields = ['enable_load', 'load_mode']
    print("\nChecking for new resource fields:")
    for field in new_resource_fields:
        if field in resource_col_names:
            print(f"  [OK] {field} - EXISTS")
        else:
            print(f"  [MISSING] {field}")

    # Check columns in application table
    print("\nColumns in application table:")
    application_columns = inspector.get_columns('application', schema='opendata')
    for col in application_columns:
        print(f"  - {col['name']}: {col['type']}")

    # Check if new fields were added
    app_col_names = [col['name'] for col in application_columns]
    new_app_fields = ['webhook_url', 'webhook_secret']
    print("\nChecking for new application fields:")
    for field in new_app_fields:
        if field in app_col_names:
            print(f"  [OK] {field} - EXISTS")
        else:
            print(f"  [MISSING] {field}")

    print("\nMigration verification complete!")

if __name__ == "__main__":
    verify_tables()
