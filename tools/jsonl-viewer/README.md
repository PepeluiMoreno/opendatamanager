# JSONL Viewer for OpenDataManager

Simple and efficient JSONL file viewer for exploring staged data files

## Features

- 📁 View JSONL files line-by-line
- 🔍 Search within files
- 🎯 Syntax highlighting
- 📄 Copy formatted JSON
- 📊 Download individual files
- 🔍 Download entire directory as ZIP

## Installation

Clone this repository and run the web viewer:

```bash
git clone <this_repo_url>
cd opendatamanager/frontend
npm install
npm run dev
```

## Access your JSONL files

Point this viewer to your staging directory:

```
C:\Users\Jose\dev\opendatamanager\data\staging\
```

## Usage Examples

### View staged datasets:
```
# Direct file access
https://localhost:8040/api/datasets/{dataset_id}/data.jsonl

# Download all datasets as ZIP
https://localhost:8040/api/datasets/download?resource_id={resource_id}
```

## Available Endpoints

```graphql
query Getdatasets($resourceId: String) {
  datasets(resourceId: $resourceId) {
    id
    version
    recordCount
    created_at
    downloadUrls {
      data: "/api/datasets/{dataset_id}/data.jsonl"
      schema: "/api/datasets/{dataset_id}/schema.json" 
      models: "/api/datasets/{dataset_id}/models.py"
      metadata: "/api/datasets/{dataset_id}/metadata.json"
    }
  }
}
```

# REST API for JSONL files
```bash
# List all JSONL files in staging
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8040/api/staging/files

# View specific file
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8040/api/staging/files/data/rer_2025.jsonl

# Preview file content
curl -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8040/api/staging/files/rer_2025.jsonl?lines=10
```

## Why JSONL is perfect for your use case:

✅ **Large datasets** - No memory issues with 14,836 records  
✅ **Streaming parsing** - Process files as they download  
✅ **Line-by-line access** - Navigate large files efficiently  
✅ **Web interface** - No need for specialized viewers  
✅ **API integration** - Already connected to your existing API  
✅ **Backend validation** - Schema validation for data integrity  
✅ **Download control** - Granular download de archivos
✅ **Debugging** - Inspect files sin sobrecargar el sistema

The JSONL files are already available at:
`C:\Users\Jose\dev\opendatamanager\data\staging\`

You can access them through:
1. Direct file system
2. REST API endpoints
3. Future web interface

🚀 **The JSONL is already working perfectly for your use case.**