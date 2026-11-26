import json
import warnings
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates

from core.analysis import analyze_video
from core.marker_tracker import BLUE_HSV_LOWER, BLUE_HSV_UPPER, MIN_MARKER_AREA_PX2
from core.video_loader import extract_frame, load_video
from export.csv_exporter import export_motion_csv
from visualization.plots import plot_motion


SAMPLE_CONFIG = Path(__file__).resolve().parents[1] / "data" / "objektjaeger_blue_marker_test.json"
FILTER_MODES = ("필터 끔", "필터 켬", "필터 전후 비교")


@contextmanager
def video_path(source):
    if isinstance(source, Path):
        yield source
        return

    # Close the upload file before OpenCV opens it on Windows.
    with TemporaryDirectory(prefix="objektjaeger-") as directory:
        path = Path(directory) / ("upload" + Path(source.name).suffix.lower())
        path.write_bytes(source.getbuffer())
        yield path


def first_frame(source):
    with video_path(source) as path:
        video = load_video(str(path))
        try:
            return extract_frame(video, 0)
        finally:
            video.release()


def analysis_settings(width, height, preset, key):
    calibration = preset.get("calibration", {})
    units = ("mm", "cm", "m")
    distance = st.number_input(
        "두 점 사이의 실제 길이", min_value=0.0,
        value=float(calibration.get("reference_length", 0.0)), key=f"distance-{key}",
    )
    unit = st.selectbox(
        "길이 단위", units, index=units.index(calibration.get("length_unit", "mm")),
        key=f"unit-{key}",
    )
    mode = st.selectbox("사비츠키–골레이 필터", FILTER_MODES, key=f"filter-{key}")

    with st.expander("추적 설정"):
        default_roi = preset.get("tracking", {}).get("roi_xywh")
        restrict = st.checkbox("탐색 영역 지정", value=default_roi is not None, key=f"roi-{key}")
        roi = None
        if restrict:
            values = default_roi or (0, 0, width, height)
            columns = st.columns(2)
            roi = tuple(
                columns[i % 2].number_input(
                    label, min_value=minimum, max_value=maximum, value=value,
                    key=f"roi-{i}-{key}",
                )
                for i, (label, minimum, maximum, value) in enumerate(zip(
                    ("시작 x (px)", "시작 y (px)", "너비 (px)", "높이 (px)"),
                    (0, 0, 1, 1), (width - 1, height - 1, width, height), values,
                ))
            )

        st.caption("OpenCV HSV 범위 · H 0–179, S·V 0–255")
        columns = st.columns(3)
        ranges = [
            columns[i].slider(
                name, 0, maximum, (BLUE_HSV_LOWER[i], BLUE_HSV_UPPER[i]),
                key=f"hsv-{name}-{key}",
            )
            for i, (name, maximum) in enumerate(zip("HSV", (179, 255, 255)))
        ]
        hsv_lower, hsv_upper = (tuple(bounds) for bounds in zip(*ranges))
        min_area = st.number_input(
            "최소 윤곽 면적 (px²)", min_value=1, value=MIN_MARKER_AREA_PX2, key=f"area-{key}",
        )

    return distance, unit, mode, roi, hsv_lower, hsv_upper, min_area


def select_points(frame, roi, state, key):
    height, width = frame.shape[:2]
    preview = frame.copy()
    if roi is not None:
        x, y, w, h = roi
        cv2.rectangle(preview, (x, y), (x + w - 1, y + h - 1), (80, 180, 0), 2)

    points = state["points"]
    if len(points) == 2:
        cv2.line(preview, *points, (0, 170, 255), 2)
    for number, (x, y) in enumerate(points, start=1):
        cv2.circle(preview, (x, y), 6, (0, 170, 255), -1)
        cv2.putText(preview, str(number), (max(0, x - 14), max(18, y - 11)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 100, 220), 2)

    click = streamlit_image_coordinates(
        cv2.cvtColor(preview, cv2.COLOR_BGR2RGB), width="content", cursor="crosshair",
        key=f"frame-{key}-{state['point_revision']}",
    )
    if click and click["unix_time"] != state["last_click"]:
        state["last_click"] = click["unix_time"]
        point = (
            min(width - 1, max(0, round(click["x"] * width / click["width"]))),
            min(height - 1, max(0, round(click["y"] * height / click["height"]))),
        )
        if not points or len(points) == 2:
            state["points"] = [point]
        elif point != points[0]:
            points.append(point)
        st.rerun()

    st.caption("같은 운동 평면에서 실제 거리를 아는 두 점을 선택하세요.")
    if points:
        st.write(" · ".join(f"기준점 {i}: ({x}, {y})" for i, (x, y) in enumerate(points, 1)))
        if st.button("기준점 지우기"):
            state["points"] = []
            state["last_click"] = None
            state["point_revision"] += 1
            st.rerun()


