from pydantic import BaseModel


class MediaUploadResponse(BaseModel):
    """Response from upload service"""
    success: bool
    url: str
    key: str
    size: int
    mimetype: str
