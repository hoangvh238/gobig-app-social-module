"""
Media upload router - proxies to upload service
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
import httpx
from app.config import settings
from app.schemas.media import MediaUploadResponse

router = APIRouter()


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_media(file: UploadFile = File(...)):
    """
    Upload media file to storage service

    Returns:
        - success: Upload status
        - url: Public URL to access the file
        - key: Storage key (for reference)
        - size: File size in bytes
        - mimetype: File MIME type
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read file content
    file_content = await file.read()

    # Prepare multipart form data
    files = {
        'file': (file.filename, file_content, file.content_type)
    }

    # Forward to upload service
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{settings.upload_service_url}/api/upload",
                files=files
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Upload service error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to upload service: {str(e)}"
            )
