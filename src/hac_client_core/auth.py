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
    """HTTP Basic Authentication handler.
    
    Security: Password reference is cleared from memory when handler is destroyed.
    """
    
    def __init__(self, username: str, password: str):
        """Initialize Basic Auth handler.
        
        Args:
            username: HAC username
            password: HAC password
        """
        self.username = username
        self._password = password
    
    def apply_auth(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Apply HTTP Basic Authentication."""
        return request
    
    def get_initial_credentials(self) -> Dict[str, str]:
        """Get credentials for Spring Security form login.
        
        Returns credential dictionary. Can be called multiple times if needed
        (e.g., retries, multiple authentication attempts).
        """
        return {
            'j_username': self.username,
            'j_password': self._password
        }
    
    def __del__(self):
        """Clear password reference on object destruction."""
        if hasattr(self, '_password'):
            self._password = None

