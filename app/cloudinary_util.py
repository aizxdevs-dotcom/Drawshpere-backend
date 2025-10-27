import cloudinary
import cloudinary.uploader
import os
from fastapi import UploadFile, HTTPException

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

async def upload_image(file: UploadFile, folder: str = "drawsphere") -> dict:
    """
    Upload an image to Cloudinary and return the URL and public_id
    """
    try:
        # Read file content
        contents = await file.read()
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            resource_type="auto",
            transformation=[
                {"width": 1200, "height": 1200, "crop": "limit"},
                {"quality": "auto:good"}
            ]
        )
        
        return {
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "width": result.get("width"),
            "height": result.get("height")
        }
    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

def delete_image(public_id: str) -> bool:
    """
    Delete an image from Cloudinary by public_id
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
    except Exception as e:
        print(f"❌ Cloudinary delete error: {e}")
        return False
