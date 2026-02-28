"""Typed parameter dataclass for cross-agent parameter passing (M4)."""
import dataclasses
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedParams:
    arrival_city: Optional[str] = None
    arrival_airport: Optional[str] = None
    departure_city: Optional[str] = None
    departure_airport: Optional[str] = None
    check_in_date: Optional[str] = None       # ISO 8601
    check_out_date: Optional[str] = None       # ISO 8601
    destination_city: Optional[str] = None
    travel_dates: list = field(default_factory=list)
    num_travelers: int = 1

    def to_dict(self) -> dict:
        """Serialize as a flat dict via dataclasses.asdict()."""
        return dataclasses.asdict(self)
