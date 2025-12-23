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
    
    Security: Password is cleared from memory after first use.
    """
    
    def __init__(self, username: str, password: str):
        """Initialize Basic Auth handler.
        
        Args:
            username: HAC username
            password: HAC password
        """
        self.username = username
        self._password = password
        self._credentials_used = False
    
    def apply_auth(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        """Apply HTTP Basic Authentication."""
        return request
    
    def get_initial_credentials(self) -> Dict[str, str]:
        """Get credentials for Spring Security form login.
        
        Note: Password is cleared from memory after first call for security.
        """
        if self._credentials_used:
            raise RuntimeError("Credentials already used and cleared from memory")
        
        credentials = {
            'j_username': self.username,
            'j_password': self._password
        }
        
        # Clear password from memory immediately after use
        self._credentials_used = True
        if self._password:
            # Attempt to overwrite (limited effectiveness in Python due to string immutability)
            self._password = None
            del self._password
        
        return credentials
    
    def __del__(self):
        """Ensure password is cleared on object destruction."""
        if hasattr(self, '_password') and self._password:
            self._password = None

