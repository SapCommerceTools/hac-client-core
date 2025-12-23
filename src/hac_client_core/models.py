"""Data models for HAC API responses."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class GroovyScriptResult:
    """Result from Groovy script execution."""
    
    output_text: str
    """Console output from the script"""
    
    execution_result: str
    """The return value of the script"""
    
    stacktrace_text: Optional[str] = None
    """Error stacktrace if script failed"""
    
    commit_mode: bool = False
    """Whether script was executed in commit mode"""
    
    execution_time_ms: Optional[int] = None
    """Execution time in milliseconds"""
    
    @property
    def success(self) -> bool:
        """Whether the script executed successfully."""
        return self.stacktrace_text is None or len(self.stacktrace_text.strip()) == 0


@dataclass
class FlexibleSearchResult:
    """Result from FlexibleSearch query execution."""
    
    headers: List[str]
    """Column headers"""
    
    rows: List[List[str]]
    """Result rows"""
    
    result_count: int
    """Number of results returned"""
    
    execution_time_ms: Optional[int] = None
    """Execution time in milliseconds"""
    
    exception: Optional[str] = None
    """Error message if query failed"""
    
    @property
    def success(self) -> bool:
        """Whether the query executed successfully."""
        return self.exception is None


@dataclass
class ImpexResult:
    """Result from Impex import/export operation."""
    
    success: bool
    """Whether the operation succeeded"""
    
    output: str
    """Output text from the operation"""
    
    error: Optional[str] = None
    """Error message if operation failed"""
    
    validation_errors: List[str] = None
    """List of validation errors"""
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


@dataclass
class SessionInfo:
    """HAC session information."""
    
    session_id: str
    """JSESSIONID"""
    
    csrf_token: str
    """CSRF token for POST requests"""
    
    route_cookie: Optional[str] = None
    """ROUTE cookie for load balancer affinity"""
    
    is_authenticated: bool = False
    """Whether session is authenticated"""

