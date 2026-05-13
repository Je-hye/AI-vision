# AI Vision Gesture Events

Python web dashboard for detecting hand gesture events from a live video stream. The app samples frames from an RTSP/HLS/HTTP stream, sends them to Roboflow Hosted API, converts detections into gesture events, and shows recent frames, detections, and event logs in the browser.

## Features

- FastAPI dashboard and REST API
- RTSP, HLS, and HTTP video stream input through OpenCV
- Roboflow Hosted API object detection integration
- Configurable confidence threshold, sample FPS, consecutive-frame trigger, cooldown, and target classes
- JSONL event log with snapshot paths

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env`:

```dotenv
ROBOFLOW_API_KEY=your_api_key
ROBOFLOW_MODEL_ID=your-project/1
```

The default model ID is a starter value. Use the exact model ID from the Roboflow model page you want to run.

## Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 and enter a stream URL.

## API

- `GET /health`
- `POST /streams/start`
- `POST /streams/stop`
- `GET /streams/status`
- `GET /events`

Example start request:

```json
{
  "stream_url": "https://example.com/live.m3u8",
  "confidence_threshold": 0.5,
  "frame_sample_fps": 1,
  "consecutive_frames": 2,
  "cooldown_seconds": 5,
  "target_classes": ["wave", "thumbs_up"]
}
```

## Test

```bash
pytest
```

## GitHub

This repo is intended to be pushed as a public GitHub repository:

```bash
git init
git add .
git commit -m "Initial gesture event dashboard"
gh repo create AI-vision --public --source=. --remote=origin --push
```
