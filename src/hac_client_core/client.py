"""HAC HTTP client implementation."""

import requests
from bs4 import BeautifulSoup
from typing import Optional
from urllib.parse import urljoin
import warnings

from hac_client_core.auth import AuthHandler
from hac_client_core.models import (
    GroovyScriptResult,
    FlexibleSearchResult,
    ImpexResult,
    SessionInfo
)
from hac_client_core.session import SessionManager


# Suppress SSL warnings when ignore_ssl is enabled
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class HacClientError(Exception):
    """Base exception for HAC client errors."""
    pass


class HacAuthenticationError(HacClientError):
    """Authentication failed."""
    pass


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
        """Setup authentication interceptor for requests."""
        # Store original request method
        original_request = self.http_session.request
        
        def intercepted_request(*args, **kwargs):
            """Intercept request to apply authentication."""
            # Prepare the request
            req = requests.Request(*args, **kwargs)
            prepared = self.http_session.prepare_request(req)
            
            # Apply authentication
            prepared = self.auth_handler.apply_auth(prepared)
            
            # Send the request
            return original_request(*args, **kwargs)
        
        # Don't actually override - requests handles auth differently
        # The auth is applied during login via form submission
    
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
        """Extract JSESSIONID from response cookies.
        
        Args:
            response: HTTP response
            
        Returns:
            Session ID if found, None otherwise
        """
        return response.cookies.get('JSESSIONID')
    
    def _extract_route_cookie(self, response: requests.Response) -> Optional[str]:
        """Extract ROUTE cookie for load balancer affinity.
        
        Args:
            response: HTTP response
            
        Returns:
            ROUTE cookie if found, None otherwise
        """
        return response.cookies.get('ROUTE')
    
    def _build_cookie_header(self) -> str:
        """Build cookie header for requests.
        
        Returns:
            Cookie header string
        """
        cookies = []
        
        if self.session_info and self.session_info.session_id:
            cookies.append(f"JSESSIONID={self.session_info.session_id}")
        
        if self.session_info and self.session_info.route_cookie:
            cookies.append(f"ROUTE={self.session_info.route_cookie}")
        
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
                        print("Using cached session", file=__import__('sys').stderr)
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
            session_id = self._extract_session_cookie(response)
            route_cookie = self._extract_route_cookie(response)
            
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
            
            # Extract session info
            session_id = self._extract_session_cookie(response) or session_id
            csrf_token = self._extract_csrf_token(response.text) or csrf_token
            route_cookie = self._extract_route_cookie(response) or route_cookie
            
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
                print("Authenticated successfully", file=__import__('sys').stderr)
                
        except requests.RequestException as e:
            raise HacAuthenticationError(f"Network error during authentication: {e}")
    
    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated, login if necessary."""
        if not self.session_info or not self.session_info.is_authenticated:
            self.login()
    
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
                'commit': 'true' if commit else 'false',
                '_csrf': self.session_info.csrf_token
            }
            
            headers = {
                'Cookie': self._build_cookie_header(),
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
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
            
            return GroovyScriptResult(
                output_text=result.get('outputText', ''),
                execution_result=result.get('executionResult', ''),
                stacktrace_text=result.get('stacktraceText'),
                commit_mode=commit,
                execution_time_ms=result.get('executionTime')
            )
            
        except requests.RequestException as e:
            raise HacClientError(f"Failed to execute Groovy script: {e}")
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
                'commit': 'false',
                '_csrf': self.session_info.csrf_token
            }
            
            headers = {
                'Cookie': self._build_cookie_header(),
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
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
            
            return FlexibleSearchResult(
                headers=result.get('headers', []),
                rows=result.get('resultList', []),
                result_count=result.get('resultCount', 0),
                execution_time_ms=result.get('executionTime'),
                exception=result.get('exception')
            )
            
        except requests.RequestException as e:
            raise HacClientError(f"Failed to execute FlexibleSearch: {e}")
        except (KeyError, ValueError) as e:
            raise HacClientError(f"Invalid response from HAC: {e}")
    
    def import_impex(
        self,
        impex_content: str,
        validation_mode: str = "strict"
    ) -> ImpexResult:
        """Import Impex data in HAC.
        
        Args:
            impex_content: Impex content to import
            validation_mode: Validation mode (strict, relaxed, import_relaxed)
            
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
                'maxThreads': '1',
                '_legacyMode': 'on',
                '_enableCodeExecution': 'on',
                '_csrf': self.session_info.csrf_token
            }
            
            headers = {
                'Cookie': self._build_cookie_header(),
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
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
            
            return ImpexResult(
                success=success,
                output=output,
                error=None if success else output
            )
            
        except requests.RequestException as e:
            raise HacClientError(f"Failed to import Impex: {e}")

