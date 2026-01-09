"""
Test script for STAGE phase implementation.
Tests EXTRACT -> STAGE pipeline.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Resource, ResourceExecution
from app.manager.fetcher_manager import FetcherManager

def main():
    """Test the STAGE phase"""
    with SessionLocal() as session:
        # Get first active resource
        resource = session.query(Resource).filter(Resource.active == True).first()

        if not resource:
            print("No active resources found. Creating a test resource...")
            print("Please configure at least one active resource in the database.")
            return

        print(f"Testing STAGE phase with resource: {resource.name}")
        print(f"Resource ID: {resource.id}")
        print()

        # Run the pipeline
        try:
            execution = FetcherManager.run(session, str(resource.id))

            if execution:
                print()
                print("Execution details:")
                print(f"  - ID: {execution.id}")
                print(f"  - Status: {execution.status}")
                print(f"  - Total records: {execution.total_records}")
                print(f"  - Staging path: {execution.staging_path}")
                print(f"  - Started at: {execution.started_at}")
                print(f"  - Completed at: {execution.completed_at}")

                # Verify file exists
                if execution.staging_path:
                    from pathlib import Path
                    staging_file = Path(execution.staging_path)
                    if staging_file.exists():
                        size = staging_file.stat().st_size
                        print(f"  - File size: {size} bytes")
                        print()
                        print("[OK] STAGE phase working correctly!")
                    else:
                        print()
                        print("[ERROR] Staging file not found!")
                else:
                    print()
                    print("[ERROR] No staging path recorded!")
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
