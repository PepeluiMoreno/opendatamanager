"""
Test GraphQL queries para datasets.
Prueba las nuevas queries agregadas al schema.
"""
import requests
import json

GRAPHQL_URL = "http://localhost:8040/graphql"


def test_query(query, variables=None):
    """Ejecuta una query GraphQL y retorna el resultado"""
    response = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables or {}},
        headers={"Content-Type": "application/json"}
    )
    return response.json()


def main():
    print("Testing GraphQL Dataset Queries")
    print("=" * 50)

    # Test 1: List all datasets
    print("\n1. Listing all datasets:")
    query1 = """
    query {
      datasets {
        id
        version
        resourceId
        recordCount
        createdAt
        downloadUrls
      }
    }
    """
    result1 = test_query(query1)
    if "errors" in result1:
        print(f"  ERROR: {result1['errors']}")
    else:
        datasets = result1.get("data", {}).get("datasets", [])
        print(f"  Found {len(datasets)} datasets")
        for art in datasets[:3]:  # Show first 3
            print(f"    - {art['version']} ({art['recordCount']} records)")

    # Test 2: Get specific dataset
    if datasets:
        dataset_id = datasets[0]["id"]
        print(f"\n2. Getting dataset {dataset_id}:")
        query2 = """
        query GetDataset($id: String!) {
          dataset(id: $id) {
            id
            version
            majorVersion
            minorVersion
            patchVersion
            resourceId
            checksum
            downloadUrls
          }
        }
        """
        result2 = test_query(query2, {"id": dataset_id})
        if "errors" in result2:
            print(f"  ERROR: {result2['errors']}")
        else:
            dataset = result2.get("data", {}).get("dataset")
            if dataset:
                print(f"  Version: {dataset['version']}")
                print(f"  Checksum: {dataset['checksum'][:16]}...")
                print(f"  Download URLs:")
                for key, url in dataset['downloadUrls'].items():
                    print(f"    - {key}: {url}")

    # Test 3: List resource executions
    print("\n3. Listing resource executions:")
    query3 = """
    query {
      resourceExecutions {
        id
        resourceId
        status
        totalRecords
        recordsLoaded
        startedAt
        completedAt
      }
    }
    """
    result3 = test_query(query3)
    if "errors" in result3:
        print(f"  ERROR: {result3['errors']}")
    else:
        executions = result3.get("data", {}).get("resourceExecutions", [])
        print(f"  Found {len(executions)} executions")
        for exe in executions[:3]:
            print(f"    - {exe['status']}: {exe['totalRecords']} records")

    # Test 4: List dataset subscriptions
    print("\n4. Listing dataset subscriptions:")
    query4 = """
    query {
      datasetSubscriptions {
        id
        applicationId
        resourceId
        pinnedVersion
        autoUpgrade
        currentVersion
      }
    }
    """
    result4 = test_query(query4)
    if "errors" in result4:
        print(f"  ERROR: {result4['errors']}")
    else:
        subs = result4.get("data", {}).get("datasetSubscriptions", [])
        print(f"  Found {len(subs)} subscriptions")
        for sub in subs:
            print(f"    - App {sub['applicationId'][:8]}... pinned to {sub.get('pinnedVersion', 'none')}")

    print("\n" + "=" * 50)
    print("GraphQL tests completed!")


if __name__ == "__main__":
    main()
