# src/utils/errors.py
class AppError(Exception):
    """Base error class for application exceptions."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code