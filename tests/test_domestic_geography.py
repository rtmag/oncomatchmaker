import sqlite3

import pytest

from schemas.match_results import Site
from schemas.molecular_profile import Location
from trials.geography import (
    find_accessible_site,
    find_nearest_site,
    geographic_access,
    haversine_distance,
)
from trials.pipeline import attach_screening_geography


@pytest.mark.parametrize(
    "city,lat,lon",
    [
        ("Daegu", 35.8714, 128.6014),
        ("Busan", 35.1796, 129.0756),
        ("Changwon", 35.2281, 128.6811),
    ],
)
def test_korean_cities_have_high_access_to_seoul(city, lat, lon):
    distance = haversine_distance(lat, lon, 37.5665, 126.9780)
    domestic = geographic_access(distance, "South Korea", "Korea, Republic of")
    international = geographic_access(distance, "South Korea", "Japan")
    assert domestic["travel_context"] == "domestic"
    assert domestic["score"] >= 75
    assert domestic["score"] > international["score"]


def test_access_site_can_differ_from_nearest_but_must_be_recruiting():
    patient = Location(latitude=0, longitude=0, country="South Korea")
    foreign = Site(
        name="Foreign", latitude=0, longitude=1, country="Japan", status="RECRUITING"
    )
    domestic = Site(
        name="Domestic",
        latitude=0,
        longitude=3,
        country="Republic of Korea",
        status="RECRUITING",
    )
    assert find_nearest_site(patient, [foreign, domestic]).site.name == "Foreign"
    chosen, access = find_accessible_site(patient, [foreign, domestic])
    assert chosen.site.name == "Domestic"
    assert access["travel_context"] == "domestic"
    domestic.status = "ACTIVE_NOT_RECRUITING"
    assert find_accessible_site(patient, [foreign, domestic])[0].site.name == "Foreign"
    foreign.status = "UNKNOWN"
    assert find_accessible_site(patient, [foreign, domestic]) == (None, None)


def test_unknown_country_does_not_receive_domestic_bonus():
    assert geographic_access(300, None, None)["travel_context"] == "country_unknown"
    assert (
        geographic_access(300, "unknown", "unknown")["travel_context"]
        == "country_unknown"
    )
    assert (
        geographic_access(300, "South Korea", None)["score"]
        < geographic_access(300, "KR", "KOR")["score"]
    )
    assert (
        geographic_access(3000, "KR", "KR")["score"]
        < geographic_access(300, "KR", "KR")["score"]
    )


def test_landscape_and_reviewed_site_selection_use_same_policy():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE studies(nct_id, overall_status);
        CREATE TABLE sites(nct_id,status,latitude,longitude,country);
        INSERT INTO studies VALUES('A','RECRUITING'),('B','NOT_YET_RECRUITING');
        INSERT INTO sites VALUES('A','RECRUITING',0,1,'Japan'),
        ('A','RECRUITING',0,3,'Korea, Republic of'),
        ('A','ACTIVE_NOT_RECRUITING',0,0,'South Korea'),
        ('B','RECRUITING',0,0,'South Korea');
    """)
    points = [{"nct_id": n, "distance_km": None, "geography_score": None} for n in "AB"]
    patient = Location(latitude=0, longitude=0, country="South Korea")
    attach_screening_geography(db, points, patient)
    chosen, access = find_accessible_site(
        patient,
        [
            Site(latitude=0, longitude=1, country="Japan", status="RECRUITING"),
            Site(
                latitude=0,
                longitude=3,
                country="Korea, Republic of",
                status="RECRUITING",
            ),
        ],
    )
    assert points[0]["distance_km"] == chosen.distance_km
    assert points[0]["geography_score"] == access["score"]
    assert points[1]["geography_score"] is None


def test_landscape_keeps_nearest_site_per_country_for_travel_filters():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE studies(nct_id, overall_status);
        CREATE TABLE sites(nct_id,status,latitude,longitude,country);
        INSERT INTO studies VALUES('A','RECRUITING');
        INSERT INTO sites VALUES('A','RECRUITING',0,1,'Japan'),
        ('A','RECRUITING',0,3,'South Korea'),
        ('A','RECRUITING',0,4,'South Korea'),
        ('A','ACTIVE_NOT_RECRUITING',0,0,'South Korea');
    """)
    points = [{"nct_id": "A", "clinical_score": 60}]
    attach_screening_geography(
        db, points, Location(latitude=0, longitude=0, country="South Korea")
    )
    sites = points[0]["recruiting_sites"]
    assert len(sites) == 2
    assert {row["site"]["longitude"] for row in sites} == {1, 3}
    assert min(row["distance_km"] for row in sites) < points[0]["distance_km"]
    assert points[0]["clinical_score"] == 60
