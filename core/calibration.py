def cal_pixel(point1, point2): #사용자가 입력한 두 점을 기반으로 픽셀 거리를 계산
    pixel_distance = ((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2) ** 0.5
    return pixel_distance

def cal_scale(pixel_distance, real_distance): #픽셀 거리와 실제 거리를 비율로 계산
    if pixel_distance == 0: #같은 점 클릭 시 예외처리
        raise ValueError("픽셀 거리가 0입니다.")
    scale = real_distance / pixel_distance
    return scale

def convert_coordinates(pixel_coordinates, scale): #픽셀 좌표를 실제 좌표로 변환
    if pixel_coordinates is None:
        return None

    coor_x = pixel_coordinates[0] * scale
    coor_y = pixel_coordinates[1] * scale
    real_coordinates = [coor_x, coor_y]
    return real_coordinates

def set_origin(coordinates):
    """프레임별 좌표를 첫 검출 좌표 기준으로 옮기고 None을 보존한다."""
    positions = list(coordinates)
    origin = next((position for position in positions if position is not None), None)
    if origin is None:
        return positions

    origin_x, origin_y = origin
    return [
        None if position is None else (position[0] - origin_x, position[1] - origin_y)
        for position in positions
    ]
