from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import requests
import os
import uuid
import re
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# Import correctly from niimprint
from niimprint import PrinterClient, BluetoothTransport

app = FastAPI(title="Niimbot B18 Printing Service")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PrintRequest(BaseModel):
    image_url: HttpUrl
    rotation: int = 90  # Default to 90 degrees
    density: int = 3    # Default to density 3 for B18

@app.post("/print")
async def print_image(request: PrintRequest):
    # Create a temporary directory if it doesn't exist
    temp_dir = "temp_images"
    os.makedirs(temp_dir, exist_ok=True)

    # Generate unique filename
    temp_filename = f"{temp_dir}/{uuid.uuid4()}.png"

    try:
        # Download the image
        response = requests.get(request.image_url, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Could not download image from URL")

        # Save the image
        with open(temp_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Open the image
        img = Image.open(temp_filename)

        # Apply rotation if needed
        if request.rotation:
            img = img.rotate(-request.rotation, expand=True)  # PIL rotates counter-clockwise

        # Check image width
        if img.width > 384:  # B18 max width is 384 pixels
            raise HTTPException(status_code=400, detail="Image width too big for B18 printer")

        # Create transport
        bluetooth_addr = "09:07:03:87:F3:D2"
        transport = BluetoothTransport(bluetooth_addr)

        # Create printer client correctly
        printer = PrinterClient(transport)

        # Print the image with specified density
        printer.print_image(img, density=request.density)

        return {"success": True, "message": "Image printed successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.get("/")
async def root():
    return {"message": "Niimbot B18 Printing Service. Send POST to /print with image_url."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8118)
