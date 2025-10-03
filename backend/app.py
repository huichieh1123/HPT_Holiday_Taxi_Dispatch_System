import os
import datetime
import requests
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Construct path to .env file and load it
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI()

# CORS middleware to allow requests from the frontend
# More secure configuration for production
origins = [
    "https://hpt-holidaytaxidispatchsystem.netlify.app",  # Deployed frontend
    "http://localhost:5173",  # Default Vite dev server port
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load API Key and Endpoint from environment variables
API_KEY = os.getenv('API_KEY')
END_POINT = os.getenv('END_POINT')

if not API_KEY or not END_POINT:
    raise RuntimeError("API_KEY and END_POINT must be set in the .env file")

# Available trip statuses
TRIP_STATUSES = ["BEFORE_PICKUP", "WAITING_FOR_CUSTOMER", "AFTER_PICKUP", "COMPLETED", "NO_SHOW"]

class LocationUpdateRequest(BaseModel):
    lat: float
    lng: float
    status: str

@app.get("/api/bookings")
def get_bookings(
    dateFrom: str,
    dateTo: str,
    page: int = Query(1, ge=1)
):
    """Search for bookings for a specific page within a date range."""
    headers = {
        "Accept": "application/json",
        "API_KEY": API_KEY,
        "VERSION": "2025-01"
    }

    api_url = f"{END_POINT}/bookings/search/since/{dateFrom}/until/{dateTo}/page/{page}"

    try:
        response = requests.get(api_url, headers=headers, timeout=15)

        # Handle 204 No Content for pages that don't exist
        if response.status_code == 204:
            return {"bookings": [], "pagination": {"current_page": page, "has_next_page": False}}

        response.raise_for_status()
        data = response.json()

        # The external API response is expected to be a dictionary
        # with a 'bookings' list and an optional 'more' URL.
        bookings_list = []
        has_next_page = False

        if isinstance(data, dict):
            bookings_list = data.get('bookings', [])
            has_next_page = bool(data.get('more'))
        elif isinstance(data, list):
            # Handle cases where the last page might just be a list
            bookings_list = data

        pagination_info = {
            "current_page": page,
            "has_next_page": has_next_page
        }

        return {"bookings": bookings_list, "pagination": pagination_info}

    except requests.exceptions.RequestException as e:
        # For a 404 from the external API, treat as an empty result for that page.
        if e.response is not None and e.response.status_code == 404:
            return {"bookings": [], "pagination": {"current_page": page, "has_next_page": False}}
        
        detail = f"External API error: {e}"
        if getattr(e, 'response', None) is not None:
            try:
                detail += f" - {e.response.text}"
            except Exception:
                pass
        raise HTTPException(status_code=502, detail=detail)



@app.get("/api/bookings/{booking_ref}")
def get_booking_details(booking_ref: str):
    """Get the full details for a single booking by its reference."""
    headers = {
        "Accept": "application/json",
        "API_KEY": API_KEY,
        "VERSION": "2025-01"
    }
    api_url = f"{END_POINT}/bookings/{booking_ref}"

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        detail = f"External API error: {e}"
        if e.response is not None:
            detail += f" - {e.response.text}"
        raise HTTPException(status_code=502, detail=detail)
    headers = {
        "Accept": "application/json",
        "API_KEY": API_KEY,
        "VERSION": "2025-01"
    }
    # URL format corrected by user
    print(dateFrom, dateTo, page)

    api_url = f"{END_POINT}/bookings/search/since/{dateFrom}/until/{dateTo}/page/{page}"


    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"External API error: {e}")

from urllib.parse import quote

