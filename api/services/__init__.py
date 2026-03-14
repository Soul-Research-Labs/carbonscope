"""CarbonScope API services package."""


class ServiceError(Exception):
    """Base domain error raised by service operations."""

    def __init__(self, detail: str, *, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
