from fastapi import APIRouter
import requests

router = APIRouter()

NASA_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"


@router.get("/satellite")
def satellite():
    response = requests.get(NASA_URL, timeout=10)

    return {
        "status": response.status_code
    }


@router.get("/wildfires")
def get_wildfires():

    response = requests.get(NASA_URL, timeout=10)
    data = response.json()

    wildfires = []

    for event in data.get("events", []):

        for category in event.get("categories", []):

            if category.get("id") == "wildfires":

                wildfires.append({
                    "title": event.get("title"),
                    "event_id": event.get("id"),
                    "category": category.get("title"),
                    "coordinates": event.get("geometry", [{}])[0].get("coordinates")
                })
+
    return wildfires



@router.get("/storms")
def get_storms():

    response = requests.get(NASA_URL, timeout=10)
    data = response.json()

    storms = []

    for event in data.get("events", []):

        for category in event.get("categories", []):

            if category.get("id") == "severeStorms":

                storms.append({
                    "title": event.get("title"),
                    "event_id": event.get("id"),
                    "category": category.get("title"),
                    "coordinates": event.get("geometry", [{}])[0].get("coordinates")
                })

    return storms