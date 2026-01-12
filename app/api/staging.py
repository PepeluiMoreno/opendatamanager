import os
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, APIRouter, Query
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask
import io

router = APIRouter(prefix="/api/staging", tags=["staging"])

# Get staging directory from environment or use default
STAGING_DIR = Path(os.getenv('STAGING_DIR', './data/staging'))

def ensure_staging_dir():
    """Ensure staging directory exists"""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/files")
async def list_files():
    """List all JSONL files in the staging directory"""
    ensure_staging_dir()
    
    try:
        files = []
        for file_path in STAGING_DIR.rglob("*.jsonl"):
            if file_path.is_file():
                stat = file_path.stat()
                relative_path = file_path.relative_to(STAGING_DIR)
                
                files.append({
                    "name": file_path.name,
                    "path": str(relative_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "created": stat.st_ctime
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.get("/preview")
async def preview_file(
    path: str = Query(..., description="Relative path to the JSONL file"),
    limit: int = Query(100, description="Number of lines to preview")
):
    """Preview the first N lines of a JSONL file"""
    ensure_staging_dir()
    
    try:
        file_path = STAGING_DIR / path
        
        # Security check: ensure file is within staging directory
        if not file_path.resolve().is_relative_to(STAGING_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied: file outside staging directory")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        lines = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= limit:
                    break
                line = line.strip()
                if line:
                    try:
                        # Validate JSON and format it
                        json_obj = json.loads(line)
                        lines.append(json.dumps(json_obj, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError:
                        lines.append(f"[INVALID JSON] {line}")
        
        return lines
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {str(e)}")

@router.get("/download")
async def download_file(
    path: str = Query(..., description="Relative path to the JSONL file")
):
    """Download a specific JSONL file"""
    ensure_staging_dir()
    
    try:
        file_path = STAGING_DIR / path
        
        # Security check: ensure file is within staging directory
        if not file_path.resolve().is_relative_to(STAGING_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied: file outside staging directory")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type='application/x-lines+json'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.get("/download-all")
async def download_all_as_zip():
    """Download all JSONL files as a ZIP archive"""
    ensure_staging_dir()
    
    try:
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            jsonl_files = list(STAGING_DIR.rglob("*.jsonl"))
            
            if not jsonl_files:
                raise HTTPException(status_code=404, detail="No JSONL files found")
            
            for file_path in jsonl_files:
                if file_path.is_file():
                    # Use relative path in ZIP to preserve directory structure
                    relative_path = file_path.relative_to(STAGING_DIR)
                    zip_file.write(file_path, str(relative_path))
        
        zip_buffer.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jsonl_files_{timestamp}.zip"
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ZIP: {str(e)}")

@router.delete("/files")
async def delete_file(
    path: str = Query(..., description="Relative path to the JSONL file to delete")
):
    """Delete a specific JSONL file"""
    ensure_staging_dir()
    
    try:
        file_path = STAGING_DIR / path
        
        # Security check: ensure file is within staging directory
        if not file_path.resolve().is_relative_to(STAGING_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied: file outside staging directory")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        file_path.unlink()
        return {"message": f"File {path} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@router.get("/stats")
async def get_staging_stats():
    """Get statistics about the staging directory"""
    ensure_staging_dir()
    
    try:
        jsonl_files = list(STAGING_DIR.rglob("*.jsonl"))
        
        total_files = len(jsonl_files)
        total_size = sum(f.stat().st_size for f in jsonl_files if f.is_file())
        
        # Count files by extension in subdirectories
        directory_stats = {}
        for file_path in jsonl_files:
            if file_path.is_file():
                parent_dir = str(file_path.parent.relative_to(STAGING_DIR))
                if parent_dir not in directory_stats:
                    directory_stats[parent_dir] = {"count": 0, "size": 0}
                directory_stats[parent_dir]["count"] += 1
                directory_stats[parent_dir]["size"] += file_path.stat().st_size
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "directory_stats": directory_stats,
            "staging_dir": str(STAGING_DIR)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")