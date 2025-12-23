"""Session management for HAC client."""

import json
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import asdict
from hac_client_core.models import SessionInfo


class SessionManager:
    """Manage HAC session persistence and caching."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize session manager.
        
        Args:
            cache_dir: Directory for session cache (default: ~/.cache/hac-client)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "hac-client"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_key(self, base_url: str, username: str, environment: str) -> str:
        """Generate unique key for session."""
        key_str = f"{base_url}:{username}:{environment}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_session_file(self, base_url: str, username: str, environment: str) -> Path:
        """Get path to session cache file."""
        key = self._get_session_key(base_url, username, environment)
        return self.cache_dir / f"session_{key}.json"
    
    def load_session(self, base_url: str, username: str, environment: str) -> Optional[SessionInfo]:
        """Load cached session if available.
        
        Args:
            base_url: HAC base URL
            username: Username
            environment: Environment name
            
        Returns:
            SessionInfo if cached session exists, None otherwise
        """
        session_file = self._get_session_file(base_url, username, environment)
        
        if not session_file.exists():
            return None
        
        try:
            with session_file.open('r') as f:
                data = json.load(f)
            return SessionInfo(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            # Invalid cache file, remove it
            session_file.unlink(missing_ok=True)
            return None
    
    def save_session(self, base_url: str, username: str, environment: str, session: SessionInfo) -> None:
        """Save session to cache.
        
        Args:
            base_url: HAC base URL
            username: Username
            environment: Environment name
            session: Session info to save
        """
        session_file = self._get_session_file(base_url, username, environment)
        
        try:
            with session_file.open('w') as f:
                json.dump(asdict(session), f, indent=2)
        except (IOError, OSError):
            # Ignore errors when saving cache - it's just an optimization
            pass
    
    def remove_session(self, base_url: str, username: str, environment: str) -> None:
        """Remove cached session.
        
        Args:
            base_url: HAC base URL
            username: Username
            environment: Environment name
        """
        session_file = self._get_session_file(base_url, username, environment)
        session_file.unlink(missing_ok=True)

