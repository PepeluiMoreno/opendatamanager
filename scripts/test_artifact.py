"""
Test script for complete EXTRACT -> STAGE -> ARTIFACT pipeline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Resource, Artifact
from app.manager.fetcher_manager import FetcherManager

def main():
    """Test the full pipeline"""
    with SessionLocal() as session:
        # Get first active resource
        resource = session.query(Resource).filter(Resource.active == True).first()

        if not resource:
            print("No active resources found.")
            return

        print(f"Testing full pipeline with resource: {resource.name}")
        print(f"Resource ID: {resource.id}")
        print()

        # Run the pipeline
        try:
            artifact = FetcherManager.run(session, str(resource.id))

            if artifact:
                print()
                print("Artifact details:")
                print(f"  - ID: {artifact.id}")
                print(f"  - Version: {artifact.version_string}")
                print(f"  - Record count: {artifact.record_count}")
                print(f"  - Data path: {artifact.data_path}")
                print(f"  - Checksum: {artifact.checksum}")

                # Verify all files exist
                artifact_dir = Path(artifact.data_path).parent
                files = {
                    "data.jsonl": artifact_dir / "data.jsonl",
                    "schema.json": artifact_dir / "schema.json",
                    "models.py": artifact_dir / "models.py",
                    "metadata.json": artifact_dir / "metadata.json"
                }

                print()
                print("Package files:")
                all_exist = True
                for name, path in files.items():
                    if path.exists():
                        size = path.stat().st_size
                        print(f"  [OK] {name} ({size} bytes)")
                    else:
                        print(f"  [MISSING] {name}")
                        all_exist = False

                if all_exist:
                    print()
                    print("[OK] Full pipeline working correctly!")
                else:
                    print()
                    print("[ERROR] Some files are missing!")
        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
