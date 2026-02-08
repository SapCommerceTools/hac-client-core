"""Data models for HAC API responses.

All models are plain :mod:`dataclasses` with no external dependencies so
they can be serialised, compared, and used in tests without side effects.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Optional


def _html_to_text(html_content: str) -> str:
    """Convert HAC HTML log output to plain text."""
    text = html_content.replace('<br/>', '\n').replace('<br>', '\n')
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


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
    
    headers: list[str]
    """Column headers"""
    
    rows: list[list[str]]
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
    
    validation_errors: Optional[list[str]] = None
    """List of validation errors"""
    
    def __post_init__(self) -> None:
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


@dataclass
class UpdateParameter:
    """Parameter for a project data extension."""
    
    name: str
    """Parameter name (e.g., 'Patch_MVP', 'importCoreData')"""
    
    label: str
    """Display label for the parameter"""
    
    values: dict[str, bool]
    """Available values and their selected state (e.g. ``{'yes': True, 'no': False}``)"""
    
    legacy: bool = False
    """Whether this is a legacy parameter"""
    
    multi_select: bool = False
    """Whether multiple values can be selected"""
    
    default: Optional[str] = None
    """Default value if any"""
    
    @property
    def selected_value(self) -> Optional[str]:
        """Get the currently selected value."""
        for value, selected in self.values.items():
            if selected:
                return value
        return None
    
    @property
    def available_values(self) -> list[str]:
        """Get list of available values."""
        return list(self.values.keys())


@dataclass
class ProjectData:
    """Project data extension information."""
    
    name: str
    """Extension name (e.g., 'cchpatches', 'cchinitialdata')"""
    
    description: Optional[str]
    """Extension description"""
    
    parameters: list[UpdateParameter]
    """Configurable parameters for this extension"""
    
    @property
    def has_parameters(self) -> bool:
        """Whether this extension has configurable parameters."""
        return len(self.parameters) > 0


@dataclass
class UpdateData:
    """System update data from HAC."""
    
    is_initializing: bool
    """Whether an initialization is currently in progress"""
    
    project_datas: list[ProjectData]
    """List of project data extensions"""
    
    @property
    def extensions_with_parameters(self) -> list[ProjectData]:
        """Get extensions that have configurable parameters."""
        return [pd for pd in self.project_datas if pd.has_parameters]
    
    def get_extension(self, name: str) -> Optional[ProjectData]:
        """Get a specific extension by name."""
        for pd in self.project_datas:
            if pd.name == name:
                return pd
        return None
    
    def get_patches_extension(self) -> Optional[ProjectData]:
        """Get the patches extension (commonly 'cchpatches' or similar).
        
        Prefers extensions that:
        1. Have 'patches' in name AND have parameters (most likely the real patches)
        2. Have a prefix before 'patches' (e.g., cchpatches, mypatches) - not just 'patches'
        3. Any extension with 'patches' in name as fallback
        """
        candidates = [pd for pd in self.project_datas if 'patches' in pd.name.lower()]
        
        if not candidates:
            return None
        
        # Prefer extensions with parameters
        with_params = [pd for pd in candidates if pd.has_parameters]
        if with_params:
            # Among those with params, prefer project-specific ones (not just 'patches')
            project_specific = [pd for pd in with_params if pd.name.lower() != 'patches']
            if project_specific:
                return project_specific[0]
            return with_params[0]
        
        # No extensions have parameters, prefer project-specific names
        project_specific = [pd for pd in candidates 
                           if pd.name.lower().endswith('patches') and pd.name.lower() != 'patches']
        if project_specific:
            return project_specific[0]
        
        return candidates[0]


@dataclass
class UpdateResult:
    """Result from system update execution."""
    
    success: bool
    """Whether the update succeeded"""
    
    log_html: str
    """HTML log content from the update"""
    
    @property
    def log_text(self) -> str:
        """Convert HTML log to plain text."""
        return _html_to_text(self.log_html)
    
    @property
    def is_finished(self) -> bool:
        """Check if the update is finished."""
        return 'FINISHED' in self.log_html or 'finished' in self.log_html.lower()


@dataclass
class UpdateLog:
    """Update progress log from HAC (for polling during long updates)."""
    
    log_html: str
    """Raw HTML log content"""
    
    @property
    def log_text(self) -> str:
        """Convert HTML log to plain text."""
        return _html_to_text(self.log_html)
    
    @property
    def is_complete(self) -> bool:
        """Check if the update appears to be complete."""
        text = self.log_text.lower()
        return (
            'update finished' in text or
            'initialization finished' in text or
            'completed successfully' in text or
            'update completed' in text
        )
    
    @property
    def has_errors(self) -> bool:
        """Check if the log contains errors."""
        text = self.log_text.lower()
        return 'error' in text or 'exception' in text or 'failed' in text
