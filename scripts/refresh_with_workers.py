"""
Script para ejecutar recursos con workers en paralelo
Permite procesar múltiples resources simultáneamente usando ThreadPoolExecutor
"""
import sys
import os
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models import Resource
from app.manager.fetcher_manager import FetcherManager


def process_resource(resource_id: str) -> dict:
    """
    Worker function - procesa un resource completo

    Args:
        resource_id: ID del resource a procesar

    Returns:
        dict con resultado de la ejecución
    """
    session = SessionLocal()
    result = {
        'resource_id': resource_id,
        'success': False,
        'error': None,
        'resource_name': None
    }

    try:
        # Get resource info
        resource = session.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            result['error'] = f"Resource {resource_id} not found"
            return result

        result['resource_name'] = resource.name

        print(f"[Worker] 🔄 Processing: {resource.name}")

        # Execute the resource
        FetcherManager.run(session, resource_id)

        result['success'] = True
        print(f"[Worker] ✅ Completed: {resource.name}")

    except Exception as e:
        result['error'] = str(e)
        print(f"[Worker] ❌ Error in {result.get('resource_name', resource_id)}: {e}")

    finally:
        session.close()

    return result


def run_with_workers(max_workers: int = 4, resource_ids: list = None):
    """
    Ejecuta resources usando workers en paralelo

    Args:
        max_workers: Número máximo de workers simultáneos (default: 4)
        resource_ids: Lista de resource IDs a procesar (None = todos los activos)
    """
    session = SessionLocal()

    try:
        # Get resources to process
        if resource_ids:
            resources = session.query(Resource).filter(
                Resource.id.in_(resource_ids),
                Resource.active == True
            ).all()
        else:
            resources = session.query(Resource).filter(
                Resource.active == True
            ).all()

        if not resources:
            print("⚠️  No active resources to process")
            return

        resource_ids_to_process = [str(r.id) for r in resources]

        print("=" * 70)
        print(f"🚀 Starting parallel execution")
        print(f"   Workers: {max_workers}")
        print(f"   Resources: {len(resource_ids_to_process)}")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        # List resources to process
        for i, resource in enumerate(resources, 1):
            print(f"{i}. {resource.name} ({resource.fetcher.code})")
        print()

        start_time = datetime.now()

        # Execute with ThreadPoolExecutor (for I/O-bound tasks)
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_resource = {
                executor.submit(process_resource, rid): rid
                for rid in resource_ids_to_process
            }

            # Collect results as they complete
            for future in as_completed(future_to_resource):
                result = future.result()
                results.append(result)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Print summary
        print()
        print("=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)

        success_count = sum(1 for r in results if r['success'])
        error_count = len(results) - success_count

        print(f"Total resources: {len(results)}")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {error_count}")
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"⚡ Avg per resource: {duration/len(results):.2f}s")
        print()

        # List failed resources
        if error_count > 0:
            print("Failed resources:")
            for result in results:
                if not result['success']:
                    print(f"  ❌ {result['resource_name'] or result['resource_id']}")
                    print(f"     Error: {result['error']}")
            print()

        print("=" * 70)

    finally:
        session.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Execute resources with parallel workers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute all active resources with 4 workers (default)
  python scripts/refresh_with_workers.py

  # Execute with 8 workers
  python scripts/refresh_with_workers.py --workers 8

  # Execute specific resources
  python scripts/refresh_with_workers.py --resources <uuid1> <uuid2>

  # Execute with 1 worker (sequential)
  python scripts/refresh_with_workers.py --workers 1
        """
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )

    parser.add_argument(
        '--resources',
        nargs='+',
        help='Specific resource IDs to process (default: all active)'
    )

    args = parser.parse_args()

    # Validate workers
    if args.workers < 1:
        print("Error: --workers must be >= 1")
        sys.exit(1)

    if args.workers > 20:
        print("Warning: Using more than 20 workers may cause issues")
        print("Are you sure? (y/n): ", end='')
        if input().lower() != 'y':
            sys.exit(0)

    # Run
    run_with_workers(
        max_workers=args.workers,
        resource_ids=args.resources
    )


if __name__ == "__main__":
    main()
