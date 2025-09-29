import os
import datetime
import requests
from fastapi import FastAPI, HTTPException, Query
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
    "https://holidaytaxidispatchsystem.netlify.app",  # Deployed frontend
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

from urllib.parse import quote

@app.get("/api/bookings/from/{dateFrom}/to/{dateTo}")
def get_bookings(
    dateFrom: str,
    dateTo: str,
    page: int = Query(1, ge=1, description="Page number")
):
    """Search for bookings within a date range."""
    headers = {
        "Accept": "application/json",
        "API_KEY": API_KEY,
        "VERSION": "2025-01"
    }

    api_url = f"{END_POINT}/bookings/search/since/{dateFrom}/until/{dateTo}/page/{page}"

    try:
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # 把供應商回應內容也帶回來，方便你看原因
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

@app.post("/api/bookings/{booking_ref}/vehicles/{vehicle_identifier}/location")
def update_location(
    booking_ref: str,
    vehicle_identifier: str,
    update_request: LocationUpdateRequest
):
    """Update the location and status of a specific booking vehicle."""
    # --- 基本驗證 ---
    booking_ref = (booking_ref or "").strip()
    vehicle_identifier = (vehicle_identifier or "").strip()

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

    # --- 預檢：確認 booking 存在（同一把 API_KEY / END_POINT）---
    check_url = f"{END_POINT}/bookings/{quote(booking_ref, safe='')}"
    try:
        check = requests.get(check_url, headers=headers, timeout=15)
        if not (200 <= check.status_code < 300):
            raise HTTPException(
                status_code=400,
                detail=f"Booking '{booking_ref}' not found under this API key/env. "
                       f"Supplier HTTP {check.status_code}: {check.text[:500]}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Network error when verifying booking: {e}")

    # --- 組定位 payload：UTC 時間戳以 Z 結尾 ---
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    formatted_time = now_utc.isoformat(timespec='seconds')
    payload = {
        "timestamp": formatted_time,
        "location": {"lat": update_request.lat, "lng": update_request.lng},
        "status": update_request.status
    }

    # --- 發送定位 ---
    api_url = (
        f"{END_POINT}/bookings/{quote(booking_ref, safe='')}"
        f"/vehicles/{quote(vehicle_identifier, safe='')}/location"
    )

    try:
        resp = requests.post(api_url, headers=headers, json=payload, timeout=15)
        if not (200 <= resp.status_code < 300):
            # 把供應商原文帶回來，定位失敗最常見：未先派車、vehicleIdentifier 不一致
            raise HTTPException(
                status_code=502,
                detail=f"Supplier HTTP {resp.status_code}: {resp.text[:1000]}"
            )
        # 成功但 body 可能為空，避免 .json() 失敗
        try:
            return resp.json()
        except ValueError:
            return {"ok": True, "message": "Location updated (empty body from supplier)"}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"External API error: {e}")

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