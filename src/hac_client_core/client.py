"""HAC HTTP client implementation."""

from __future__ import annotations

import json
import sys
import time
import warnings
from typing import Any, NoReturn, Optional, final
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from hac_client_core.auth import AuthHandler
from hac_client_core.models import (
    FlexibleSearchResult,
    GroovyScriptResult,
    ImpexResult,
    ProjectData,
    SessionInfo,
    UpdateData,
    UpdateLog,
    UpdateParameter,
    UpdateResult,
)
from hac_client_core.session import SessionManager

# Suppress SSL warnings when ignore_ssl is enabled
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class HacClientError(Exception):
    """Base exception for HAC client errors."""


@final
class HacAuthenticationError(HacClientError):
    """Authentication failed or session expired."""


class HacClient:
    """HTTP client for SAP Commerce HAC API.
    
    This client handles:
    - Authentication via pluggable AuthHandler
    - Session management with CSRF tokens
    - Groovy script execution
    - FlexibleSearch queries
    - Impex operations
    """
    
    def __init__(
        self,
        base_url: str,
        auth_handler: AuthHandler,
        environment: str = "local",
        timeout: int = 30,
        ignore_ssl: bool = False,
        session_persistence: bool = True,
        quiet: bool = False
    ):
        """Initialize HAC client.
        
        Args:
            base_url: HAC base URL (e.g., https://localhost:9002)
            auth_handler: Authentication handler
            environment: Environment name for session caching
            timeout: HTTP timeout in seconds
            ignore_ssl: Ignore SSL certificate errors
            session_persistence: Enable session caching
            quiet: Suppress informational messages
        """
        self.base_url = base_url.rstrip('/')
        self.auth_handler = auth_handler
        self.environment = environment
        self.timeout = timeout
        self.ignore_ssl = ignore_ssl
        self.quiet = quiet
        
        # Session state
        self.session_info: Optional[SessionInfo] = None
        self.session_manager = SessionManager() if session_persistence else None
        
        # HTTP session
        self.http_session = requests.Session()
        if ignore_ssl:
            self.http_session.verify = False
        
        # Apply auth interceptor
        self._setup_auth_interceptor()
    
    def _setup_auth_interceptor(self) -> None:
        """Configure the HTTP session for the chosen auth handler.
        
        Currently a no-op — authentication is applied during login via
        form submission.  The hook exists so that custom ``AuthHandler``
        subclasses can override it to install request-level interceptors
        (e.g. injecting Bearer tokens on every request).
        """
    
    def _extract_csrf_token(self, html: str) -> Optional[str]:
        """Extract CSRF token from HTML page.
        
        Args:
            html: HTML content
            
        Returns:
            CSRF token if found, None otherwise
        """
        soup = BeautifulSoup(html, 'html.parser')
        csrf_input = soup.find('input', {'name': '_csrf'})
        if csrf_input and 'value' in csrf_input.attrs:
            return csrf_input['value']
        
        # Try meta tag
        csrf_meta = soup.find('meta', {'name': '_csrf'})
        if csrf_meta and 'content' in csrf_meta.attrs:
            return csrf_meta['content']
        
        return None
    
    def _extract_session_cookie(self, response: requests.Response) -> Optional[str]:
        """Extract JSESSIONID from Set-Cookie headers.
        
        Args:
            response: HTTP response
            
        Returns:
            Session ID if found, None otherwise
        """
        # First try response.cookies (works for some cases)
        session_id = response.cookies.get('JSESSIONID')
        if session_id:
            return session_id
        
        # Fall back to parsing Set-Cookie headers directly
        # requests.Response.headers is a case-insensitive dict that can have multiple values
        # for the same header. We need to get all Set-Cookie headers.
        if 'Set-Cookie' in response.headers:
            # response.raw.headers.getlist() gives us all Set-Cookie headers
            if hasattr(response.raw, 'headers'):
                set_cookie_headers = response.raw.headers.getlist('Set-Cookie')
            else:
                # Fallback: response.headers only returns the last value
                set_cookie_headers = [response.headers['Set-Cookie']]
            
            for cookie in set_cookie_headers:
                if 'JSESSIONID=' in cookie:
                    # Extract value: "JSESSIONID=abc123; Path=/; ..."
                    for part in cookie.split(';'):
                        if 'JSESSIONID=' in part:
                            return part.split('=', 1)[1].strip()
        
        return None
    
    def _extract_route_cookie(self, response: requests.Response) -> Optional[str]:
        """Extract ROUTE cookie for load balancer affinity.
        
        Args:
            response: HTTP response
            
        Returns:
            ROUTE cookie string (e.g., "ROUTE=value") if found, None otherwise
        """
        # First try response.cookies
        route = response.cookies.get('ROUTE')
        if route:
            return f"ROUTE={route}"
        
        # Fall back to parsing Set-Cookie headers directly
        if 'Set-Cookie' in response.headers:
            if hasattr(response.raw, 'headers'):
                set_cookie_headers = response.raw.headers.getlist('Set-Cookie')
            else:
                set_cookie_headers = [response.headers['Set-Cookie']]
            
            for cookie in set_cookie_headers:
                if 'ROUTE=' in cookie:
                    # Extract "ROUTE=value" part (before first semicolon)
                    for part in cookie.split(';'):
                        if 'ROUTE=' in part:
                            return part.strip()
        
        return None
    
    def _build_cookie_header(self) -> str:
        """Build cookie header for requests.
        
        Returns:
            Cookie header string
        """
        cookies = []
        
        if self.session_info and self.session_info.session_id:
            cookies.append(f"JSESSIONID={self.session_info.session_id}")
        
        if self.session_info and self.session_info.route_cookie:
            # route_cookie is already in "ROUTE=value" format
            cookies.append(self.session_info.route_cookie)
        
        return "; ".join(cookies)
    
    def _validate_session(self) -> bool:
        """Validate if current session is still working.
        
        Returns:
            True if session is valid, False otherwise
        """
        if not self.session_info or not self.session_info.session_id:
            return False
        
        try:
            response = self.http_session.get(
                urljoin(self.base_url, '/hac/'),
                timeout=5,
                headers={'Cookie': self._build_cookie_header()}
            )
            
            # Check if we're redirected to login page
            is_login_page = (
                'j_spring_security_check' in response.text or
                'name="j_username"' in response.text
            )
            
            return response.status_code == 200 and not is_login_page
            
        except requests.RequestException:
            return False
    
    def login(self) -> None:
        """Authenticate with HAC and establish session.
        
        Raises:
            HacAuthenticationError: If authentication fails
        """
        # Try to load cached session
        if self.session_manager:
            cached_metadata = self.session_manager.load_session(
                self.base_url,
                self.auth_handler.get_initial_credentials()['j_username'],
                self.environment
            )
            if cached_metadata:
                self.session_info = SessionInfo(
                    session_id=cached_metadata.session_id,
                    csrf_token=cached_metadata.csrf_token,
                    route_cookie=cached_metadata.route_cookie,
                    is_authenticated=cached_metadata.is_authenticated
                )
                if self._validate_session():
                    if not self.quiet:
                        print("Using cached session", file=sys.stderr)
                    return
                else:
                    # Cached session is invalid
                    if self.session_manager:
                        self.session_manager.remove_session(
                            self.base_url,
                            self.auth_handler.get_initial_credentials()['j_username'],
                            self.environment
                        )
        
        # Perform fresh login
        try:
            # Step 1: Get login page to extract CSRF token
            login_url = urljoin(self.base_url, '/hac/')
            response = self.http_session.get(login_url, timeout=self.timeout)
            response.raise_for_status()
            
            csrf_token = self._extract_csrf_token(response.text)
            # Extract from the session cookies (requests.Session stores them automatically)
            session_id = self.http_session.cookies.get('JSESSIONID')
            route = self.http_session.cookies.get('ROUTE')
            route_cookie = f"ROUTE={route}" if route else None
            
            if not csrf_token:
                raise HacAuthenticationError("Could not extract CSRF token from login page")
            
            # Step 2: Submit login form
            credentials = self.auth_handler.get_initial_credentials()
            login_data = {
                **credentials,
                '_csrf': csrf_token
            }
            
            auth_url = urljoin(self.base_url, '/hac/j_spring_security_check')
            cookies = {}
            if session_id:
                cookies['JSESSIONID'] = session_id
            if route_cookie:
                cookies['ROUTE'] = route_cookie
            
            response = self.http_session.post(
                auth_url,
                data=login_data,
                cookies=cookies,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # Check if login was successful
            if response.status_code != 200 or 'j_spring_security_check' in response.text:
                raise HacAuthenticationError("Authentication failed - invalid credentials")
            
            # Extract session info from auth response
            # The session cookies are automatically stored in http_session.cookies
            session_id = self.http_session.cookies.get('JSESSIONID') or session_id
            route = self.http_session.cookies.get('ROUTE')
            route_cookie = f"ROUTE={route}" if route else route_cookie
            
            # Extract updated CSRF token from authenticated page
            new_csrf_token = self._extract_csrf_token(response.text)
            csrf_token = new_csrf_token or csrf_token
            
            if not session_id or not csrf_token:
                missing = []
                if not session_id:
                    missing.append("session_id")
                if not csrf_token:
                    missing.append("csrf_token")
                raise HacAuthenticationError(
                    f"Could not establish session - missing: {', '.join(missing)}. "
                    f"Response status: {response.status_code}, URL: {response.url}"
                )
            
            # Store session info
            self.session_info = SessionInfo(
                session_id=session_id,
                csrf_token=csrf_token,
                route_cookie=route_cookie,
                is_authenticated=True
            )
            
            # Cache session with metadata
            if self.session_manager:
                self.session_manager.save_session(
                    self.base_url,
                    credentials['j_username'],
                    self.environment,
                    session_id,
                    csrf_token,
                    route_cookie
                )
            
            if not self.quiet:
                print("Authenticated successfully", file=sys.stderr)
                
        except requests.RequestException as e:
            raise HacAuthenticationError(f"Network error during authentication: {e}")
    
    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated, login if necessary."""
        if not self.session_info or not self.session_info.is_authenticated:
            self.login()
    
    def _clear_invalid_session(self) -> None:
        """Clear invalid/expired session from cache."""
        if self.session_manager and self.session_info:
            try:
                username = self.auth_handler.get_initial_credentials().get('j_username', 'unknown')
                self.session_manager.remove_session(
                    self.base_url,
                    username,
                    self.environment
                )
                self.session_info = None
            except (OSError, KeyError, TypeError):
                # If we can't clear it, just continue
                pass
    
    def _handle_request_error(self, error: requests.RequestException, operation: str) -> NoReturn:
        """Handle request errors and detect authentication failures.
        
        Args:
            error: The request exception
            operation: Description of the operation that failed
            
        Raises:
            HacAuthenticationError: If authentication failed/expired
            HacClientError: For other errors
        """
        if isinstance(error, requests.HTTPError) and error.response is not None:
            if error.response.status_code in (401, 403, 405):
                self._clear_invalid_session()
                raise HacAuthenticationError(
                    f"Session expired or invalid (HTTP {error.response.status_code}). "
                    f"Re-authenticate by calling login()."
                )
        raise HacClientError(f"{operation}: {error}")
    
    def _touch_session(self) -> None:
        """Update session last_used timestamp after successful operation."""
        if self.session_manager and self.session_info:
            try:
                username = self.auth_handler.get_initial_credentials().get('j_username', 'unknown')
                self.session_manager.touch_session(
                    self.base_url,
                    username,
                    self.environment
                )
            except (OSError, KeyError, TypeError):
                # Non-critical, ignore errors
                pass
    
    def execute_groovy(
        self,
        script: str,
        commit: bool = False
    ) -> GroovyScriptResult:
        """Execute Groovy script in HAC.
        
        Args:
            script: Groovy script code
            commit: Enable commit mode (default: rollback)
            
        Returns:
            GroovyScriptResult with execution results
            
        Raises:
            HacClientError: If execution fails
        """
        self._ensure_authenticated()
        
        try:
            url = urljoin(self.base_url, '/hac/console/scripting/execute')
            
            data = {
                'script': script,
                'scriptType': 'groovy',
                'commit': 'true' if commit else 'false'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRF-TOKEN': self.session_info.csrf_token,
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Ensure cookies are set in http_session for automatic inclusion
            if self.session_info.session_id not in str(self.http_session.cookies):
                parsed = urlparse(self.base_url)
                self.http_session.cookies.set('JSESSIONID', self.session_info.session_id, 
                                             domain=parsed.hostname, path='/')
                if self.session_info.route_cookie:
                    route_value = self.session_info.route_cookie.replace('ROUTE=', '')
                    self.http_session.cookies.set('ROUTE', route_value,
                                                 domain=parsed.hostname, path='/')
            
            response = self.http_session.post(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Update session timestamp on successful use
            self._touch_session()
            
            return GroovyScriptResult(
                output_text=result.get('outputText', ''),
                execution_result=result.get('executionResult', ''),
                stacktrace_text=result.get('stacktraceText'),
                commit_mode=commit,
                execution_time_ms=result.get('executionTime')
            )
            
        except requests.RequestException as e:
            self._handle_request_error(e, "Failed to execute Groovy script")
        except (KeyError, ValueError) as e:
            raise HacClientError(f"Invalid response from HAC: {e}")
    
    def execute_flexiblesearch(
        self,
        query: str,
        max_count: int = 200,
        locale: str = "en"
    ) -> FlexibleSearchResult:
        """Execute FlexibleSearch query in HAC.
        
        Args:
            query: FlexibleSearch query
            max_count: Maximum number of results
            locale: Locale for the query
            
        Returns:
            FlexibleSearchResult with query results
            
        Raises:
            HacClientError: If query execution fails
        """
        self._ensure_authenticated()
        
        try:
            url = urljoin(self.base_url, '/hac/console/flexsearch/execute')
            
            data = {
                'flexibleSearchQuery': query,
                'maxCount': str(max_count),
                'locale': locale,
                'commit': 'false'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRF-TOKEN': self.session_info.csrf_token,
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.http_session.post(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Update session timestamp on successful use
            self._touch_session()
            
            return FlexibleSearchResult(
                headers=result.get('headers', []),
                rows=result.get('resultList', []),
                result_count=result.get('resultCount', 0),
                execution_time_ms=result.get('executionTime'),
                exception=result.get('exception')
            )
            
        except requests.RequestException as e:
            self._handle_request_error(e, "Failed to execute FlexibleSearch")
        except (KeyError, ValueError) as e:
            raise HacClientError(f"Invalid response from HAC: {e}")
    
    def import_impex(
        self,
        impex_content: str,
        validation_mode: str = "import_strict"
    ) -> ImpexResult:
        """Import Impex data in HAC.
        
        Args:
            impex_content: Impex content to import
            validation_mode: Validation mode (import_strict, import_relaxed, strict, relaxed)
            
        Returns:
            ImpexResult with import results
            
        Raises:
            HacClientError: If import fails
        """
        self._ensure_authenticated()
        
        try:
            url = urljoin(self.base_url, '/hac/console/impex/import')
            
            data = {
                'scriptContent': impex_content,
                'validationEnum': validation_mode.upper(),
                'encoding': 'UTF-8',
                'maxThreads': '1',
                '_legacyMode': 'on',
                '_enableCodeExecution': 'on'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-CSRF-TOKEN': self.session_info.csrf_token
            }
            
            response = self.http_session.post(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse HTML response (Impex doesn't return JSON)
            soup = BeautifulSoup(response.text, 'html.parser')
            result_div = soup.find('div', {'class': 'impex-result'})
            
            if result_div:
                output = result_div.get_text(strip=True)
                success = 'error' not in output.lower()
            else:
                output = response.text
                success = response.status_code == 200
            
            # Update session timestamp on successful use
            self._touch_session()
            
            return ImpexResult(
                success=success,
                output=output,
                error=None if success else output
            )
            
        except requests.RequestException as e:
            self._handle_request_error(e, "Failed to import Impex")
    
    def get_update_data(self) -> UpdateData:
        """Fetch available update data (extensions, patches, parameters).
        
        Returns:
            UpdateData with available extensions and their parameters
            
        Raises:
            HacClientError: If fetching fails
        """
        self._ensure_authenticated()
        
        try:
            # Must visit the update page first - server requires this to populate patch data
            update_page_url = urljoin(self.base_url, '/hac/platform/update')
            self.http_session.get(
                update_page_url,
                headers={'X-CSRF-TOKEN': self.session_info.csrf_token},
                timeout=self.timeout
            )
            
            url = urljoin(self.base_url, '/hac/platform/init/data/')
            
            headers = {
                'Accept': 'application/json',
                'X-CSRF-TOKEN': self.session_info.csrf_token,
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': update_page_url
            }
            
            response = self.http_session.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse project datas
            project_datas = []
            for pd in data.get('projectDatas', []):
                params = []
                for p in pd.get('parameter', []):
                    params.append(UpdateParameter(
                        name=p.get('name', ''),
                        label=p.get('label', p.get('name', '')),
                        values=p.get('values', {}),
                        legacy=p.get('legacy', False),
                        multi_select=p.get('multiSelect', False),
                        default=p.get('default')
                    ))
                
                project_datas.append(ProjectData(
                    name=pd.get('name', ''),
                    description=pd.get('description'),
                    parameters=params
                ))
            
            # Update session timestamp on successful use
            self._touch_session()
            
            return UpdateData(
                is_initializing=data.get('isInitializing', False),
                project_datas=project_datas
            )
            
        except requests.RequestException as e:
            self._handle_request_error(e, "Failed to fetch update data")
        except (KeyError, ValueError) as e:
            raise HacClientError(f"Invalid response from HAC: {e}")
    
    def execute_update(
        self,
        patches: Optional[dict[str, str]] = None,
        drop_tables: bool = False,
        clear_hmc: bool = False,
        create_essential_data: bool = False,
        create_project_data: bool = False,
        localize_types: bool = False,
        all_parameters: Optional[dict[str, Any]] = None,
        include_pending_patches: bool = True
    ) -> UpdateResult:
        """Execute system update.
        
        Args:
            patches: Dictionary of patch names to values (e.g., {'Patch_MVP': 'yes'})
            drop_tables: Drop all tables (DANGEROUS)
            clear_hmc: Clear HMC configuration
            create_essential_data: Create essential data
            create_project_data: Create project data
            localize_types: Localize types
            all_parameters: Full parameters dict (overrides individual patch settings)
            include_pending_patches: Include required system patches (validation, etc.)
            
        Returns:
            UpdateResult with success status and log
            
        Raises:
            HacClientError: If update execution fails
        """
        self._ensure_authenticated()
        
        try:
            url = urljoin(self.base_url, '/hac/platform/init/execute')
            
            # Build parameters
            if all_parameters is None:
                all_parameters = {}
            
            # Add patch parameters
            if patches:
                for patch_name, value in patches.items():
                    # Patches are typically prefixed with extension name
                    all_parameters[patch_name] = [value]
            
            # Get pending system patches (validation, etc.)
            pending_patches_payload: dict[str, list[str]] = {}
            if include_pending_patches:
                try:
                    pending = self.get_pending_patches()
                    for category, patch_list in pending.items():
                        # Include all required patches, and optionally others
                        hashes = [p['hash'] for p in patch_list if p.get('required', False)]
                        if hashes:
                            pending_patches_payload[category] = hashes
                except (requests.RequestException, KeyError, ValueError):
                    # Don't fail if we can't get pending patches
                    pass
            
            # Build the request payload
            payload = {
                'dropTables': drop_tables,
                'clearHMC': clear_hmc,
                'createEssentialData': create_essential_data,
                'createProjectData': create_project_data,
                'localizeTypes': localize_types,
                'initMethod': None,
                'allParameters': all_parameters,
                'patches': pending_patches_payload,
                'parametersAsStringMap': {
                    'initmethod': ['update'],
                    **{k: v if isinstance(v, list) else [v] for k, v in all_parameters.items()}
                }
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json; charset=UTF-8',
                'X-CSRF-TOKEN': self.session_info.csrf_token,
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.http_session.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Update session timestamp on successful use
            self._touch_session()
            
            return UpdateResult(
                success=result.get('success', False),
                log_html=result.get('log', '')
            )
            
        except requests.RequestException as e:
            self._handle_request_error(e, "Failed to execute update")
        except (KeyError, ValueError) as e:
            raise HacClientError(f"Invalid response from HAC: {e}")
    
    def get_pending_patches(self) -> dict[str, list[dict[str, Any]]]:
        """Fetch pending system patches that need to be included in updates.
        
        Returns:
            Dictionary mapping patch category to list of patches with hashes
            
        Raises:
            HacClientError: If fetching fails
        """
        self._ensure_authenticated()
        
        try:
            url = urljoin(self.base_url, '/hac/platform/init/pendingPatches')
            
            headers = {
                'Accept': 'application/json',
                'X-CSRF-TOKEN': self.session_info.csrf_token,
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.http_session.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            self._handle_request_error(e, "Failed to fetch pending patches")
        except (KeyError, ValueError) as e:
            raise HacClientError(f"Invalid response from HAC: {e}")
    
    def get_update_log(self) -> UpdateLog:
        """Fetch the current update/initialization log.
        
        Returns:
            UpdateLog with current log content
            
        Raises:
            HacClientError: If fetching log fails
        """
        self._ensure_authenticated()
        
        try:
            url = urljoin(self.base_url, f'/hac/initlog/log?_={int(time.time() * 1000)}')
            
            headers = {
                'Accept': 'application/json',
                'X-CSRF-TOKEN': self.session_info.csrf_token,
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.http_session.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Update session timestamp on successful use
            self._touch_session()
            
            return UpdateLog(
                log_html=data.get('log', '')
            )
            
        except requests.RequestException as e:
            self._handle_request_error(e, "Failed to fetch update log")
        except (KeyError, ValueError) as e:
            raise HacClientError(f"Invalid response from HAC: {e}")

