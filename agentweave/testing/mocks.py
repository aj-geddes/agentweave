"""
Mock providers for testing AgentWeave SDK.

This module provides mock implementations of Identity, Authorization, and
Transport providers for testing purposes.
"""

import asyncio
import ssl
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


@dataclass
class MockSVID:
    """Mock SPIFFE Verifiable Identity Document."""

    spiffe_id: str
    cert_chain: bytes
    private_key: bytes
    expiry: datetime

    def is_expired(self) -> bool:
        """Check if SVID is expired."""
        return datetime.utcnow() >= self.expiry


@dataclass
class MockTrustBundle:
    """Mock trust bundle for peer verification."""

    trust_domain: str
    ca_certs: List[bytes]

    def verify_cert(self, cert: bytes) -> bool:
        """Verify certificate against trust bundle."""
        # Simplified verification for testing
        return True


@dataclass
class AuthzCheck:
    """Record of an authorization check."""

    caller_id: str
    callee_id: Optional[str]
    action: str
    context: Dict[str, Any]
    timestamp: datetime
    allowed: bool
    reason: str


class MockIdentityProvider:
    """
    Mock SPIFFE identity provider for testing.

    Features:
    - Returns configurable SPIFFE ID
    - Generates self-signed certificates
    - Simulates certificate rotation
    - No real SPIRE connection required

    Example:
        >>> provider = MockIdentityProvider(
        ...     spiffe_id="spiffe://test.local/agent/test-agent",
        ...     rotation_interval=60  # Rotate every 60 seconds
        ... )
        >>> svid = await provider.get_svid()
        >>> assert svid.spiffe_id == "spiffe://test.local/agent/test-agent"
    """

    def __init__(
        self,
        spiffe_id: str = "spiffe://test.local/agent/mock",
        trust_domain: Optional[str] = None,
        rotation_interval: int = 3600,  # 1 hour default
        auto_rotate: bool = False,
    ):
        """
        Initialize mock identity provider.

        Args:
            spiffe_id: SPIFFE ID to return
            trust_domain: Override trust domain (extracted from spiffe_id if not provided)
            rotation_interval: Seconds between rotations
            auto_rotate: Whether to automatically rotate SVIDs
        """
        self.spiffe_id = spiffe_id
        self.trust_domain = trust_domain or self._extract_trust_domain(spiffe_id)
        self.rotation_interval = rotation_interval
        self.auto_rotate = auto_rotate

        self._current_svid: Optional[MockSVID] = None
        self._trust_bundles: Dict[str, MockTrustBundle] = {}
        self._rotation_task: Optional[asyncio.Task] = None
        self._update_listeners: List[asyncio.Queue] = []

        # Generate initial SVID
        self._generate_svid()

    def _extract_trust_domain(self, spiffe_id: str) -> str:
        """Extract trust domain from SPIFFE ID."""
        # spiffe://trust-domain/path -> trust-domain
        if not spiffe_id.startswith("spiffe://"):
            raise ValueError(f"Invalid SPIFFE ID: {spiffe_id}")
        parts = spiffe_id[9:].split("/")
        return parts[0] if parts else "unknown"

    def _generate_svid(self) -> MockSVID:
        """Generate a self-signed certificate for testing."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Create self-signed certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "HVS Test"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.spiffe_id),
        ])

        expiry = datetime.utcnow() + timedelta(seconds=self.rotation_interval)

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            expiry
        ).add_extension(
            # Add SPIFFE ID as SAN URI
            x509.SubjectAlternativeName([
                x509.UniformResourceIdentifier(self.spiffe_id)
            ]),
            critical=True,
        ).sign(private_key, hashes.SHA256(), default_backend())

        # Convert to PEM
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )

        self._current_svid = MockSVID(
            spiffe_id=self.spiffe_id,
            cert_chain=cert_pem,
            private_key=key_pem,
            expiry=expiry
        )

        return self._current_svid

    async def get_svid(self) -> MockSVID:
        """Get current SVID (X.509)."""
        if self._current_svid is None or self._current_svid.is_expired():
            self._generate_svid()
        return self._current_svid

    async def get_trust_bundle(self, trust_domain: str) -> MockTrustBundle:
        """Get trust bundle for verifying peers."""
        if trust_domain not in self._trust_bundles:
            # Create mock trust bundle
            svid = await self.get_svid()
            self._trust_bundles[trust_domain] = MockTrustBundle(
                trust_domain=trust_domain,
                ca_certs=[svid.cert_chain]
            )
        return self._trust_bundles[trust_domain]

    def get_spiffe_id(self) -> str:
        """Get this workload's SPIFFE ID."""
        return self.spiffe_id

    async def watch_updates(self) -> AsyncIterator[MockSVID]:
        """Stream SVID rotation events."""
        queue: asyncio.Queue = asyncio.Queue()
        self._update_listeners.append(queue)

        try:
            while True:
                svid = await queue.get()
                yield svid
        finally:
            self._update_listeners.remove(queue)

    async def rotate_svid(self) -> MockSVID:
        """Manually trigger SVID rotation."""
        svid = self._generate_svid()

        # Notify all listeners
        for queue in self._update_listeners:
            await queue.put(svid)

        return svid

    async def start_auto_rotation(self):
        """Start automatic SVID rotation."""
        if self._rotation_task is not None:
            return

        async def _rotation_loop():
            while self.auto_rotate:
                await asyncio.sleep(self.rotation_interval)
                await self.rotate_svid()

        self._rotation_task = asyncio.create_task(_rotation_loop())

    async def stop_auto_rotation(self):
        """Stop automatic SVID rotation."""
        self.auto_rotate = False
        if self._rotation_task:
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass
            self._rotation_task = None


