"""Location resolution and proximity ranking for explicitly recruiting sites."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import sqlite3
from typing import Any, Iterable, Mapping, Optional, Sequence


EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class PatientLocation:
    city: str
    country: str
    latitude: float
    longitude: float

    def __post_init__(self):
        if not self.city.strip() or not self.country.strip():
            raise ValueError("city and country are required")
        if not math.isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not math.isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")


@dataclass(frozen=True)
class RecruitingSiteDistance:
    nct_id: str
    title: str
    site_ordinal: int
    facility: Optional[str]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    latitude: float
    longitude: float
    distance_km: float
    study_status: str
    site_status: str
    source_url: str
    registry_last_update: Optional[str]
    snapshot_retrieved_at: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["distance_km"] = round(self.distance_km, 1)
        return value


class StaticCityResolver:
    """Resolve configured test cities; a production geocoder can replace this."""

    def __init__(self, cities: Iterable[Mapping[str, Any]]):
        self._locations = [PatientLocation(**dict(city)) for city in cities]

    def resolve(self, text: str) -> PatientLocation:
        query = " ".join(text.casefold().split())
        if not query:
            raise ValueError("city input is required")
        exact = [
            location for location in self._locations
            if query == f"{location.city}, {location.country}".casefold()
        ]
        if exact:
            return exact[0]
        city_only = [location for location in self._locations if query == location.city.casefold()]
        if len(city_only) == 1:
            return city_only[0]
        if len(city_only) > 1:
            raise ValueError("city is ambiguous; include the country")
        raise ValueError("city is not configured in this resolver")


def haversine_km(origin: PatientLocation, latitude: float, longitude: float) -> float:
    """Return great-circle distance; this is not driving or travel distance."""
    lat1, lat2 = math.radians(origin.latitude), math.radians(latitude)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(longitude - origin.longitude)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def nearest_recruiting_sites(
    db: sqlite3.Connection,
    origin: PatientLocation,
    trial_ids: Optional[Sequence[str]] = None,
    limit: int = 10,
    max_distance_km: Optional[float] = None,
) -> list[RecruitingSiteDistance]:
    """Rank open sites after enforcing separate study and site status gates."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if max_distance_km is not None and max_distance_km < 0:
        raise ValueError("max_distance_km cannot be negative")
    identifiers = tuple(dict.fromkeys(trial_ids or ()))
    where = [
        "studies.overall_status='RECRUITING'",
        "sites.status='RECRUITING'",
        "sites.latitude IS NOT NULL",
        "sites.longitude IS NOT NULL",
    ]
    parameters: list[Any] = []
    if trial_ids is not None:
        if not identifiers:
            return []
        where.append("studies.nct_id IN ({})".format(",".join("?" for _ in identifiers)))
        parameters.extend(identifiers)
    query = """
        SELECT studies.nct_id, studies.title, sites.ordinal, sites.facility,
               sites.city, sites.region, sites.country, sites.latitude,
               sites.longitude, studies.overall_status AS study_status,
               sites.status AS site_status, studies.source_url,
               studies.last_update_posted, studies.retrieved_at
        FROM sites JOIN studies USING(nct_id)
        WHERE {}
    """.format(" AND ".join(where))
    rows = []
    for row in db.execute(query, parameters):
        distance = haversine_km(origin, row[7], row[8])
        if max_distance_km is not None and distance > max_distance_km:
            continue
        rows.append((distance, row))
    rows.sort(key=lambda item: (item[0], item[1][0], item[1][2]))
    unique_rows = []
    seen = set()
    for distance, row in rows:
        identity = (row[0], row[3], row[4], row[5], row[6], row[7], row[8])
        if identity in seen:
            continue
        seen.add(identity)
        unique_rows.append((distance, row))
    return [
        RecruitingSiteDistance(
            nct_id=row[0], title=row[1], site_ordinal=row[2], facility=row[3], city=row[4],
            region=row[5], country=row[6], latitude=row[7], longitude=row[8],
            distance_km=distance, study_status=row[9], site_status=row[10],
            source_url=row[11], registry_last_update=row[12], snapshot_retrieved_at=row[13],
        )
        for distance, row in unique_rows[:limit]
    ]
