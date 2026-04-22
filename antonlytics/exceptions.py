"""
Custom exceptions for Antonlytics SDK.
"""


class AntonlyticsError(Exception):
    """Base exception for all Antonlytics SDK errors."""
    pass


class APIError(AntonlyticsError):
    """Exception raised for API errors."""
    
    def __init__(self, message: str, status_code: int = None):
        """
        Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
        """
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(AntonlyticsError):
    """Exception raised for authentication errors."""
    pass
