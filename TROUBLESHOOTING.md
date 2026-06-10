# 트러블슈팅 가이드 (TROUBLESHOOTING.md)

이 문서는 프로젝트 개발 및 실행 중 발생한 에러와 그 해결 과정을 기록합니다.

---

## 1. 포트 충돌 에러 (Address already in use)

### **현상**
서버 실행 시 다음과 같은 에러 메시지 발생:
`[Errno 48] error while attempting to bind on address ('127.0.0.1', 8000): address already in use`

### **원인**
이미 다른 프로세스(이전의 uvicorn 서버 등)가 8000번 포트를 사용 중임.

### **해결 방법**
1. 8000번 포트를 점유 중인 PID 확인: `lsof -i :8000`
2. 해당 프로세스 종료: `kill -9 <PID>`
3. 또는 다른 포트로 실행: `uvicorn app.main:app --port 8001`

---

## 2. API 유효성 검사 에러 (422 Unprocessable Content)

### **현상**
대시보드에서 `Start Stream` 버튼 클릭 시 브라우저 콘솔 및 서버 로그에 `422` 에러 발생.

### **원인**
`app/models.py`의 `StreamStartRequest` 클래스에서 `stream_url`에 대한 유효성 검사 로직이 너무 엄격하여, 숫자(웹캠)나 특정 형식의 주소를 거부함.

### **해결 방법**
- `models.py` 내 `validate_stream_url` 메서드를 수정하여 숫자로 된 입력(문자열 형태의 숫자)을 허용하도록 변경함.

---

## 3. 로컬 웹캠 인식 실패

### **현상**
주소창에 `0`을 입력해도 웹캠이 켜지지 않고 에러 발생.

### **원인**
OpenCV의 `cv2.VideoCapture()`는 로컬 웹캠 호출 시 정수(`0`, `1` 등)를 인자로 받아야 하는데, 백엔드에서 문자열 `"0"`으로 그대로 전달하여 발생한 문제.

### **해결 방법**
- `app/stream_processor.py`에서 `stream_url`이 숫자로만 구성된 경우 `int()`로 형변환하여 전달하도록 로직 수정.

---

## 4. 스트림 로딩 지연 및 미표시

### **현상**
스트림 연결은 되었으나 화면이 나오지 않음.

### **원인**
Roboflow API 키 미설정 또는 잘못된 스트림 코덱 지원 여부.

### **해결 방법**
- `.env` 파일에 유효한 `ROBOFLOW_API_KEY`가 있는지 확인.
- OpenCV 설치 상태 및 `ffmpeg` 지원 여부 확인 권장.

---

## 5. NameError: name 'cv2' is not defined

### **현상**
스트림 시작 시 서버 로그에 `NameError: name 'cv2' is not defined`가 출력되며 화면에 프레임이 나오지 않음.

### **원인**
`import cv2`가 특정 메서드(`_run`) 내부에만 선언되어 있어, 동일한 클래스의 다른 메서드(`_write_frame`)에서 `cv2`를 참조하지 못해 발생함.

### **해결 방법**
- `import cv2`를 파일 상단(Module Level)으로 이동하여 파일 내 모든 메서드에서 전역적으로 참조할 수 있도록 수정함.

---

## 6. 서버 시작 실패: IndentationError

### **현상**
`uvicorn app.main:app` 실행 시 다음과 같은 에러가 발생하며 서버가 시작되지 않음.

`IndentationError: unexpected indent`

### **원인**
`app/stream_processor.py`에 중복된 `_set_error` 메서드 정의와 깨진 문자열(`ath`)이 남아 있어 Python import 단계에서 실패함.

### **해결 방법**
- 중복 `_set_error` 정의를 제거함.
- 깨진 문자열을 삭제함.
- `python -m py_compile app/stream_processor.py app/main.py`로 import 문법 오류가 사라졌는지 확인함.

---

## 7. 로컬 서버 바인딩 실패: operation not permitted

### **현상**
서버 실행 시 다음과 같은 에러가 발생함.

`[Errno 1] error while attempting to bind on address ('127.0.0.1', 8000): operation not permitted`

