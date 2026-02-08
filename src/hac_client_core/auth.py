"""Authentication abstraction for HAC client.

Provides a pluggable interface for authenticating HTTP requests to the
SAP Commerce HAC.  Ship with :class:`BasicAuthHandler` for form-based
login.  Extend :class:`AuthHandler` for OAuth, JWT, API-key, or any
other scheme.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import final

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
            request: The prepared HTTP request.
            
        Returns:
            The modified request with authentication applied.
        """

    @abstractmethod
    def get_initial_credentials(self) -> dict[str, str]:
        """Get credentials for initial login form.
        
        Returns:
            Dictionary with credentials
            (e.g. ``{'j_username': 'admin', 'j_password': 'nimda'}``).
        """


@final
class BasicAuthHandler(AuthHandler):
    """Form-based authentication handler for Spring Security.
    
    Provides ``j_username`` / ``j_password`` credentials for the HAC login
    form.  The password reference is cleared from memory when the handler
    is garbage-collected.
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
    
    def get_initial_credentials(self) -> dict[str, str]:
        """Get credentials for Spring Security form login.
        
        Returns credential dictionary.  Can be called multiple times
        (e.g. retries, re-authentication after session expiry).
        """
        return {
            'j_username': self.username,
            'j_password': self._password
        }
    
    def __del__(self):
        """Clear password reference on object destruction."""
        if hasattr(self, '_password'):
            self._password = None

