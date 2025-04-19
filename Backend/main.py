from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pytubefix import YouTube
from pathlib import Path
from typing import Optional

app = FastAPI()

# Serve the React‐style single‐page HTML (or drop this in your static files)
INDEX_FILE = Path(__file__).parent / "index.html"

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if not INDEX_FILE.exists():
        raise HTTPException(404, "index.html not found")
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))

@app.get("/video/resolutions")
async def video_resolutions(url: str):
    """
    Return all progressive MP4 resolutions for a given YouTube URL.
    """
    try:
        yt = YouTube(url, use_po_token=True)
        streams = yt.streams.filter(progressive=True, file_extension="mp4")
        resolutions = sorted({s.resolution for s in streams if s.resolution})
        return JSONResponse({"resolutions": resolutions})
    except Exception as e:
        raise HTTPException(400, f"Could not fetch resolutions: {e}")

@app.get("/audio/qualities")
async def audio_qualities(url: str):
    """
    Return all audio bitrates for a given YouTube URL.
    """
    try:
        yt = YouTube(url, use_po_token=True)
        streams = yt.streams.filter(only_audio=True)
        bitrates = sorted({s.abr for s in streams if s.abr})
        return JSONResponse({"audio_qualities": bitrates})
    except Exception as e:
        raise HTTPException(400, f"Could not fetch audio qualities: {e}")

@app.get("/download_url")
async def download_url(
    url: str,
    download_type: str,
    resolution: Optional[str] = "highest",
    audio_quality: Optional[str] = "high"
):
    """
    Return a direct‐streaming URL to the requested media.
    Clients should <a download> this URL.
    """
    try:
        yt = YouTube(url, use_po_token=True)
        if download_type == "video":
            streams = yt.streams.filter(progressive=True, file_extension="mp4")
            if resolution and resolution != "highest":
                stream = streams.filter(res=resolution).first()
            else:
                stream = streams.get_highest_resolution()
        elif download_type == "audio":
            streams = yt.streams.filter(only_audio=True)
            if audio_quality == "low":
                stream = streams.order_by("abr").asc().first()
            else:
                stream = streams.order_by("abr").desc().first()
        else:
            raise HTTPException(400, "download_type must be 'video' or 'audio'")

        if not stream:
            raise HTTPException(404, "Requested stream not found")

        return {"download_url": stream.url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generating download URL: {e}")
