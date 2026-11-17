import cv2

def load_video(video_path): #영상 불러오기, 실패시 오류 메시지 출력
    video = cv2.VideoCapture(video_path)
    if video.isOpened():
        return video
    else:
        raise ValueError(f"{video_path}파일을 열 수 없습니다.")

def video_information(video): #영상 정보 추출
    fps = video.get(cv2.CAP_PROP_FPS) #초당 프레임
    frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT)) #전체 프레임
    width = video.get(cv2.CAP_PROP_FRAME_WIDTH) #가로 해상도
    height = video.get(cv2.CAP_PROP_FRAME_HEIGHT) #세로 해상도
    duration = frame_count / fps #영상 길이
    video_info = [fps, frame_count, width, height, duration]
    return video_info

def extract_frame(video, frame_num): #특정 프레임 추출, 실패시 오류 메시지 출력 
    video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

    success, frame = video.read()

    if success:
        return frame
    else:
        raise ValueError("프레임 읽기에 실패했습니다.")
