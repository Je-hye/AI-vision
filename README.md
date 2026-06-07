# AI 비전 제스처 이벤트 (AI Vision Gesture Events)

실시간 비디오 스트림에서 손동작 이벤트를 감지하는 Python 웹 대시보드입니다. 이 애플리케이션은 RTSP/HLS/HTTP 스트림에서 프레임을 샘플링하여 Roboflow Hosted API로 전송하고, 탐지된 결과를 제스처 이벤트로 변환하여 최근 프레임, 탐지 결과 및 이벤트 로그를 브라우저에 표시합니다.

## 주요 기능

- FastAPI 대시보드 및 REST API
- OpenCV를 통한 RTSP, HLS, HTTP 비디오 스트림 입력 지원
- Roboflow Hosted API 객체 탐지 통합
- 신뢰도 임계값, 샘플 FPS, 연속 프레임 트리거, 쿨다운, 대상 클래스 등 설정 가능
- 스냅샷 경로를 포함한 JSONL 이벤트 로그

## 설정 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

`.env` 파일 수정:

```dotenv
ROBOFLOW_API_KEY=your_api_key
ROBOFLOW_MODEL_ID=your-project/1
```

기본 모델 ID는 예시입니다. 사용하려는 Roboflow 모델 페이지의 정확한 모델 ID를 사용하세요.

## 실행 방법

```bash
uvicorn app.main:app --reload
```

http://127.0.0.1:8000 접속 후 스트림 URL을 입력하세요.

## API 엔드포인트

- `GET /health`: 상태 확인
- `POST /streams/start`: 스트림 시작
- `POST /streams/stop`: 스트림 중지
- `GET /streams/status`: 스트림 상태 조회
- `GET /events`: 이벤트 목록 조회

스트림 시작 요청 예시:

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

## 대시보드 사용 방법

1.  **접속**: 서버 실행 후 브라우저에서 `http://127.0.0.1:8000`에 접속합니다.
2.  **스트림 설정**:
    *   **Stream URL**: 분석할 비디오 스트림 주소(RTSP, HLS, HTTP 또는 웹캠 번호 `0`)를 입력합니다.
    *   **Confidence Threshold**: 감지 신뢰도 (예: 0.5).
    *   **Target Classes**: 감지할 제스처 이름을 쉼표로 구분하여 입력합니다 (예: `thumbs_up, palm`).
3.  **시작/중지**: 'Start Stream' 버튼을 눌러 분석을 시작하고, 'Stop Stream'으로 중지합니다.
4.  **모니터링**:
    *   **Live View**: 현재 분석 중인 프레임이 실시간으로 표시됩니다.
    *   **Detection Results**: 최근에 탐지된 객체 정보가 리스트로 나타납니다.
    *   **Event Log**: 설정된 규칙(연속 프레임 등)에 따라 발생한 최종 이벤트 로그를 확인합니다.

## 트러블슈팅 (문제 해결)

스트림이 대시보드에 표시되지 않거나 오류가 발생할 경우 다음을 확인하세요.

1.  **`.env` 파일 확인**:
    *   `ROBOFLOW_API_KEY`가 올바르게 입력되었는지 확인하세요. 키가 없으면 분석 단계에서 에러가 발생합니다.
    *   `.env.example`을 `.env`로 복사했는지 확인하세요.
2.  **OpenCV 코덱 지원**:
    *   HLS(`.m3u8`)나 RTSP 스트림을 사용하려면 OpenCV가 `ffmpeg`를 지원해야 합니다.
    *   웹캠(URL에 `0` 입력)이 작동하는지 먼저 테스트하여 OpenCV 설치 상태를 확인하세요.
3.  **로그 확인**:
    *   터미널에서 `uvicorn` 실행 로그를 확인하세요. `failed to open stream` 또는 `failed to read frame` 메시지가 있는지 확인합니다.
4.  **네트워크**:
    *   입력한 스트림 URL이 브라우저나 VLC 플레이어에서 정상적으로 재생되는지 확인하세요.

## 테스트 실행

```bash
pytest
```

## GitHub 배포

이 저장소는 공개 GitHub 저장소로 푸시하도록 설계되었습니다.

```bash
git init
git add .
git commit -m "Initial gesture event dashboard"
gh repo create AI-vision --public --source=. --remote=origin --push
```
