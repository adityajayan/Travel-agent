"""Normalized response schemas for all provider domains (M8).

Every provider (real and mock) returns instances of these Pydantic v2 models.
The alias fields ensure PolicyEngine.evaluate() receives the field names it expects
(estimated_cost, cost_per_night, etc.) when serialized via model_dump(by_alias=True).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NormalizedFlightResult(BaseModel):
    flight_id: str
    airline: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration_minutes: int = 0
    stops: int = 0
    cabin_class: str = "economy"
    estimated_cost: float = Field(default=0.0)
    currency: str = "USD"
    fare_rules: dict = Field(default_factory=dict)
    provider: str = ""
    raw_provider_id: str = ""
    seats_available: int = 0

    model_config = {"populate_by_name": True}


class NormalizedHotelResult(BaseModel):
    hotel_id: str
    name: str
    destination: str
    check_in: str
    check_out: str
    cost_per_night: float = Field(default=0.0)
    total_price: float = 0.0
    star_rating: float = 0.0
    rating_score: float = 0.0
    distance_km: float = 0.0
    amenities: list[str] = Field(default_factory=list)
    cancellation_policy: str = ""
    provider: str = ""
    raw_provider_id: str = ""
    rooms_available: int = 0

    model_config = {"populate_by_name": True}


class NormalizedTransportResult(BaseModel):
    transport_id: str
    type: str = ""
    pickup: str = ""
    dropoff: str = ""
    departure_time: Optional[str] = None
    duration_minutes: int = 0
    estimated_cost: float = Field(default=0.0)
    vehicle_class: str = ""
    provider: str = ""
    raw_provider_id: str = ""
    date: str = ""
    eta_minutes: int = 0

    model_config = {"populate_by_name": True}


class NormalizedActivityResult(BaseModel):
    activity_id: str
    name: str = ""
    destination: str = ""
    date: str = ""
    duration_minutes: int = 0
    estimated_cost: float = Field(default=0.0)
    category: str = ""
    rating: float = 0.0
    provider: str = ""
    raw_provider_id: str = ""
    duration_hours: float = 0.0
    spots_available: int = 0

    model_config = {"populate_by_name": True}


class NormalizedBookingConfirmation(BaseModel):
    booking_reference: str
    domain: str
    provider: str = ""
    status: str = "confirmed"
    amount: float = 0.0
    currency: str = "USD"
    cancellation_policy: str = ""
    is_sandbox: bool = False
    raw_details: dict = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class PriceVerification(BaseModel):
    item_id: str
    current_price: float
    original_price: float
    price_changed: bool
    pct_change: float = 0.0
    verified_at: datetime

    model_config = {"populate_by_name": True}


class HoldResult(BaseModel):
    hold_id: str = ""
    item_id: str
    verified_price: float = 0.0
    expires_at: datetime = Field(default_factory=datetime.utcnow)
    provider: str = ""
    supported: bool = True

    model_config = {"populate_by_name": True}


class CancellationPolicy(BaseModel):
    booking_reference: str
    refundable: bool = False
    refund_amount: float = 0.0
    cancellation_fee: float = 0.0
    deadline: Optional[datetime] = None
    policy_text: str = ""
    provider: str = ""

    model_config = {"populate_by_name": True}