@app.post("/api/bookings/{booking_ref}/vehicles/{vehicle_identifier}/location")
def update_location(
    booking_ref: str,
    vehicle_identifier: str,
    update_request: LocationUpdateRequest
):
    """Update the location and status of a specific booking vehicle."""
    if update_request.status not in TRIP_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid statuses are: {TRIP_STATUSES}")

    if not (-90 <= update_request.lat <= 90 and -180 <= update_request.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid lat/lng range")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "API_KEY": API_KEY,
        "VERSION": "2025-01"
    }

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "timestamp": now_utc.isoformat(timespec='seconds'),
        "location": {"lat": update_request.lat, "lng": update_request.lng},
        "status": update_request.status
    }

    api_url = (
        f"{END_POINT}/bookings/{quote(booking_ref, safe='')}"
        f"/vehicles/{quote(vehicle_identifier, safe='')}/location"
    )

    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=15)
        
        # Default success response
        response_payload = {"success": True, "status_code": resp.status_code, "data": {}}

        if resp.status_code == 200:
            response_payload["reason"] = "OK"
        elif resp.status_code == 202:
            response_payload["reason"] = "BOOKING_DATA_PROVIDED_TOO_EARLY"
        
        if resp.text:
            try:
                response_payload["data"] = resp.json()
            except ValueError:
                response_payload["data"] = {"message": resp.text}

        if 200 <= resp.status_code < 300:
            return response_payload

        # Handle error cases
        error_payload = {
            "success": False,
            "status_code": resp.status_code,
            "message": resp.text
        }
        
        # Simple text matching based on rule.txt
        resp_text = resp.text.lower()
        if "cancelled" in resp_text:
            error_payload["reason"] = "CANCELLED"
        elif "travelled too long ago" in resp_text:
            error_payload["reason"] = "BOOKING_TRAVELLED_TOO_LONG_AGO"
        elif "travels too long in the future" in resp_text:
            error_payload["reason"] = "BOOKING_TRAVELS_TOO_LONG_IN_THE_FUTURE"
        elif "not expected for this booking type" in resp_text:
            error_payload["reason"] = "INFORMATION_NOT_EXPECTED_FOR_THIS_BOOKING_TYPE"
        elif "too many distinct vehicle" in resp_text:
            error_payload["reason"] = "TOO_MANY_DISTINCT_VEHICLE_IDENTIFIERS_FOR_THIS_BOOKING"
        elif "de-allocate a vehicle identifier that does not exist" in resp_text:
            error_payload["reason"] = "ATTEMPT_TO_DE_ALLOCATE_A_VEHICLE_IDENTIFIER_THAT_DOES_NOT_EXIST"
        elif resp.status_code == 404:
            error_payload["reason"] = "NOT_FOUND"
        else:
            error_payload["reason"] = "UNKNOWN_ERROR"

        return JSONResponse(status_code=resp.status_code, content=error_payload)

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Network error during location update: {e}")

class Driver(BaseModel):
    name: str
    phoneNumber: str
    preferredContactMethod: str
    contactMethods: list[str]

class Vehicle(BaseModel):
    brand: str
    model: str
    color: str
    description: str
    registration: str

class DriverUpdateRequest(BaseModel):
    driver: Driver
    vehicle: Vehicle

@app.put("/api/bookings/{booking_ref}/driver")
def update_driver(
    booking_ref: str,
    update_request: DriverUpdateRequest
):
    """Update the driver and vehicle information for a specific booking."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "API_KEY": API_KEY,
        "VERSION": "2025-01"
    }
    if not update_request.vehicle.registration:
        raise HTTPException(status_code=400, detail="Vehicle registration cannot be empty")

    vehicleIdentifier = update_request.vehicle.registration
    api_url = f"{END_POINT}/bookings/{booking_ref}/vehicles/{vehicleIdentifier}"

    payload = update_request.dict()

    try:
        response = requests.put(api_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        detail = f"External API error: {e}"
        if e.response is not None:
            detail += f" - {e.response.text}"
        raise HTTPException(status_code=502, detail=detail)

@app.get("/api/statuses")
def get_statuses():
    """Provide the list of available trip statuses."""
    return TRIP_STATUSES

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)