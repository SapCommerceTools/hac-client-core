"""Session management for HAC client."""

import json
import hashlib
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class SessionMetadata:
    """Metadata about a HAC session."""
    
    session_id: str
    """JSESSIONID"""
    
    csrf_token: str
    """CSRF token"""
    
    route_cookie: Optional[str]
    """ROUTE cookie for load balancer affinity"""
    
    environment: str
    """Environment identifier (environment or environment/endpoint)"""
    
    base_url: str
    """HAC base URL"""
    
    username: str
    """Username"""
    
    created_at: float
    """Timestamp when session was created"""
    
    last_used_at: float
    """Timestamp when session was last used"""
    
    is_authenticated: bool = True
    """Whether session is authenticated"""
    
    @property
    def age_seconds(self) -> float:
        """Get session age in seconds."""
        return time.time() - self.created_at
    
    @property
    def idle_seconds(self) -> float:
        """Get time since last use in seconds."""
        return time.time() - self.last_used_at
    
    @property
    def created_at_formatted(self) -> str:
        """Get formatted creation time."""
        return datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def last_used_at_formatted(self) -> str:
        """Get formatted last used time."""
        return datetime.fromtimestamp(self.last_used_at).strftime("%Y-%m-%d %H:%M:%S")


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
        """Generate unique key for session.
        
        Note: environment can be just 'env' or 'env/endpoint' for composite keys.
        """
        key_str = f"{base_url}:{username}:{environment}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_session_file(self, base_url: str, username: str, environment: str) -> Path:
        """Get path to session cache file."""
        key = self._get_session_key(base_url, username, environment)
        return self.cache_dir / f"session_{key}.json"
    
    def load_session(self, base_url: str, username: str, environment: str) -> Optional[SessionMetadata]:
        """Load cached session if available.
        
        Args:
            base_url: HAC base URL
            username: Username
            environment: Environment identifier (e.g., 'local' or 'local/hac')
            
        Returns:
            SessionMetadata if cached session exists, None otherwise
        """
        session_file = self._get_session_file(base_url, username, environment)
        
        if not session_file.exists():
            return None
        
        try:
            with session_file.open('r') as f:
                data = json.load(f)
            return SessionMetadata(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            # Invalid cache file, remove it
            session_file.unlink(missing_ok=True)
            return None
    
    def save_session(
        self,
        base_url: str,
        username: str,
        environment: str,
        session_id: str,
        csrf_token: str,
        route_cookie: Optional[str] = None
    ) -> None:
        """Save session to cache.
        
        Args:
            base_url: HAC base URL
            username: Username
            environment: Environment identifier (e.g., 'local' or 'local/hac')
            session_id: Session ID
            csrf_token: CSRF token
            route_cookie: Optional ROUTE cookie
        """
        session_file = self._get_session_file(base_url, username, environment)
        
        # Check if we're updating existing session
        existing = self.load_session(base_url, username, environment)
        created_at = existing.created_at if existing else time.time()
        
        metadata = SessionMetadata(
            session_id=session_id,
            csrf_token=csrf_token,
            route_cookie=route_cookie,
            environment=environment,
            base_url=base_url,
            username=username,
            created_at=created_at,
            last_used_at=time.time(),
            is_authenticated=True
        )
        
        try:
            # Ensure parent directory exists
            session_file.parent.mkdir(parents=True, exist_ok=True)
            with session_file.open('w') as f:
                json.dump(asdict(metadata), f, indent=2)
        except (IOError, OSError):
            # Ignore errors when saving cache - it's just an optimization
            pass
    
    def remove_session(self, base_url: str, username: str, environment: str) -> None:
        """Remove cached session.
        
        Args:
            base_url: HAC base URL
            username: Username
            environment: Environment identifier (e.g., 'local' or 'local/hac')
        """
        session_file = self._get_session_file(base_url, username, environment)
        session_file.unlink(missing_ok=True)
    
    def list_sessions(self) -> List[SessionMetadata]:
        """List all cached sessions.
        
        Returns:
            List of SessionMetadata for all cached sessions
        """
        sessions = []
        
        if not self.cache_dir.exists():
            return sessions
        
        for session_file in self.cache_dir.glob("session_*.json"):
            try:
                with session_file.open('r') as f:
                    data = json.load(f)
                sessions.append(SessionMetadata(**data))
            except (json.JSONDecodeError, TypeError, KeyError):
                # Invalid file, skip it
                continue
        
        return sorted(sessions, key=lambda s: s.last_used_at, reverse=True)
    
    def clear_all_sessions(self) -> int:
        """Clear all cached sessions.
        
        Returns:
            Number of sessions cleared
        """
        count = 0
        if self.cache_dir.exists():
            for session_file in self.cache_dir.glob("session_*.json"):
                session_file.unlink(missing_ok=True)
                count += 1
        return count
