from math import isfinite

from .calibration import cal_pixel, cal_scale, convert_coordinates, set_origin
from .kinematics import calculate_kinematics
from .marker_tracker import track_marker
from .video_loader import load_video


def analyze_video(
    video_path,
    point1,
    point2,
    real_distance,
    *,
    roi=None,
    hsv_lower=None,
    hsv_upper=None,
    min_area=None,
):
    """영상에서 (프레임 번호, 시간, 위치, 속도, 가속도) 목록을 구한다.

    두 기준점은 원본 프레임의 픽셀 좌표다. 첫 검출점이 위치의 원점이며,
    영상처럼 오른쪽이 +x, 아래쪽이 +y다. 길이 단위는 real_distance를 따른다.
    지정하지 않은 검출 설정에는 추적기의 기본값을 사용한다.
    """
    if not isfinite(real_distance) or real_distance <= 0:
        raise ValueError("기준점 사이의 실제 길이는 유한한 양수여야 합니다.")

    pixel_distance = cal_pixel(point1, point2)
    if pixel_distance == 0:
        raise ValueError("두 기준점이 같은 위치입니다. 서로 다른 점을 선택하세요.")
    if not isfinite(pixel_distance):
        raise ValueError("두 기준점 사이의 픽셀 거리는 유한해야 합니다.")
    scale = cal_scale(pixel_distance, real_distance)

    tracking_options = {
        "roi": roi,
        "hsv_lower": hsv_lower,
        "hsv_upper": hsv_upper,
        "min_area": min_area,
    }
    tracking_options = {
        name: value for name, value in tracking_options.items() if value is not None
    }
    video = load_video(str(video_path))
    try:
        observations = track_marker(video, **tracking_options)
    finally:
        video.release()

    if all(position is None for _, _, position in observations):
        raise ValueError("모든 프레임에서 마커를 검출하지 못했습니다. ROI와 색상 설정을 확인하세요.")

    relative_positions = set_origin(position for _, _, position in observations)
    calibrated = [
        (frame_number, time, convert_coordinates(position, scale))
        for (frame_number, time, _), position in zip(observations, relative_positions)
    ]
    return calculate_kinematics(calibrated)