def run_analysis(source, points, distance, mode, options):
    with video_path(source) as path, warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always", RuntimeWarning)
        results = analyze_video(path, *points, distance, use_filter=mode == FILTER_MODES[1], **options)
        comparison = None
        if mode == FILTER_MODES[2]:
            comparison = analyze_video(path, *points, distance, use_filter=True, **options)
    messages = list(dict.fromkeys(str(item.message) for item in notices))
    return results, comparison, messages


def main():
    st.set_page_config(page_title="Objektjäger", layout="wide")
    st.title("Objektjäger")
    st.caption("영상으로 추적 대상의 위치, 속도, 가속도를 측정하세요.")
    choice = st.radio("영상 소스", ("영상 업로드", "합성 테스트 영상"), horizontal=True)
    preset = {}
    if choice == "영상 업로드":
        source = st.file_uploader("분석할 영상", type=("mp4", "avi", "mov", "mkv", "webm"))
        if source is None:
            st.session_state.pop("video_state", None)
            return
        source_key = (source.name, sha256(source.getbuffer()).hexdigest())
        filename = Path(source.name).stem
    else:
        try:
            preset = json.loads(SAMPLE_CONFIG.read_text(encoding="utf-8"))
            source = SAMPLE_CONFIG.parent / preset["video_file"]
        except (OSError, ValueError, KeyError) as error:
            st.error(f"합성 테스트 영상 설정을 열 수 없습니다. {error}")
            return
        source_key = str(source)
        filename = source.stem

    state = st.session_state.get("video_state")
    if state is None or state["source_key"] != source_key:
        try:
            frame = first_frame(source)
        except (OSError, ValueError, cv2.error) as error:
            st.error(f"영상의 첫 프레임을 읽을 수 없습니다. {error}")
            return
        revision = st.session_state.get("source_revision", 0) + 1
        st.session_state.source_revision = revision
        state = {
            "source_key": source_key,
            "frame": frame,
            "points": [tuple(point) for point in preset.get("calibration", {}).get("points_px", [])],
            "last_click": None,
            "point_revision": 0,
            "result": None,
        }
        st.session_state.video_state = state

    frame = state["frame"]
    height, width = frame.shape[:2]
    image_col, settings_col = st.columns((3, 2), gap="large")
    with settings_col:
        st.subheader("분석 설정")
        distance, unit, mode, roi, hsv_lower, hsv_upper, min_area = analysis_settings(
            width, height, preset, st.session_state.source_revision,
        )
        roi_valid = roi is None or (roi[0] + roi[2] <= width and roi[1] + roi[3] <= height)
        if not roi_valid:
            st.error("탐색 영역이 영상의 오른쪽 또는 아래쪽 경계를 벗어났습니다.")
        ready = len(state["points"]) == 2 and distance > 0 and roi_valid
        if not ready and roi_valid:
            st.caption("기준점 두 개와 0보다 큰 기준 길이가 필요합니다.")
        submitted = st.button("분석 실행", type="primary", disabled=not ready)
    with image_col:
        st.subheader("기준점 선택")
        select_points(frame, roi if roi_valid else None, state, st.session_state.source_revision)

    points = tuple(state["points"])
    signature = (points, distance, unit, mode, roi, hsv_lower, hsv_upper, min_area)
    if submitted:
        state["result"] = None
        options = {"roi": roi, "hsv_lower": hsv_lower, "hsv_upper": hsv_upper, "min_area": min_area}
        try:
            with st.spinner("영상에서 추적 대상을 찾고 있습니다…"):
                state["result"] = (signature, run_analysis(source, points, distance, mode, options))
        except (OSError, ValueError, cv2.error) as error:
            st.error(f"분석 실패 · {error}")

    if state["result"] is None:
        return
    saved_signature, (results, comparison, messages) = state["result"]
    if saved_signature != signature:
        st.info("새 설정을 적용하려면 분석을 다시 실행하세요.")
        return

    st.subheader("분석 결과")
    for message in messages:
        st.warning(message)
    detected = sum(position is not None for _, _, position, _, _ in results)
    st.write(f"마커 검출 {detected}/{len(results)}프레임")
    st.plotly_chart(plot_motion(results, unit, filtered_results=comparison))
    st.download_button(
        "필터 끔 CSV 다운로드" if comparison is not None else "CSV 다운로드",
        export_motion_csv(results, unit), f"{filename}-motion.csv", mime="text/csv",
    )
    if comparison is not None:
        st.download_button(
            "필터 켬 CSV 다운로드", export_motion_csv(comparison, unit),
            f"{filename}-motion-filtered.csv", mime="text/csv",
        )


if __name__ == "__main__":
    main()
