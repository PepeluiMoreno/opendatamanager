"""
Debug script to see what the fetcher returns.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Resource
from app.fetchers.factory import FetcherFactory

def main():
    with SessionLocal() as session:
        resource = session.query(Resource).filter(Resource.active == True).first()

        if not resource:
            print("No active resources found.")
            return

        print(f"Testing fetcher for: {resource.name}")
        print()

        # Create fetcher and execute
        fetcher = FetcherFactory.create_from_resource(resource)
        data = fetcher.execute()

        print(f"Type of data: {type(data)}")
        print(f"Length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
        print()

        if isinstance(data, dict):
            print("Keys in data:")
            for key in data.keys():
                val_type = type(data[key]).__name__
                print(f"  - {key}: {val_type}")
        elif isinstance(data, list) and len(data) > 0:
            print("First item keys:")
            if isinstance(data[0], dict):
                for key in data[0].keys():
                    val_type = type(data[0][key]).__name__
                    print(f"  - {key}: {val_type}")

        print()
        print("Attempting to serialize...")
        try:
            import json
            if isinstance(data, list):
                serialized = json.dumps(data[0] if len(data) > 0 else {}, indent=2, ensure_ascii=False)
            else:
                serialized = json.dumps(data, indent=2, ensure_ascii=False)
            print(serialized)
        except TypeError as e:
            print(f"Cannot serialize: {e}")

if __name__ == "__main__":
    main()