class MockAuthorizationProvider:
    """
    Mock OPA authorization provider for testing.

    Features:
    - Configurable allow/deny responses
    - Record all authorization checks
    - Simulate OPA responses
    - Support for policy-based rules

    Example:
        >>> authz = MockAuthorizationProvider(default_allow=True)
        >>> decision = await authz.check_inbound(
        ...     caller_id="spiffe://test.local/agent/caller",
        ...     action="search"
        ... )
        >>> assert decision.allowed == True
        >>> assert len(authz.get_checks()) == 1
    """

    def __init__(
        self,
        default_allow: bool = False,
        policy_rules: Optional[Dict[str, bool]] = None,
    ):
        """
        Initialize mock authorization provider.

        Args:
            default_allow: Default decision when no rule matches
            policy_rules: Dict of "caller:callee:action" -> bool decisions
        """
        self.default_allow = default_allow
        self.policy_rules = policy_rules or {}
        self._checks: List[AuthzCheck] = []

    def _make_key(self, caller_id: str, callee_id: Optional[str], action: str) -> str:
        """Create policy rule key."""
        if callee_id:
            return f"{caller_id}:{callee_id}:{action}"
        return f"{caller_id}:{action}"

    async def check_outbound(
        self,
        caller_id: str,
        callee_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "AuthzDecision":
        """Check if caller can invoke callee."""
        key = self._make_key(caller_id, callee_id, action)
        allowed = self.policy_rules.get(key, self.default_allow)

        reason = "allowed by policy" if allowed else "denied by policy"

        check = AuthzCheck(
            caller_id=caller_id,
            callee_id=callee_id,
            action=action,
            context=context or {},
            timestamp=datetime.utcnow(),
            allowed=allowed,
            reason=reason,
        )
        self._checks.append(check)

        return AuthzDecision(
            allowed=allowed,
            reason=reason,
            audit_id=str(uuid.uuid4()),
        )

    async def check_inbound(
        self,
        caller_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "AuthzDecision":
        """Check if incoming request is allowed."""
        key = self._make_key(caller_id, None, action)
        allowed = self.policy_rules.get(key, self.default_allow)

        reason = "allowed by policy" if allowed else "denied by policy"

        check = AuthzCheck(
            caller_id=caller_id,
            callee_id=None,
            action=action,
            context=context or {},
            timestamp=datetime.utcnow(),
            allowed=allowed,
            reason=reason,
        )
        self._checks.append(check)

        return AuthzDecision(
            allowed=allowed,
            reason=reason,
            audit_id=str(uuid.uuid4()),
        )

    def get_checks(self) -> List[AuthzCheck]:
        """Get all recorded authorization checks."""
        return self._checks.copy()

    def clear_checks(self):
        """Clear all recorded checks."""
        self._checks.clear()

    def add_rule(self, caller_id: str, callee_id: Optional[str], action: str, allowed: bool):
        """Add a policy rule."""
        key = self._make_key(caller_id, callee_id, action)
        self.policy_rules[key] = allowed

    def remove_rule(self, caller_id: str, callee_id: Optional[str], action: str):
        """Remove a policy rule."""
        key = self._make_key(caller_id, callee_id, action)
        self.policy_rules.pop(key, None)


@dataclass
class AuthzDecision:
    """Authorization decision."""

    allowed: bool
    reason: str
    audit_id: str


@dataclass
class MockRequest:
    """Mock HTTP request."""

    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[bytes]
    timestamp: datetime


@dataclass
class MockResponse:
    """Mock HTTP response."""

    status_code: int
    headers: Dict[str, str]
    body: bytes
    timestamp: datetime


class MockTransport:
    """
    Mock transport layer for testing.

    Features:
    - Record all requests
    - Return configurable responses
    - Simulate network failures
    - Verify mTLS setup

    Example:
        >>> transport = MockTransport()
        >>> transport.add_response(
        ...     url="https://agent.example.com/task",
        ...     status_code=200,
        ...     body=b'{"status": "ok"}'
        ... )
        >>> response = await transport.post(
        ...     "https://agent.example.com/task",
        ...     data=b'{"task": "test"}'
        ... )
        >>> assert response.status_code == 200
    """

    def __init__(self):
        """Initialize mock transport."""
        self._requests: List[MockRequest] = []
        self._responses: Dict[str, List[MockResponse]] = {}
        self._failure_mode: Optional[str] = None
        self._ssl_context: Optional[ssl.SSLContext] = None

    def add_response(
        self,
        url: str,
        status_code: int = 200,
        body: bytes = b"",
        headers: Optional[Dict[str, str]] = None,
    ):
        """Add a canned response for a URL."""
        if url not in self._responses:
            self._responses[url] = []

        self._responses[url].append(MockResponse(
            status_code=status_code,
            headers=headers or {},
            body=body,
            timestamp=datetime.utcnow(),
        ))

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        timeout: float = 30.0,
    ) -> MockResponse:
        """Make a request."""
        # Record request
        request = MockRequest(
            method=method,
            url=url,
            headers=headers or {},
            body=data,
            timestamp=datetime.utcnow(),
        )
        self._requests.append(request)

        # Simulate failures
        if self._failure_mode == "timeout":
            await asyncio.sleep(timeout + 1)
            raise asyncio.TimeoutError("Request timeout")
        elif self._failure_mode == "connection":
            raise ConnectionError("Connection failed")
        elif self._failure_mode == "ssl":
            raise ssl.SSLError("SSL verification failed")

        # Return canned response
        if url in self._responses and self._responses[url]:
            return self._responses[url].pop(0)

        # Default 404 response
        return MockResponse(
            status_code=404,
            headers={},
            body=b"Not Found",
            timestamp=datetime.utcnow(),
        )

    async def get(self, url: str, **kwargs) -> MockResponse:
        """Make GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> MockResponse:
        """Make POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> MockResponse:
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> MockResponse:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    def get_requests(self) -> List[MockRequest]:
        """Get all recorded requests."""
        return self._requests.copy()

    def clear_requests(self):
        """Clear all recorded requests."""
        self._requests.clear()

    def set_failure_mode(self, mode: Optional[str] = None):
        """
        Set failure simulation mode.

        Args:
            mode: One of 'timeout', 'connection', 'ssl', or None
        """
        self._failure_mode = mode

    def set_ssl_context(self, ssl_context: ssl.SSLContext):
        """Set SSL context (for verification in tests)."""
        self._ssl_context = ssl_context

    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context."""
        return self._ssl_context
