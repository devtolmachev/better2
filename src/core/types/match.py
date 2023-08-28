from dataclasses import dataclass
from typing import Any


@dataclass
class MatchItem:
    timer: str
    teams: list[str, str]
    sportname: str
    part: int
    score: dict
    previos_score: str
    general_score: str
    bet: Any
    view_url: str
    data_url: str
