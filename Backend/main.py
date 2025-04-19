from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pytubefix import YouTube
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import os
import traceback

app = FastAPI()

# CORS middleware (for frontend testing or cross-origin access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create downloads directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def list_video_resolutions(url: str):
    yt = YouTube(url)
    streams = yt.streams.filter(progressive=True, file_extension='mp4')
    resolutions = sorted({s.resolution for s in streams if s.resolution})
    return resolutions

def download_video(url: str, quality: Optional[str] = None) -> Path:
    yt = YouTube(url)
    if quality:
        stream = yt.streams.filter(progressive=True, file_extension='mp4', resolution=quality).first()
    else:
        stream = yt.streams.get_highest_resolution()

    if not stream:
        raise ValueError("Requested quality not available.")

    file_path = stream.download(output_path=str(DOWNLOAD_DIR))
    return Path(file_path)

def make_attachment_header(filename: str) -> str:
    quoted_filename = quote(filename)
    return f'attachment; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}'

@app.get("/")
def root():
    return {"message": "YouTube Video Downloader API is running."}

@app.get("/video/resolutions")
def get_video_resolutions(url: str):
    try:
        if "?" in url:
            url = url.split("?")[0]
        return {"resolutions": list_video_resolutions(url)}
    except Exception as e:
        print("Error in /video/resolutions:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/video_file")
def download_video_file(url: str, quality: str = "highest"):
    try:
        if "?" in url:
            url = url.split("?")[0]
        actual_quality = None if quality == "highest" else quality
        file_path = download_video(url, actual_quality)
        disposition = make_attachment_header(file_path.name)
        return FileResponse(
            path=str(file_path),
            media_type="application/octet-stream",
            filename=file_path.name,
            headers={"Content-Disposition": disposition}
        )
    except Exception as e:
        print("Error in /download/video_file:\n", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
