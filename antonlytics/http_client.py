"""
HTTP client for making requests to Antonlytics API.
"""

import requests
from typing import Dict, Any
from .exceptions import APIError, AuthenticationError, AntonlyticsError


class HTTPClient:
    """HTTP client for Antonlytics API."""
    
    def __init__(self, api_key: str, base_url: str):
        """
        Initialize HTTP client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'antonlytics-python/2.0.0'
        })
    
    def _make_request(self, method: str, path: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            path: API endpoint path
            data: Request payload
            
        Returns:
            Response JSON data
            
        Raises:
            AuthenticationError: If authentication fails
            APIError: If API returns an error
            AntonlyticsError: For other errors
        """
        url = f"{self.base_url}{path}"
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PATCH':
                response = self.session.patch(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            else:
                raise AntonlyticsError(f"Unsupported HTTP method: {method}")
            
            # Handle different status codes
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or unauthorized")
            elif response.status_code == 403:
                raise AuthenticationError("Access forbidden")
            elif response.status_code == 404:
                raise APIError(f"Resource not found: {path}", status_code=404)
            elif response.status_code == 429:
                raise APIError("Rate limit exceeded", status_code=429)
            elif response.status_code >= 500:
                raise APIError(f"Server error: {response.status_code}", status_code=response.status_code)
            elif not response.ok:
                try:
                    error_data = response.json()
                    message = error_data.get('error', error_data.get('detail', response.text))
                except:
                    message = response.text
                raise APIError(f"API error ({response.status_code}): {message}", status_code=response.status_code)
            
            return response.json()
            
        except requests.RequestException as e:
            raise AntonlyticsError(f"Request failed: {str(e)}")
    
    def get(self, path: str) -> Dict[str, Any]:
        """Make GET request."""
        return self._make_request('GET', path)
    
    def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request."""
        return self._make_request('POST', path, data)
    
    def patch(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PATCH request."""
        return self._make_request('PATCH', path, data)
    
    def delete(self, path: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return self._make_request('DELETE', path)
