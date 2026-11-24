from operator import index

from scipy.signal import savgol_filter


def smooth_positions(records, *, window_length=5, polyorder=2):
    """연속 프레임의 x, y를 평활화하고 완전한 중앙 창이 없는 위치는 None으로 둔다.

    입력과 반환값은 (프레임 번호, 시간(초), 2차원 위치 또는 None) 기록이다.
    미검출과 프레임 번호 누락은 각각 구간을 끊는다.
    """
    try:
        window_length = index(window_length)
        polyorder = index(polyorder)
    except TypeError as error:
        raise ValueError("window_length와 polyorder는 정수여야 합니다.") from error
    if window_length <= 0 or window_length % 2 == 0:
        raise ValueError("window_length는 양의 홀수여야 합니다.")
    if not 0 <= polyorder < window_length:
        raise ValueError("polyorder는 0 이상이고 window_length보다 작아야 합니다.")

    records = list(records)
    result = [(frame, time, None) for frame, time, _ in records]
    half_window = window_length // 2
    start = 0

    while start < len(records):
        if records[start][2] is None:
            start += 1
            continue

        end = start + 1
        while (
            end < len(records)
            and records[end][2] is not None
            and records[end][0] == records[end - 1][0] + 1
        ):
            end += 1

        if end - start >= window_length:
            positions = [position for _, _, position in records[start:end]]
            smoothed = savgol_filter(
                positions, window_length, polyorder, deriv=0, axis=0, mode="constant"
            )
            # SciPy가 경계에서 계산한 값은 완전한 중앙 창을 사용하지 않는다.
            for offset in range(half_window, len(positions) - half_window):
                frame, time, _ = records[start + offset]
                x, y = smoothed[offset]
                result[start + offset] = (frame, time, (float(x), float(y)))

        start = end

    return result
