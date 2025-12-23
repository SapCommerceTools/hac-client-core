"""Authentication abstraction for HAC client."""

from abc import ABC, abstractmethod
from typing import Dict
import requests


class AuthHandler(ABC):
    """Abstract base class for authentication handlers.
    
    Authentication handlers are responsible for modifying HTTP requests
    to include necessary authentication credentials.
    """
    
    @abstractmethod
    def apply_auth(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Apply authentication to a prepared request.
        
        Args:
            request: The prepared HTTP request
            
        Returns:
            The modified request with authentication applied
        """
        pass
    
    @abstractmethod
    def get_initial_credentials(self) -> Dict[str, str]:
        """Get credentials for initial login form.
        
        Returns:
            Dictionary with credentials (e.g., {'j_username': 'admin', 'j_password': 'nimda'})
        """
        pass


class BasicAuthHandler(AuthHandler):
    """HTTP Basic Authentication handler."""
    
    def __init__(self, username: str, password: str):
        """Initialize Basic Auth handler.
        
        Args:
            username: HAC username
            password: HAC password
        """
        self.username = username
        self.password = password
    
    def apply_auth(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Apply HTTP Basic Authentication.
        
        This is currently not used for HAC since we use form-based login,
        but kept for future extensibility.
        """
        return request
    
    def get_initial_credentials(self) -> Dict[str, str]:
        """Get credentials for Spring Security form login."""
        return {
            'j_username': self.username,
            'j_password': self.password
        }

