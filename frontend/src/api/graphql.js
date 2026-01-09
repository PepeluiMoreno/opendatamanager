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
  GET_SOURCES: `
    query GetSources($activeOnly: Boolean) {
      sources(activeOnly: $activeOnly) {
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

  GET_SOURCE: `
    query GetSource($id: String!) {
      source(id: $id) {
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

  PREVIEW_SOURCE_DATA: `
    query PreviewSourceData($id: String!, $limit: Int = 10) {
      previewSourceData(id: $id, limit: $limit)
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
}

// Mutations
export const MUTATIONS = {
  CREATE_SOURCE: `
    mutation CreateSource($input: CreateSourceInput!) {
      createSource(input: $input) {
        id
        name
        publisher
        targetTable
      }
    }
  `,

  UPDATE_SOURCE: `
    mutation UpdateSource($id: String!, $input: UpdateSourceInput!) {
      updateSource(id: $id, input: $input) {
        id
        name
        publisher
        targetTable
      }
    }
  `,

  DELETE_SOURCE: `
    mutation DeleteSource($id: String!) {
      deleteSource(id: $id)
    }
  `,

  EXECUTE_SOURCE: `
    mutation ExecuteSource($id: String!) {
      executeSource(id: $id) {
        success
        message
        sourceId
      }
    }
  `,

  EXECUTE_ALL_SOURCES: `
    mutation ExecuteAllSources {
      executeAllSources {
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
export async function fetchSources(activeOnly = false) {
  try {
    return await client.request(QUERIES.GET_SOURCES, { activeOnly })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchSource(id) {
  try {
    return await client.request(QUERIES.GET_SOURCE, { id })
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

export async function createSource(input) {
  try {
    return await client.request(MUTATIONS.CREATE_SOURCE, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updateSource(id, input) {
  try {
    return await client.request(MUTATIONS.UPDATE_SOURCE, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteSource(id) {
  try {
    return await client.request(MUTATIONS.DELETE_SOURCE, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function executeSource(id) {
  try {
    return await client.request(MUTATIONS.EXECUTE_SOURCE, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function executeAllSources() {
  try {
    return await client.request(MUTATIONS.EXECUTE_ALL_SOURCES)
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

export async function previewSourceData(id, limit = 10) {
  try {
    return await client.request(QUERIES.PREVIEW_SOURCE_DATA, { id, limit })
  } catch (error) {
    handleGraphQLError(error)
  }
}
