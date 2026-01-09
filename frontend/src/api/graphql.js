import { GraphQLClient } from 'graphql-request'

const endpoint = 'http://localhost:8040/graphql'

export const client = new GraphQLClient(endpoint, {
  headers: {
    'Content-Type': 'application/json',
  },
})

// Helper to handle errors with better messages
function handleGraphQLError(error) {
  // Just pass through the original error - let components handle the display
  throw error
}

// Queries
export const QUERIES = {
  GET_RESOURCES: `
    query GetResources($activeOnly: Boolean) {
      resources(activeOnly: $activeOnly) {
        id
        name
        publisher
        targetTable
        active
        fetcherType {
          id
          code
          classPath
          description
        }
        params {
          id
          key
          value
        }
      }
    }
  `,

  GET_RESOURCE: `
    query GetResource($id: String!) {
      resource(id: $id) {
        id
        name
        publisher
        targetTable
        active
        fetcherType {
          id
          code
          classPath
          description
        }
        params {
          id
          key
          value
        }
      }
    }
  `,

  PREVIEW_RESOURCE_DATA: `
    query PreviewResourceData($id: String!, $limit: Int = 10) {
      previewResourceData(id: $id, limit: $limit)
    }
  `,

  GET_FETCHER_TYPES: `
    query GetFetcherTypes {
      fetcherTypes {
        id
        code
        classPath
        description
      }
    }
  `,

  GET_APPLICATIONS: `
    query GetApplications {
      applications {
        id
        name
        description
        modelsPath
        subscribedProjects
        active
      }
    }
  `,

  GET_FIELD_METADATA: `
    query GetFieldMetadata($tableName: String!) {
      fieldMetadata(tableName: $tableName) {
        id
        tableName
        fieldName
        label
        helpText
        placeholder
      }
    }
  `,

  GET_ARTIFACTS: `
    query GetArtifacts($resourceId: String) {
      artifacts(resourceId: $resourceId) {
        id
        resourceId
        version
        majorVersion
        minorVersion
        patchVersion
        schemaJson
        recordCount
        createdAt
        downloadUrls
      }
    }
  `,

  GET_RESOURCE_EXECUTIONS: `
    query GetResourceExecutions($resourceId: String) {
      resourceExecutions(resourceId: $resourceId) {
        id
        resourceId
        startedAt
        completedAt
        status
        totalRecords
        recordsLoaded
        errorMessage
      }
    }
  `,
}

// Mutations
export const MUTATIONS = {
  CREATE_RESOURCE: `
    mutation CreateResource($input: CreateResourceInput!) {
      createResource(input: $input) {
        id
        name
        publisher
        targetTable
      }
    }
  `,

  UPDATE_RESOURCE: `
    mutation UpdateResource($id: String!, $input: UpdateResourceInput!) {
      updateResource(id: $id, input: $input) {
        id
        name
        publisher
        targetTable
      }
    }
  `,

  DELETE_RESOURCE: `
    mutation DeleteResource($id: String!) {
      deleteResource(id: $id)
    }
  `,

  EXECUTE_RESOURCE: `
    mutation ExecuteResource($id: String!) {
      executeResource(id: $id) {
        success
        message
        resourceId
      }
    }
  `,

  EXECUTE_ALL_RESOURCES: `
    mutation ExecuteAllResources {
      executeAllResources {
        success
        message
      }
    }
  `,

  CREATE_APPLICATION: `
    mutation CreateApplication($input: CreateApplicationInput!) {
      createApplication(input: $input) {
        id
        name
      }
    }
  `,

  UPDATE_APPLICATION: `
    mutation UpdateApplication($id: String!, $input: UpdateApplicationInput!) {
      updateApplication(id: $id, input: $input) {
        id
        name
      }
    }
  `,

  DELETE_APPLICATION: `
    mutation DeleteApplication($id: String!) {
      deleteApplication(id: $id)
    }
  `,

  CREATE_FETCHER_TYPE: `
    mutation CreateFetcherType($input: CreateFetcherTypeInput!) {
      createFetcherType(input: $input) {
        id
        code
        classPath
        description
      }
    }
  `,

  UPDATE_FETCHER_TYPE: `
    mutation UpdateFetcherType($id: String!, $input: UpdateFetcherTypeInput!) {
      updateFetcherType(id: $id, input: $input) {
        id
        code
        classPath
        description
      }
    }
  `,

  DELETE_FETCHER_TYPE: `
    mutation DeleteFetcherType($id: String!) {
      deleteFetcherType(id: $id)
    }
  `,
}

// Helper functions with error handling
export async function fetchResources(activeOnly = false) {
  try {
    return await client.request(QUERIES.GET_RESOURCES, { activeOnly })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchResource(id) {
  try {
    return await client.request(QUERIES.GET_RESOURCE, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchFetcherTypes() {
  try {
    return await client.request(QUERIES.GET_FETCHER_TYPES)
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchApplications() {
  try {
    return await client.request(QUERIES.GET_APPLICATIONS)
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchFieldMetadata(tableName) {
  try {
    return await client.request(QUERIES.GET_FIELD_METADATA, { tableName })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function createResource(input) {
  try {
    return await client.request(MUTATIONS.CREATE_RESOURCE, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updateResource(id, input) {
  try {
    return await client.request(MUTATIONS.UPDATE_RESOURCE, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteResource(id) {
  try {
    return await client.request(MUTATIONS.DELETE_RESOURCE, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function executeResource(id) {
  try {
    return await client.request(MUTATIONS.EXECUTE_RESOURCE, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function executeAllResources() {
  try {
    return await client.request(MUTATIONS.EXECUTE_ALL_RESOURCES)
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function createApplication(input) {
  try {
    return await client.request(MUTATIONS.CREATE_APPLICATION, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updateApplication(id, input) {
  try {
    return await client.request(MUTATIONS.UPDATE_APPLICATION, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteApplication(id) {
  try {
    return await client.request(MUTATIONS.DELETE_APPLICATION, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function createFetcherType(input) {
  try {
    return await client.request(MUTATIONS.CREATE_FETCHER_TYPE, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updateFetcherType(id, input) {
  try {
    return await client.request(MUTATIONS.UPDATE_FETCHER_TYPE, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteFetcherType(id) {
  try {
    return await client.request(MUTATIONS.DELETE_FETCHER_TYPE, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function previewResourceData(id, limit = 10) {
  try {
    return await client.request(QUERIES.PREVIEW_RESOURCE_DATA, { id, limit })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchArtifacts(resourceId = null) {
  try {
    return await client.request(QUERIES.GET_ARTIFACTS, { resourceId })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchResourceExecutions(resourceId = null) {
  try {
    return await client.request(QUERIES.GET_RESOURCE_EXECUTIONS, { resourceId })
  } catch (error) {
    handleGraphQLError(error)
  }
}
