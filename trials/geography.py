import math

from schemas.match_results import NearestSite


def haversine_distance(lat1, lon1, lat2, lon2):
    a, b = math.radians(lat1), math.radians(lat2)
    dlat, dlon = b - a, math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def find_nearest_site(patient_location, sites):
    if patient_location.latitude is None or patient_location.longitude is None:
        return None
    candidates = [
        NearestSite(
            site=s,
            distance_km=round(
                haversine_distance(
                    patient_location.latitude,
                    patient_location.longitude,
                    s.latitude,
                    s.longitude,
                ),
                1,
            ),
        )
        for s in sites
        if s.status == "RECRUITING"
        and s.latitude is not None
        and s.longitude is not None
    ]
    return min(candidates, key=lambda s: s.distance_km) if candidates else None
