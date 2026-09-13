from schemas.match_results import Site, TrialCandidate


def parse_trial(record):
    protocol = record["protocolSection"]
    identification = protocol["identificationModule"]
    eligibility = protocol.get("eligibilityModule", {})
    sites = []
    for raw in protocol.get("contactsLocationsModule", {}).get("locations", []):
        geo = raw.get("geoPoint") or {}
        lat, lon = geo.get("lat"), geo.get("lon")
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            lat, lon = None, None
        sites.append(
            Site(
                name=raw.get("facility") or "Unknown facility",
                status=raw.get("status") or "UNKNOWN",
                city=raw.get("city"),
                country=raw.get("country"),
                latitude=lat,
                longitude=lon,
                contacts=raw.get("contacts", []),
            )
        )
    nct_id = identification["nctId"]
    return TrialCandidate(
        nct_id=nct_id,
        title=identification.get("officialTitle") or identification["briefTitle"],
        status=protocol.get("statusModule", {}).get("overallStatus", "UNKNOWN"),
        phase=protocol.get("designModule", {}).get("phases", []),
        conditions=protocol.get("conditionsModule", {}).get("conditions", []),
        interventions=[
            i["name"]
            for i in protocol.get("armsInterventionsModule", {}).get(
                "interventions", []
            )
            if "name" in i
        ],
        eligibility_text=eligibility.get("eligibilityCriteria", ""),
        minimum_age=eligibility.get("minimumAge"),
        maximum_age=eligibility.get("maximumAge"),
        sex=eligibility.get("sex"),
        sites=sites,
        sources=[f"https://clinicaltrials.gov/study/{nct_id}"],
        retrieved_at=record["_retrieved_at"],
        cached=record.get("_cached", False),
        expanded_access=protocol.get("statusModule", {})
        .get("expandedAccessInfo", {})
        .get("hasExpandedAccess"),
        registry_updated_at=protocol.get("statusModule", {})
        .get("lastUpdatePostDateStruct", {})
        .get("date"),
    )
