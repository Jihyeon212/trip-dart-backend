from math import asin, cos, radians, sin, sqrt


def calculate_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius = 6371.0
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    value = (
        sin(delta_lat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(delta_lon / 2) ** 2
    )
    clamped_value = min(1.0, max(0.0, value))
    return 2 * radius * asin(sqrt(clamped_value))
