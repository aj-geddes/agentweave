import ssl
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
import spiffe
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

from agentweave.identity.base import TrustDomainError
from agentweave.identity.base import ConnectionError as IdentityConnectionError
from agentweave.identity.spiffe import SPIFFEIdentityProvider


def _build_real_svid_and_bundle(spiffe_id_str: str, trust_domain_str: str):
    """Build a real X509Svid and X509Bundle using the real spiffe library and cryptography."""
    # Generate RSA-2048 private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Build self-signed certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "test-cert"),
    ])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(spiffe_id_str)]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Build spiffe objects
    spiffe_id = spiffe.SpiffeId(spiffe_id_str)
    svid = spiffe.X509Svid(spiffe_id, [cert], private_key)

    trust_domain = spiffe.TrustDomain(trust_domain_str)
    bundle = spiffe.X509Bundle(trust_domain, {cert})

    return svid, bundle


class TestSPIFFEIdentityProviderRuntime:
    """Tests for SPIFFEIdentityProvider using real spiffe library types."""

    def test_module_imports_and_provider_instantiates(self):
        """Guard against ImportError regression for SpiffeError vs PySpiffeError."""
        # This test ensures that importing SPIFFEIdentityProvider does not fail
        # due to trying to import non-existent 'spiffe.errors.SpiFFEError'
        provider = SPIFFEIdentityProvider(endpoint=None, tls_min_version=ssl.TLSVersion.TLSv1_3)
        assert provider._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_wraps_real_pyspiffe_argument_error_as_identity_connection_error(self):
        """Guard against unhandled spiffe.errors.ArgumentError during initialization."""
        provider = SPIFFEIdentityProvider(endpoint="unix:///nonexistent/path/for/spire-agent.sock")
        with pytest.raises(IdentityConnectionError):
            await provider.initialize()

    @pytest.mark.asyncio
    async def test_get_trust_bundle_handles_real_x509_bundle_set(self, monkeypatch):
        """Guard against calling .update()/.keys() on X509BundleSet (not supported)."""
        svid, bundle = _build_real_svid_and_bundle("spiffe://example.org/workload", "example.org")
        mock_client = MagicMock()
        mock_client.fetch_x509_svid.return_value = svid
        mock_client.fetch_x509_bundles.return_value = spiffe.X509BundleSet.of([bundle])
        mock_client.close = lambda: None

        monkeypatch.setattr("agentweave.identity.spiffe.WorkloadApiClient", lambda *args, **kwargs: mock_client)

        provider = SPIFFEIdentityProvider(endpoint=None, tls_min_version=ssl.TLSVersion.TLSv1_3)
        await provider.initialize()

        result_bundle = await provider.get_trust_bundle("example.org")
        assert str(result_bundle.trust_domain) == "example.org"
        assert result_bundle is bundle

    @pytest.mark.asyncio
    async def test_get_trust_bundle_raises_trust_domain_error_for_unknown_domain(self, monkeypatch):
        """Guard against missing trust domain handling."""
        svid, bundle = _build_real_svid_and_bundle("spiffe://example.org/workload", "example.org")
        mock_client = MagicMock()
        mock_client.fetch_x509_svid.return_value = svid
        mock_client.fetch_x509_bundles.return_value = spiffe.X509BundleSet.of([bundle])
        mock_client.close = lambda: None

        monkeypatch.setattr("agentweave.identity.spiffe.WorkloadApiClient", lambda *args, **kwargs: mock_client)

        provider = SPIFFEIdentityProvider(endpoint=None, tls_min_version=ssl.TLSVersion.TLSv1_3)
        await provider.initialize()

        with pytest.raises(TrustDomainError):
            await provider.get_trust_bundle("unknown-domain.org")

    @pytest.mark.asyncio
    async def test_create_tls_context_builds_real_ssl_context_from_real_svid_and_bundle(self, monkeypatch):
        """Guard against accessing non-existent .*_bytes attributes on X509Svid/X509Bundle."""
        svid, bundle = _build_real_svid_and_bundle("spiffe://example.org/workload", "example.org")
        mock_client = MagicMock()
        mock_client.fetch_x509_svid.return_value = svid
        mock_client.fetch_x509_bundles.return_value = spiffe.X509BundleSet.of([bundle])
        mock_client.close = lambda: None

        monkeypatch.setattr("agentweave.identity.spiffe.WorkloadApiClient", lambda *args, **kwargs: mock_client)

        provider = SPIFFEIdentityProvider(endpoint=None, tls_min_version=ssl.TLSVersion.TLSv1_3)
        await provider.initialize()

        # Test client context
        ctx = await provider.create_tls_context(server=False)
        assert isinstance(ctx, ssl.SSLContext)

        # Test server context
        ctx_server = await provider.create_tls_context(server=True)
        assert isinstance(ctx_server, ssl.SSLContext)

    def test_register_rotation_callback_stores_callback(self):
        """Guard against callback registration logic regression."""
        provider = SPIFFEIdentityProvider(endpoint=None, tls_min_version=ssl.TLSVersion.TLSv1_3)

        async def _cb(svid):
            pass

        provider.register_rotation_callback(_cb)
        assert _cb in provider._rotation_callbacks


def test_testing_mocks_importable_without_docker_extra():
    """Verify agentweave.testing.mocks can be imported without docker package."""
    script = """
import sys
sys.modules['docker'] = None  # sabotage: any 'import docker' will raise ImportError
from agentweave.testing.mocks import MockIdentityProvider, MockAuthorizationProvider
print('OK')
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, f"Expected success, got stderr: {result.stderr}"
    assert "OK" in result.stdout

    # Also verify lazy import still works when docker IS available
    script2 = """
from agentweave.testing import TestCluster
print('OK')
"""
    result2 = subprocess.run([sys.executable, "-c", script2], capture_output=True, text=True, timeout=30)
    assert result2.returncode == 0, f"Expected success, got stderr: {result2.stderr}"
    assert "OK" in result2.stdout
