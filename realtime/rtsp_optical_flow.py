#!/usr/bin/env python3
"""
간단한 RTSP 소비자 + Farneback optical flow 기반 이벤트 PoC

특징:
- 재연결(지수 백오프)
- 프레임 샘플링(처리 FPS 지정)
- Farneback optical flow로 평균 이동량 계산하여 임계치 초과시 이벤트 발생
"""

import argparse
import time
import cv2
import numpy as np


def open_capture(source, timeout=10):
    cap = cv2.VideoCapture(source)
    t0 = time.time()
    while not cap.isOpened() and (time.time() - t0) < timeout:
        time.sleep(0.5)
        cap = cv2.VideoCapture(source)
    return cap


def run(source, process_fps=5, resize_width=640, flow_threshold=1.0, max_retries=6):
    retry = 0
    backoff = 1.0
    prev_gray = None
    last_process_ts = 0
    frame_count = 0

    while True:
        cap = open_capture(source)
        if not cap or not cap.isOpened():
            retry += 1
            if retry > max_retries:
                print(f"Unable to open source after {retry} attempts. Exiting.")
                return
            print(f"Open failed, retry {retry} in {backoff:.1f}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue

        print("Connected to source")
        retry = 0
        backoff = 1.0

        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("Frame read failed or stream ended; reconnecting...")
                    break

                frame_count += 1
                now = time.time()
                # 샘플링: 지정한 process_fps에 맞춰 처리
                if now - last_process_ts < 1.0 / process_fps:
                    continue
                last_process_ts = now

                # 전처리
                h, w = frame.shape[:2]
                if w != resize_width:
                    r = resize_width / float(w)
                    frame = cv2.resize(frame, (resize_width, int(h * r)))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if prev_gray is None:
                    prev_gray = gray
                    continue

                # Farneback optical flow
                flow = cv2.calcOpticalFlowFarneback(prev_gray, gray,
                                                    None,
                                                    0.5, 3, 15, 3, 5, 1.2, 0)
                mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                mean_mag = np.mean(mag)

                # 간단 이벤트 판단
                if mean_mag > flow_threshold:
                    print(f"[EVENT] motion detected mean_flow={mean_mag:.3f} at frame#{frame_count}")

                # 업데이트
                prev_gray = gray

        except KeyboardInterrupt:
            print("Interrupted by user")
            cap.release()
            return
        except Exception as e:
            print("Error during processing:", e)
            cap.release()
            print("Reconnecting...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, help="RTSP URL or video file")
    p.add_argument("--process-fps", type=float, default=5.0, help="How many frames/sec to process (sample)")
    p.add_argument("--resize-width", type=int, default=640, help="Resize width for processing (preserve aspect)")
    p.add_argument("--flow-threshold", type=float, default=1.0, help="Mean flow magnitude threshold for event")
    p.add_argument("--max-retries", type=int, default=6, help="Max open retries before exit")
    args = p.parse_args()

    print("Starting RTSP Optical Flow PoC")
    run(args.source, process_fps=args.process_fps, resize_width=args.resize_width,
        flow_threshold=args.flow_threshold, max_retries=args.max_retries)


if __name__ == "__main__":
    main()