### **원인**
샌드박스 또는 실행 환경에서 로컬 포트 바인딩 권한이 제한되어 발생함.

### **해결 방법**
- 권한이 허용된 환경에서 `uvicorn`을 실행함.
- 이 환경에서는 승인된 명령으로 다시 실행하여 해결함.
- 8000번 포트가 이미 사용 중이면 `--port 8001`처럼 다른 포트를 사용함.

---

## 8. Roboflow 401 Unauthorized

### **현상**
대시보드의 `Last error` 또는 `/streams/status` 응답에 다음 유형의 오류가 표시됨.

`401 Client Error: Unauthorized`

### **원인**
다음 중 하나일 가능성이 높음.

- `ROBOFLOW_API_KEY`가 잘못됨
- API 키가 만료되었거나 폐기됨
- API 키가 해당 `ROBOFLOW_MODEL_ID`에 접근 권한이 없음
- 모델 ID가 잘못되었거나 계정에서 접근할 수 없는 모델임

### **해결 방법**
1. Roboflow에서 새 API 키를 발급함.
2. `.env`의 `ROBOFLOW_API_KEY`를 새 키로 교체함.
3. `.env`의 `ROBOFLOW_MODEL_ID`가 실제 접근 가능한 모델인지 확인함.
4. 서버를 재시작함.

### **주의 사항**
- API 키를 채팅, 로그, 문서에 직접 붙여넣지 않음.
- 노출된 키는 Roboflow에서 폐기하고 새로 발급함.
- 현재 코드는 Roboflow 오류 메시지의 `api_key` 값을 마스킹하도록 수정되어 있음.

---

## 9. 영상 프레임은 보이지만 제스처 감지가 되지 않음

### **현상**
대시보드에 카메라 또는 스트림 프레임은 표시되지만 `Detections`, `Event Log`가 비어 있음.

### **확인 방법**
`/streams/status` 응답에서 다음 값을 확인함.

- `frame_count`가 증가함: 영상 입력은 들어오고 있음
- `analyzed_count`가 0이거나 증가하지 않음: Roboflow 분석이 성공하지 않음
- `last_error`가 존재함: 분석 단계에서 오류 발생

### **원인**
영상 캡처와 AI 분석은 별도 단계임. 프레임은 정상적으로 들어와도 Roboflow 인증, 모델 접근, 네트워크, rate limit 문제가 있으면 감지는 실패할 수 있음.

### **해결 방법**
- `last_error`를 확인함.
- 401/403이면 API 키와 모델 권한을 확인함.
- 429이면 sample FPS를 낮추거나 잠시 후 재시도함.
- 5xx이면 Roboflow 서비스 장애 가능성이 있으므로 재시도함.

---

## 10. 영상 렌더링이 느림

### **현상**
대시보드의 영상이 느리게 갱신되거나 Roboflow 요청이 느릴 때 화면 갱신도 함께 지연됨.

### **원인**
초기 구조에서는 프레임 저장, Roboflow 분석 요청, 최신 프레임 갱신이 같은 처리 흐름에 묶여 있었음. Roboflow API 응답이 느리면 다음 프레임 표시도 지연될 수 있었음.

### **해결 방법**
- 영상 프레임 갱신과 Roboflow 분석 요청을 분리함.
- 최신 프레임은 메모리 JPEG로 서빙하도록 개선함.
- 분석용 임시 파일은 이벤트 스냅샷으로 쓰이지 않으면 삭제하도록 개선함.
- 프론트엔드 상태 갱신 주기를 2초에서 0.5초로 줄임.

---

## 11. 감지 박스가 영상 위치와 맞지 않음

### **현상**
감지 결과는 나오지만 bbox overlay가 실제 손 위치와 어긋나 보임.

### **원인**
이미지는 CSS `object-fit: contain`으로 표시되는데, 기존 overlay 좌표는 원본 이미지 좌표를 화면 좌표로 변환하지 않고 그대로 사용했음.

### **해결 방법**
- 이미지의 `naturalWidth`, `naturalHeight`와 canvas 표시 크기를 기준으로 scale과 offset을 계산함.
- letterbox 영역을 고려해 bbox 좌표를 보정함.
