import { GraphQLClient } from 'graphql-request'

const endpoint = '/graphql'

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
        description
        publisher
        publisherId
        publisherObj {
          id
          nombre
          acronimo
          nivel
          pais
          comunidadAutonoma
        }
        targetTable
        active
        schedule
        fetcher {
          id
          name
          code
          classPath
          description
        }
        params {
          id
          key
          value
          isExternal
        }
      }
    }
  `,

  GET_RESOURCE: `
    query GetResource($id: String!) {
      resource(id: $id) {
        id
        name
        description
        publisher
        targetTable
        active
        fetcher {
          id
          name
          code
          classPath
          description
        }
        params {
          id
          key
          value
          isExternal
        }
      }
    }
  `,

  PREVIEW_RESOURCE_DATA: `
    query PreviewResourceData($id: String!, $limit: Int = 10, $params: JSON) {
      previewResourceData(id: $id, limit: $limit, params: $params)
    }
  `,

  GET_APPLICATIONS: `
    query GetApplications {
      applications {
        id
        name
        description
        subscribedProjects
        active
        webhookUrl
        consumptionMode
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
    query GetDatasets($resourceId: String) {
      datasets(resourceId: $resourceId) {
        id
        resourceId
        version
        label
        executionParams
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
        executionParams
        pauseRequested
        activeSeconds
      }
    }
  `,
  GET_APP_CONFIG: `
    query GetAppConfig {
      appConfig {
        key
        value
        description
        updatedAt
      }
    }
  `,

  GET_DERIVED_DATASET_CONFIGS: `
    query GetDerivedDatasetConfigs($sourceResourceId: String) {
      derivedDatasetConfigs(sourceResourceId: $sourceResourceId) {
        id
        sourceResourceId
        targetName
        keyField
        extractFields
        mergeStrategy
        enabled
        description
        createdAt
        entryCount
      }
    }
  `,

  GET_FETCHERS: `
    query GetFetchers {
      fetchers {
        id
        name
        code
        classPath
        description
        paramsDef {
          id
          paramName
          dataType
          required
          defaultValue
          enumValues
          description
        }
        resources {
          id
          name
          publisher
          active
        }
      }
    }
  `,

  GET_SUBSCRIPTIONS: `
    query GetSubscriptions {
      datasetSubscriptions {
        id
        applicationId
        resourceId
        pinnedVersion
        autoUpgrade
        currentVersion
        notifiedAt
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
        description
        publisher
        publisherId
        targetTable
      }
    }
  `,

  UPDATE_RESOURCE: `
    mutation UpdateResource($id: String!, $input: UpdateResourceInput!) {
      updateResource(id: $id, input: $input) {
        id
        name
        description
        publisher
        publisherId
        targetTable
      }
    }
  `,

  DELETE_RESOURCE: `
    mutation DeleteResource($id: String!, $hardDelete: Boolean) {
      deleteResource(id: $id, hardDelete: $hardDelete)
    }
  `,

  CLONE_RESOURCE: `
    mutation CloneResource($id: String!, $name: String) {
      cloneResource(id: $id, name: $name) {
        id
        name
        publisher
        fetcherId
        active
        schedule
        params { key value isExternal }
      }
    }
  `,

  EXECUTE_RESOURCE: `
    mutation ExecuteResource($id: String!, $params: JSON) {
      executeResource(id: $id, params: $params) {
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
        consumptionMode
      }
    }
  `,

  UPDATE_APPLICATION: `
    mutation UpdateApplication($id: String!, $input: UpdateApplicationInput!) {
      updateApplication(id: $id, input: $input) {
        id
        name
        consumptionMode
      }
    }
  `,

  DELETE_APPLICATION: `
    mutation DeleteApplication($id: String!, $hardDelete: Boolean) {
      deleteApplication(id: $id, hardDelete: $hardDelete)
    }
  `,


  DELETE_EXECUTION: `
    mutation DeleteExecution($id: String!, $hardDelete: Boolean) {
      deleteExecution(id: $id, hardDelete: $hardDelete)
    }
  `,

  SET_CONFIG: `
    mutation SetConfig($input: SetConfigInput!) {
      setConfig(input: $input) {
        key
        value
        updatedAt
      }
    }
  `,

  ABORT_EXECUTION: `
    mutation AbortExecution($id: String!) {
      abortExecution(id: $id) {
        success
        message
      }
    }
  `,

  PAUSE_EXECUTION: `
    mutation PauseExecution($id: String!) {
      pauseExecution(id: $id) {
        success
        message
      }
    }
  `,

  RESUME_EXECUTION: `
    mutation ResumeExecution($id: String!) {
      resumeExecution(id: $id) {
        success
        message
      }
    }
  `,

  CREATE_FETCHER: `
    mutation CreateFetcher($input: CreateFetcherInput!) {
      createFetcher(input: $input) {
        id
        code
        name
        description
      }
    }
  `,

  UPDATE_FETCHER: `
    mutation UpdateFetcher($id: String!, $input: UpdateFetcherInput!) {
      updateFetcher(id: $id, input: $input) {
        id
        code
        name
        description
      }
    }
  `,

  DELETE_FETCHER: `
    mutation DeleteFetcher($id: String!, $hardDelete: Boolean) {
      deleteFetcher(id: $id, hardDelete: $hardDelete)
    }
  `,

  CREATE_DERIVED_DATASET_CONFIG: `
    mutation CreateDerivedDatasetConfig($input: CreateDerivedDatasetConfigInput!) {
      createDerivedDatasetConfig(input: $input) {
        id
        sourceResourceId
        targetName
        keyField
        extractFields
        mergeStrategy
        enabled
        description
        entryCount
      }
    }
  `,

  UPDATE_DERIVED_DATASET_CONFIG: `
    mutation UpdateDerivedDatasetConfig($id: String!, $input: UpdateDerivedDatasetConfigInput!) {
      updateDerivedDatasetConfig(id: $id, input: $input) {
        id
        sourceResourceId
        targetName
        keyField
        extractFields
        mergeStrategy
        enabled
        description
        entryCount
      }
    }
  `,

  DELETE_DERIVED_DATASET_CONFIG: `
    mutation DeleteDerivedDatasetConfig($id: String!) {
      deleteDerivedDatasetConfig(id: $id)
    }
  `,

  TOGGLE_DERIVED_DATASET_CONFIG: `
    mutation ToggleDerivedDatasetConfig($id: String!, $enabled: Boolean!) {
      toggleDerivedDatasetConfig(id: $id, enabled: $enabled) {
        id
        enabled
        entryCount
      }
    }
  `,

  CREATE_TYPE_FETCHER_PARAM: `
    mutation CreateTypeFetcherParam($input: CreateTypeFetcherParamInput!) {
      createTypeFetcherParam(input: $input) {
        id
        paramName
        dataType
        required
        defaultValue
        enumValues
      }
    }
  `,

  UPDATE_TYPE_FETCHER_PARAM: `
    mutation UpdateTypeFetcherParam($id: String!, $input: UpdateTypeFetcherParamInput!) {
      updateTypeFetcherParam(id: $id, input: $input) {
        id
        paramName
        dataType
        required
        defaultValue
        enumValues
      }
    }
  `,

  DELETE_TYPE_FETCHER_PARAM: `
    mutation DeleteTypeFetcherParam($id: String!) {
      deleteTypeFetcherParam(id: $id)
    }
  `,

  SUBSCRIBE_RESOURCE: `
    mutation SubscribeResource($applicationId: String!, $resourceId: String!, $pinnedVersion: String, $autoUpgrade: String) {
      subscribeResource(applicationId: $applicationId, resourceId: $resourceId, pinnedVersion: $pinnedVersion, autoUpgrade: $autoUpgrade) {
        id
        applicationId
        resourceId
        pinnedVersion
        autoUpgrade
        currentVersion
        notifiedAt
      }
    }
  `,

  UNSUBSCRIBE_RESOURCE: `
    mutation UnsubscribeResource($id: String!) {
      unsubscribeResource(id: $id)
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

export async function fetchFetchers() {
  try {
    return await client.request(QUERIES.GET_FETCHERS)
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function createFetcher(input) {
  try {
    return await client.request(MUTATIONS.CREATE_FETCHER, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updateFetcher(id, input) {
  try {
    return await client.request(MUTATIONS.UPDATE_FETCHER, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteFetcher(id, hardDelete = false) {
  try {
    return await client.request(MUTATIONS.DELETE_FETCHER, { id, hardDelete })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function createTypeFetcherParam(input) {
  try {
    return await client.request(MUTATIONS.CREATE_TYPE_FETCHER_PARAM, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updateTypeFetcherParam(id, input) {
  try {
    return await client.request(MUTATIONS.UPDATE_TYPE_FETCHER_PARAM, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteTypeFetcherParam(id) {
  try {
    return await client.request(MUTATIONS.DELETE_TYPE_FETCHER_PARAM, { id })
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

export async function deleteResource(id, hardDelete = false) {
  try {
    return await client.request(MUTATIONS.DELETE_RESOURCE, { id, hardDelete })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function cloneResource(id, name = null) {
  try {
    return await client.request(MUTATIONS.CLONE_RESOURCE, { id, name })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function executeResource(id, params = null) {
  try {
    return await client.request(MUTATIONS.EXECUTE_RESOURCE, { id, params })
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

export async function deleteApplication(id, hardDelete = false) {
  try {
    return await client.request(MUTATIONS.DELETE_APPLICATION, { id, hardDelete })
  } catch (error) {
    handleGraphQLError(error)
  }
}


export async function previewResourceData(id, limit = 10, params = null) {
  try {
    return await client.request(QUERIES.PREVIEW_RESOURCE_DATA, { id, limit, params })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchDatasets(resourceId = null) {
  try {
    return await client.request(QUERIES.GET_ARTIFACTS, { resourceId })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteExecution(id, hardDelete = false) {
  try {
    return await client.request(MUTATIONS.DELETE_EXECUTION, { id, hardDelete })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchAppConfig() {
  try {
    return await client.request(QUERIES.GET_APP_CONFIG)
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function setConfig(key, value) {
  try {
    return await client.request(MUTATIONS.SET_CONFIG, { input: { key, value } })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function abortExecution(id) {
  try {
    return await client.request(MUTATIONS.ABORT_EXECUTION, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function pauseExecution(id) {
  try {
    return await client.request(MUTATIONS.PAUSE_EXECUTION, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function resumeExecution(id) {
  try {
    return await client.request(MUTATIONS.RESUME_EXECUTION, { id })
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

export async function fetchDerivedDatasetConfigs(sourceResourceId = null) {
  try {
    return await client.request(QUERIES.GET_DERIVED_DATASET_CONFIGS, { sourceResourceId })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function createDerivedDatasetConfig(input) {
  try {
    return await client.request(MUTATIONS.CREATE_DERIVED_DATASET_CONFIG, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updateDerivedDatasetConfig(id, input) {
  try {
    return await client.request(MUTATIONS.UPDATE_DERIVED_DATASET_CONFIG, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deleteDerivedDatasetConfig(id) {
  try {
    return await client.request(MUTATIONS.DELETE_DERIVED_DATASET_CONFIG, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function toggleDerivedDatasetConfig(id, enabled) {
  try {
    return await client.request(MUTATIONS.TOGGLE_DERIVED_DATASET_CONFIG, { id, enabled })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function fetchSubscriptions() {
  try {
    return await client.request(QUERIES.GET_SUBSCRIPTIONS)
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function subscribeResource(applicationId, resourceId, pinnedVersion = null, autoUpgrade = 'patch') {
  try {
    return await client.request(MUTATIONS.SUBSCRIBE_RESOURCE, { applicationId, resourceId, pinnedVersion, autoUpgrade })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function unsubscribeResource(id) {
  try {
    return await client.request(MUTATIONS.UNSUBSCRIBE_RESOURCE, { id })
  } catch (error) {
    handleGraphQLError(error)
  }
}

// ── Publishers ────────────────────────────────────────────────────────────────

const PUBLISHER_FIELDS = `
  id nombre acronimo nivel pais comunidadAutonoma provincia municipio portalUrl email telefono createdAt
`

export async function fetchPublishers() {
  try {
    return await client.request(`query { publishers { ${PUBLISHER_FIELDS} } }`)
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function createPublisher(input) {
  try {
    return await client.request(`
      mutation CreatePublisher($input: CreatePublisherInput!) {
        createPublisher(input: $input) { ${PUBLISHER_FIELDS} }
      }
    `, { input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function updatePublisher(id, input) {
  try {
    return await client.request(`
      mutation UpdatePublisher($id: String!, $input: UpdatePublisherInput!) {
        updatePublisher(id: $id, input: $input) { ${PUBLISHER_FIELDS} }
      }
    `, { id, input })
  } catch (error) {
    handleGraphQLError(error)
  }
}

export async function deletePublisher(id, hardDelete = false) {
  try {
    return await client.request(`
      mutation DeletePublisher($id: String!, $hardDelete: Boolean) { deletePublisher(id: $id, hardDelete: $hardDelete) }
    `, { id, hardDelete })
  } catch (error) {
    handleGraphQLError(error)
  }
}

// ── Trash: fetch deleted ────────────────────────────────────────────────────

export async function fetchDeletedResources() {
  try {
    return await client.request(`query { deletedResources { id name deletedAt } }`)
  } catch (e) { handleGraphQLError(e) }
}

export async function fetchDeletedApplications() {
  try {
    return await client.request(`query { deletedApplications { id name description deletedAt } }`)
  } catch (e) { handleGraphQLError(e) }
}

export async function fetchDeletedPublishers() {
  try {
    return await client.request(`query { deletedPublishers { id nombre acronimo deletedAt } }`)
  } catch (e) { handleGraphQLError(e) }
}

export async function fetchDeletedFetchers() {
  try {
    return await client.request(`query { deletedFetchers { id code description deletedAt } }`)
  } catch (e) { handleGraphQLError(e) }
}

export async function fetchDeletedExecutions() {
  try {
    return await client.request(`query { deletedExecutions { id resourceId resourceName status startedAt deletedAt } }`)
  } catch (e) { handleGraphQLError(e) }
}

// ── Trash: restore ──────────────────────────────────────────────────────────

export async function restoreResource(id) {
  try { return await client.request(`mutation { restoreResource(id: "${id}") }`) }
  catch (e) { handleGraphQLError(e) }
}

export async function restoreApplication(id) {
  try { return await client.request(`mutation { restoreApplication(id: "${id}") }`) }
  catch (e) { handleGraphQLError(e) }
}

export async function restorePublisher(id) {
  try { return await client.request(`mutation { restorePublisher(id: "${id}") }`) }
  catch (e) { handleGraphQLError(e) }
}

export async function restoreFetcher(id) {
  try { return await client.request(`mutation { restoreFetcher(id: "${id}") }`) }
  catch (e) { handleGraphQLError(e) }
}

export async function restoreExecution(id) {
  try { return await client.request(`mutation { restoreExecution(id: "${id}") }`) }
  catch (e) { handleGraphQLError(e) }
}
