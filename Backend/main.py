from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pytubefix import YouTube
from typing import Optional
from pydantic import BaseModel
import io
import base64

app = FastAPI()

# CORS setup
origins = [
    "*"
    # "http://localhost:5173",  # React local dev
    # "https://yourfrontenddomain.com",  # Production (if any)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class VideoRequest(BaseModel):
    url: str
    quality: Optional[str] = None

class AudioRequest(BaseModel):
    url: str
    quality: Optional[str] = "high"

@app.get("/")
def read_root():
    return {"message": "Welcome to the YouTube download API!"}

@app.post("/download_video/")
async def download_video(data: VideoRequest):
    try:
        yt = YouTube(data.url)

        # Use specified quality if provided, else get highest resolution
        if data.quality:
            stream = yt.streams.filter(res=data.quality, progressive=True, file_extension='mp4').first()
        else:
            stream = yt.streams.get_highest_resolution()

        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")

        buffer = io.BytesIO()
        stream.stream_to_buffer(buffer)
        buffer.seek(0)

        return {
            "file": base64.b64encode(buffer.read()).decode(),
            "filename": f"{yt.title}_{data.quality or stream.resolution}.mp4",
            "mime_type": "video/mp4"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.post("/download_audio/")
def download_audio(request: AudioRequest):
    try:
        yt = YouTube(request.url)
        audio_streams = yt.streams.filter(only_audio=True)

        if request.quality == "high":
            stream = audio_streams.order_by('abr').desc().first()
        elif request.quality == "low":
            stream = audio_streams.order_by('abr').asc().first()
        else:
            raise HTTPException(status_code=400, detail="Invalid quality: choose 'high' or 'low'.")

        buffer = io.BytesIO()
        stream.stream_to_buffer(buffer)
        buffer.seek(0)

        return {
            "file": base64.b64encode(buffer.read()).decode(),
            "filename": f"{yt.title}_{request.quality}.mp3",
            "mime_type": "audio/mp3"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.get("/list_video_resolutions/")
def list_video_resolutions(url: str):
    try:
        yt = YouTube(url)
        video_streams = yt.streams.filter(progressive=True, file_extension='mp4')
        resolutions = sorted({stream.resolution for stream in video_streams if stream.resolution})
        return {"resolutions": resolutions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

@app.get("/list_audio_streams/")
def list_audio_streams(url: str):
    try:
        yt = YouTube(url)
        audio_streams = yt.streams.filter(only_audio=True)
        qualities = sorted({stream.abr for stream in audio_streams if stream.abr})
        return {"audio_qualities": qualities}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
