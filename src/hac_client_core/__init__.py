"""HAC Client Core — Python client for the SAP Commerce HAC HTTP API.

Provides programmatic access to core HAC operations:

* Groovy script execution with commit/rollback modes
* FlexibleSearch queries with result pagination
* Impex import operations
* System update / initialization triggering and log polling
* Session management with caching and CSRF protection
* Pluggable authentication (Basic Auth, extensible for OAuth, etc.)

Typical usage::

    from hac_client_core import HacClient, BasicAuthHandler

    auth = BasicAuthHandler("admin", "nimda")
    client = HacClient("https://localhost:9002", auth_handler=auth)
    client.login()

    result = client.execute_groovy("return 'Hello'")
    print(result.execution_result)
"""

from hac_client_core.client import HacClient, HacClientError, HacAuthenticationError
from hac_client_core.auth import AuthHandler, BasicAuthHandler
from hac_client_core.models import (
    GroovyScriptResult,
    FlexibleSearchResult,
    ImpexResult,
    SessionInfo,
    UpdateData,
    UpdateParameter,
    ProjectData,
    UpdateLog,
    UpdateResult,
)
from hac_client_core.session import SessionManager, SessionMetadata

__version__ = "0.1.0"

__all__ = [
    # Client
    "HacClient",
    "HacClientError",
    "HacAuthenticationError",
    # Auth
    "AuthHandler",
    "BasicAuthHandler",
    # Models
    "GroovyScriptResult",
    "FlexibleSearchResult",
    "ImpexResult",
    "SessionInfo",
    "UpdateData",
    "UpdateParameter",
    "ProjectData",
    "UpdateLog",
    "UpdateResult",
    # Session
    "SessionManager",
    "SessionMetadata",
]

