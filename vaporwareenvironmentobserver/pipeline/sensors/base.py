from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSensor(ABC):
    """One environmental sensor: reads a single snapshot on demand.

    Unlike VaporwareSoundObserver's continuous mic stream, environmental
    readings are point-in-time polls rather than a shared buffer, so each
    sensor just returns its latest reading when asked.
    """

    @abstractmethod
    def read(self) -> dict | None: ...
