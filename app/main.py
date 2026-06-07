from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.event_store import EventStore
from app.models import GestureEvent, HealthResponse, StreamStartRequest, StreamStatus
from app.roboflow_client import RoboflowClient
from app.stream_processor import StreamProcessor

app = FastAPI(
    title="AI Vision Gesture Event Dashboard",
    description="Detect hand gesture events from live streams using Roboflow Hosted API.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

settings = get_settings()
event_store = EventStore(settings.event_log_path)
roboflow_client = RoboflowClient(
    api_url=settings.roboflow_api_url,
    api_key=settings.roboflow_api_key,
    model_id=settings.roboflow_model_id,
)
processor = StreamProcessor(roboflow_client, event_store, settings.snapshot_dir)

SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health", response_model=HealthResponse)
async def health(current_settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        ok=True,
        roboflow_configured=bool(current_settings.roboflow_api_key),
        model_id=current_settings.roboflow_model_id,
    )


@app.post("/streams/start", response_model=StreamStatus, status_code=status.HTTP_202_ACCEPTED)
async def start_stream(payload: StreamStartRequest, current_settings: SettingsDep) -> StreamStatus:
    defaults: dict[str, float | int] = {
        "confidence_threshold": current_settings.confidence_threshold,
        "frame_sample_fps": current_settings.frame_sample_fps,
        "consecutive_frames": current_settings.consecutive_frames,
        "cooldown_seconds": current_settings.event_cooldown_seconds,
    }
    return processor.start(payload, defaults)


@app.post("/streams/stop", response_model=StreamStatus)
async def stop_stream() -> StreamStatus:
    return processor.stop()


@app.get("/streams/status", response_model=StreamStatus)
async def stream_status() -> StreamStatus:
    return processor.status()


@app.get("/events", response_model=list[GestureEvent])
async def events() -> list[GestureEvent]:
    return event_store.list()


@app.get("/frame/latest", include_in_schema=False)
async def latest_frame() -> Response:
    frame = processor.latest_frame()
    if frame is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No frame available")
    return Response(
        content=frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, max-age=0"},
    )
