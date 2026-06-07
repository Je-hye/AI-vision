# RTSP Optical Flow PoC

간단한 RTSP 소비자와 Farneback optical flow 기반의 움직임(제스처 예비) 이벤트 예제입니다.

Usage:

1. 가상환경 생성 및 의존성 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 실행

```bash
python rtsp_optical_flow.py --source "rtsp://user:pw@camera:554/stream" --process-fps 5
```

옵션 및 설명은 `rtsp_optical_flow.py` 내부 참고.
