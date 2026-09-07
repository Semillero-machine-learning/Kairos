"""Small pagination helpers shared by list endpoints."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Pagination:
    page: int = 1
    size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size
