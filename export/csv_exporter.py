import csv
from io import StringIO


def export_motion_csv(results, length_unit):
    """분석 기록을 입력 순서대로 CSV 문자열로 바꾸고 결측 성분은 비워 둔다."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "frame",
        "time_s",
        f"x_{length_unit}",
        f"y_{length_unit}",
        f"vx_{length_unit}_per_s",
        f"vy_{length_unit}_per_s",
        f"ax_{length_unit}_per_s2",
        f"ay_{length_unit}_per_s2",
    ])

    for frame, time, position, velocity, acceleration in results:
        row = [frame, time]
        for vector in (position, velocity, acceleration):
            row.extend(("", "") if vector is None else vector)
        writer.writerow(row)

    return output.getvalue()
