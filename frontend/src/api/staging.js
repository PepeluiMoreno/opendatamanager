import axios from 'axios'

const API_URL = 'http://localhost:8040/api/staging'

export async function listFiles() {
  try {
    const response = await axios.get(`${API_URL}/files`)
    return response.data
  } catch (error) {
    throw new Error(`Failed to list files: ${error.response?.data?.message || error.message}`)
  }
}

export async function previewFile(filePath, limit = 100) {
  try {
    const response = await axios.get(`${API_URL}/preview`, {
      params: { path: filePath, limit }
    })
    return response.data
  } catch (error) {
    throw new Error(`Failed to preview file: ${error.response?.data?.message || error.message}`)
  }
}

export async function downloadFile(filePath) {
  try {
    const response = await axios.get(`${API_URL}/download`, {
      params: { path: filePath },
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filePath.split('/').pop())
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    throw new Error(`Failed to download file: ${error.response?.data?.message || error.message}`)
  }
}

export async function downloadAllAsZip() {
  try {
    const response = await axios.get(`${API_URL}/download-all`, {
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'jsonl_files.zip')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    throw new Error(`Failed to download ZIP: ${error.response?.data?.message || error.message}`)
  }
}