from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeviceState:
    id: str  # MAC / Address
    name: str
    game_name: str
    score: int = 0
    color: str = field(default_factory=str)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "game_name": self.game_name,
            "score": self.score,
            "color": self.color,
        }
