"""
Test GraphQL queries para artifacts.
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
    print("Testing GraphQL Artifact Queries")
    print("=" * 50)

    # Test 1: List all artifacts
    print("\n1. Listing all artifacts:")
    query1 = """
    query {
      artifacts {
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
        artifacts = result1.get("data", {}).get("artifacts", [])
        print(f"  Found {len(artifacts)} artifacts")
        for art in artifacts[:3]:  # Show first 3
            print(f"    - {art['version']} ({art['recordCount']} records)")

    # Test 2: Get specific artifact
    if artifacts:
        artifact_id = artifacts[0]["id"]
        print(f"\n2. Getting artifact {artifact_id}:")
        query2 = """
        query GetArtifact($id: String!) {
          artifact(id: $id) {
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
        result2 = test_query(query2, {"id": artifact_id})
        if "errors" in result2:
            print(f"  ERROR: {result2['errors']}")
        else:
            artifact = result2.get("data", {}).get("artifact")
            if artifact:
                print(f"  Version: {artifact['version']}")
                print(f"  Checksum: {artifact['checksum'][:16]}...")
                print(f"  Download URLs:")
                for key, url in artifact['downloadUrls'].items():
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

    # Test 4: List artifact subscriptions
    print("\n4. Listing artifact subscriptions:")
    query4 = """
    query {
      artifactSubscriptions {
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
        subs = result4.get("data", {}).get("artifactSubscriptions", [])
        print(f"  Found {len(subs)} subscriptions")
        for sub in subs:
            print(f"    - App {sub['applicationId'][:8]}... pinned to {sub.get('pinnedVersion', 'none')}")

    print("\n" + "=" * 50)
    print("GraphQL tests completed!")


if __name__ == "__main__":
    main()
