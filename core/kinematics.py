from math import isclose, isfinite


def calculate_kinematics(records):
    """보정 위치 기록에 중앙차분으로 계산한 속도와 가속도를 추가한다.

    각 입력은 (프레임 번호, 시간(초), 위치 또는 None)이다. 입력 순서와
    위치를 보존하고 (프레임 번호, 시간, 위치, 속도, 가속도) 목록을 반환한다.
    속도와 가속도의 단위는 각각 입력 길이 단위/초, 입력 길이 단위/초²이다.
    계산 가능한 세 프레임의 시간 간격이 양수가 아니거나 일정하지 않으면 ValueError를
    발생시킨다. 경계 또는 결측으로 계산할 수 없는 기록은 두 값을 None으로 둔다.
    """
    results = [
        (frame_number, time, position, None, None)
        for frame_number, time, position in records
    ]

    for index in range(1, len(results) - 1):
        previous_frame, previous_time, previous_position, _, _ = results[index - 1]
        frame_number, time, position, _, _ = results[index]
        next_frame, next_time, next_position, _, _ = results[index + 1]

        if previous_position is None or position is None or next_position is None:
            continue
        if previous_frame + 1 != frame_number or frame_number + 1 != next_frame:
            continue

        previous_interval = time - previous_time
        next_interval = next_time - time
        if (
            not isfinite(previous_interval)
            or not isfinite(next_interval)
            or min(previous_interval, next_interval) <= 0
            or not isclose(previous_interval, next_interval, rel_tol=1e-9)
        ):
            raise ValueError("연속 프레임의 시간 간격은 일정한 양수여야 합니다.")

        # 양쪽 시간 간격의 평균으로 부동소수점 반올림 차이를 줄인다.
        dt = (next_time - previous_time) / 2
        velocity = tuple(
            (following - previous) / (2 * dt)
            for previous, following in zip(previous_position, next_position)
        )
        acceleration = tuple(
            ((following - current) - (current - previous)) / dt**2
            for previous, current, following in zip(
                previous_position, position, next_position
            )
        )
        results[index] = (frame_number, time, position, velocity, acceleration)

    return results
