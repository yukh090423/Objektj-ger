import math
import warnings
from operator import index

import cv2


BLUE_HSV_LOWER = (100, 100, 80)
BLUE_HSV_UPPER = (130, 255, 255)
MIN_MARKER_AREA_PX2 = 25


def detect_marker(
    frame, *, roi=None, hsv_lower=BLUE_HSV_LOWER, hsv_upper=BLUE_HSV_UPPER,
    min_area=MIN_MARKER_AREA_PX2,
):
    """마커 중심을 원본 프레임의 픽셀 좌표로 반환한다.

    roi는 레일의 전체 이동 범위를 포함하는 (x, y, 너비, 높이)이다.
    roi가 None이면 전체 프레임을 탐색한다. 검출 실패 시 None을 반환한다.
    """
    if not math.isfinite(min_area) or min_area <= 0:
        raise ValueError("최소 윤곽 면적은 유한한 양수여야 합니다.")

    x, y = 0, 0
    if roi is not None:
        try:
            x, y, width, height = map(index, roi)
        except (TypeError, ValueError) as error:
            raise ValueError("탐색 영역은 정수 (x, y, 너비, 높이)여야 합니다.") from error

        frame_height, frame_width = frame.shape[:2]
        if not (0 <= x < x + width <= frame_width
                and 0 <= y < y + height <= frame_height):
            raise ValueError("탐색 영역은 프레임 내부에 있어야 합니다.")
        frame = frame[y:y + height, x:x + width]
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_frame, hsv_lower, hsv_upper)
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    largest_contour = max(contours, key=cv2.contourArea, default=None)
    if largest_contour is None or cv2.contourArea(largest_contour) < min_area:
        return None

    # 윤곽의 면적 모멘트로 중심 좌표를 계산한다.
    moments = cv2.moments(largest_contour)
    center_x = moments["m10"] / moments["m00"]
    center_y = moments["m01"] / moments["m00"]
    return center_x + x, center_y + y


def track_marker(
    video, *, roi=None, hsv_lower=BLUE_HSV_LOWER, hsv_upper=BLUE_HSV_UPPER,
    min_area=MIN_MARKER_AREA_PX2,
):
    """첫 프레임부터 (프레임 번호, 시간(초), 픽셀 좌표 또는 None)을 기록한다.

    고정 FPS 영상용이다. 검출 설정은 detect_marker에 전달한다.
    읽은 프레임 수가 메타데이터보다 적으면 경고한다. 영상은 호출자가 닫는다.
    """
    if not video.isOpened():
        raise ValueError("열린 영상이 필요합니다.")

    fps = video.get(cv2.CAP_PROP_FPS)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("영상의 FPS는 유한한 양수여야 합니다.")
    if not video.set(cv2.CAP_PROP_POS_FRAMES, 0):
        raise ValueError("영상의 첫 프레임으로 이동할 수 없습니다.")

    expected_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    observations = []
    while True:
        success, frame = video.read()
        if not success:
            break

        frame_index = len(observations)
        position = detect_marker(
            frame, roi=roi, hsv_lower=hsv_lower, hsv_upper=hsv_upper,
            min_area=min_area,
        )
        observations.append((frame_index, frame_index / fps, position))

    if not observations:
        raise ValueError("영상에서 프레임을 읽을 수 없습니다.")
    if math.isfinite(expected_frames) and expected_frames > len(observations):
        warnings.warn(
            f"영상 읽기가 일찍 끝났을 수 있습니다. "
            f"{len(observations)}개 프레임을 읽었으며 메타데이터에는 "
            f"{expected_frames:g}개가 기록되어 있습니다.",
            RuntimeWarning,
            stacklevel=2,
        )
    return observations
