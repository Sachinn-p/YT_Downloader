from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from pytubefix import YouTube
from pathlib import Path
from urllib.parse import quote

app = FastAPI()

BASE_DIR = Path(__file__).parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

INDEX_FILE = "index.html"


class DownloadRequest(BaseModel):
    url: str
    quality: str | None = None       # for video
    audio_quality: str = "high"       # for audio


def make_attachment_header(filename: str) -> str:
    """
    Build a Content-Disposition header that safely
    encodes non-Latin-1 characters via RFC5987.
    """
    try:
        filename.encode("latin-1")
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        quoted = quote(filename, safe="")
        return f"attachment; filename*=UTF-8''{quoted}"


def download_video(link: str, quality: str | None) -> Path:
    yt = YouTube(link)
    stream = yt.streams.get_by_resolution(quality) if quality else yt.streams.get_highest_resolution()
    if not stream:
        raise HTTPException(status_code=404, detail="Resolution not found")
    out = DOWNLOAD_DIR / stream.default_filename
    stream.download(output_path=str(DOWNLOAD_DIR))
    return out


def download_audio(link: str, quality: str) -> Path:
    yt = YouTube(link)
    streams = yt.streams.filter(only_audio=True)
    if quality == "high":
        stream = streams.order_by("abr").desc().first()
    elif quality == "low":
        stream = streams.order_by("abr").asc().first()
    else:
        raise HTTPException(status_code=400, detail="Invalid quality choice")
    if not stream:
        raise HTTPException(status_code=404, detail="Audio stream not found")
    out = DOWNLOAD_DIR / stream.default_filename
    stream.download(output_path=str(DOWNLOAD_DIR))
    return out


def list_video_resolutions(link: str) -> list[str]:
    yt = YouTube(link)
    vids = yt.streams.filter(progressive=True, file_extension="mp4")
    return sorted({s.resolution for s in vids})


def list_audio_streams(link: str) -> list[str]:
    yt = YouTube(link)
    auds = yt.streams.filter(only_audio=True)
    return sorted({s.abr for s in auds})



@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def serve_index():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=INDEX_FILE.read_text(encoding="utf-8"))


@app.get("/video/resolutions")
async def get_video_resolutions(url: str):
    try:
        return {"resolutions": list_video_resolutions(url)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audio/qualities")
async def get_audio_qualities(url: str):
    try:
        return {"audio_qualities": list_audio_streams(url)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/video_file")
async def download_video_file(url: str, quality: str = "highest"):
    """
    quality="highest" → passes None into download_video()
    triggering get_highest_resolution().
    """
    try:
        actual_quality = None if quality == "highest" else quality
        path = download_video(url, actual_quality)
        disposition = make_attachment_header(path.name)
        return FileResponse(
            path=str(path),
            media_type="application/octet-stream",
            headers={"Content-Disposition": disposition}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/audio_file")
async def download_audio_file(url: str, audio_quality: str = "high"):
    try:
        path = download_audio(url, audio_quality)
        disposition = make_attachment_header(path.name)
        return FileResponse(
            path=str(path),
            media_type="application/octet-stream",
            headers={"Content-Disposition": disposition}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
