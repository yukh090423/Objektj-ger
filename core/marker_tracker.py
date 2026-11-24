import math

import cv2


BLUE_HSV_LOWER = (100, 100, 80)
BLUE_HSV_UPPER = (130, 255, 255)
MIN_MARKER_AREA_PX2 = 25


def detect_marker(frame):
    """BGR 프레임에서 파란 마커의 중심 (x, y)을 픽셀 단위로 반환한다."""
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_frame, BLUE_HSV_LOWER, BLUE_HSV_UPPER)
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    largest_contour = max(contours, key=cv2.contourArea, default=None)
    if largest_contour is None or cv2.contourArea(largest_contour) < MIN_MARKER_AREA_PX2:
        return None

    # 윤곽의 면적 모멘트로 중심 좌표를 계산한다.
    moments = cv2.moments(largest_contour)
    center_x = moments["m10"] / moments["m00"]
    center_y = moments["m01"] / moments["m00"]
    return center_x, center_y


def track_marker(video):
    """첫 프레임부터 (프레임 번호, 시간(초), 픽셀 좌표 또는 None)을 기록한다.

    고정 FPS 영상용이다. 호출자가 영상 객체를 닫을 책임을 진다.
    """
    if not video.isOpened():
        raise ValueError("열린 영상이 필요합니다.")

    fps = video.get(cv2.CAP_PROP_FPS)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("영상의 FPS는 유한한 양수여야 합니다.")
    if not video.set(cv2.CAP_PROP_POS_FRAMES, 0):
        raise ValueError("영상의 첫 프레임으로 이동할 수 없습니다.")

    observations = []
    while True:
        success, frame = video.read()
        if not success:
            break

        frame_index = len(observations)
        position = detect_marker(frame)
        observations.append((frame_index, frame_index / fps, position))

    if not observations:
        raise ValueError("영상에서 프레임을 읽을 수 없습니다.")
    return observations
