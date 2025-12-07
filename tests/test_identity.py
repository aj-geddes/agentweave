"""
Tests for AgentWeave SDK identity providers.

Tests SPIFFE identity provider, SVID management, and certificate rotation.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from agentweave.testing import MockIdentityProvider


class TestMockIdentityProvider:
    """Test MockIdentityProvider functionality."""

    @pytest.mark.asyncio
    async def test_get_svid(self, mock_identity_provider):
        """Test getting SVID from mock provider."""
        svid = await mock_identity_provider.get_svid()

        assert svid is not None
        assert svid.spiffe_id == "spiffe://test.local/agent/test"
        assert svid.cert_chain is not None
        assert svid.private_key is not None
        assert not svid.is_expired()

    @pytest.mark.asyncio
    async def test_get_spiffe_id(self, mock_identity_provider):
        """Test getting SPIFFE ID."""
        spiffe_id = mock_identity_provider.get_spiffe_id()
        assert spiffe_id == "spiffe://test.local/agent/test"

    @pytest.mark.asyncio
    async def test_get_trust_bundle(self, mock_identity_provider):
        """Test getting trust bundle for a domain."""
        bundle = await mock_identity_provider.get_trust_bundle("test.local")

        assert bundle is not None
        assert bundle.trust_domain == "test.local"
        assert len(bundle.ca_certs) > 0

    @pytest.mark.asyncio
    async def test_svid_caching(self, mock_identity_provider):
        """Test that SVIDs are cached and reused."""
        svid1 = await mock_identity_provider.get_svid()
        svid2 = await mock_identity_provider.get_svid()

        # Should be the same SVID (cached)
        assert svid1.cert_chain == svid2.cert_chain
        assert svid1.private_key == svid2.private_key

    @pytest.mark.asyncio
    async def test_svid_expiry_check(self):
        """Test SVID expiry detection."""
        # Create provider with short expiry
        provider = MockIdentityProvider(
            spiffe_id="spiffe://test.local/agent/short-lived",
            rotation_interval=1,  # 1 second
        )

        svid1 = await provider.get_svid()
        assert not svid1.is_expired()

        # Wait for expiry
        await asyncio.sleep(2)

        # SVID should be expired
        assert svid1.is_expired()

        # Getting new SVID should return a fresh one
        svid2 = await provider.get_svid()
        assert not svid2.is_expired()
        assert svid2.cert_chain != svid1.cert_chain

    @pytest.mark.asyncio
    async def test_manual_svid_rotation(self, mock_identity_provider):
        """Test manual SVID rotation."""
        svid1 = await mock_identity_provider.get_svid()

        # Manually rotate
        svid2 = await mock_identity_provider.rotate_svid()

        # Should be different SVIDs
        assert svid2.cert_chain != svid1.cert_chain
        assert svid2.private_key != svid1.private_key

        # New SVID should be cached
        svid3 = await mock_identity_provider.get_svid()
        assert svid3.cert_chain == svid2.cert_chain

    @pytest.mark.asyncio
    async def test_svid_rotation_notifications(self, mock_identity_provider):
        """Test SVID rotation notifications via watch_updates."""
        updates = []

        async def collect_updates():
            async for svid in mock_identity_provider.watch_updates():
                updates.append(svid)
                if len(updates) >= 2:
                    break

        # Start watching in background
        watch_task = asyncio.create_task(collect_updates())

        # Trigger rotations
        await asyncio.sleep(0.1)
        await mock_identity_provider.rotate_svid()
        await asyncio.sleep(0.1)
        await mock_identity_provider.rotate_svid()

        # Wait for updates to be collected
        await asyncio.wait_for(watch_task, timeout=1.0)

        # Should have received 2 updates
        assert len(updates) == 2
        assert updates[0].cert_chain != updates[1].cert_chain

    @pytest.mark.asyncio
    async def test_trust_bundle_caching(self, mock_identity_provider):
        """Test that trust bundles are cached."""
        bundle1 = await mock_identity_provider.get_trust_bundle("test.local")
        bundle2 = await mock_identity_provider.get_trust_bundle("test.local")

        # Should be the same bundle (cached)
        assert bundle1.ca_certs == bundle2.ca_certs

    @pytest.mark.asyncio
    async def test_multiple_trust_domains(self, mock_identity_provider):
        """Test getting trust bundles for different domains."""
        bundle1 = await mock_identity_provider.get_trust_bundle("test.local")
        bundle2 = await mock_identity_provider.get_trust_bundle("partner.example.com")

        assert bundle1.trust_domain == "test.local"
        assert bundle2.trust_domain == "partner.example.com"


class TestSVIDFormat:
    """Test SVID format and structure."""

    @pytest.mark.asyncio
    async def test_svid_contains_spiffe_id(self, mock_identity_provider):
        """Test that SVID certificate contains SPIFFE ID as SAN."""
        svid = await mock_identity_provider.get_svid()

        # Parse certificate
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        cert = x509.load_pem_x509_certificate(svid.cert_chain, default_backend())

        # Check SAN extension for SPIFFE ID
        san_ext = cert.extensions.get_extension_for_oid(
            x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        )

        uris = [name.value for name in san_ext.value if isinstance(name, x509.UniformResourceIdentifier)]
        assert "spiffe://test.local/agent/test" in uris

    @pytest.mark.asyncio
    async def test_svid_certificate_validity(self, mock_identity_provider):
        """Test that SVID certificate has valid not_before and not_after."""
        svid = await mock_identity_provider.get_svid()

        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        cert = x509.load_pem_x509_certificate(svid.cert_chain, default_backend())

        # Check validity period
        now = datetime.utcnow()
        assert cert.not_valid_before <= now
        assert cert.not_valid_after > now

    @pytest.mark.asyncio
    async def test_svid_private_key_format(self, mock_identity_provider):
        """Test that SVID private key is in correct format."""
        svid = await mock_identity_provider.get_svid()

        # Should be PEM-encoded
        assert svid.private_key.startswith(b"-----BEGIN")
        assert b"PRIVATE KEY" in svid.private_key

        # Should be parseable
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        private_key = serialization.load_pem_private_key(
            svid.private_key,
            password=None,
            backend=default_backend()
        )
        assert private_key is not None


class TestAutoRotation:
    """Test automatic SVID rotation."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_auto_rotation_enabled(self):
        """Test that auto-rotation works when enabled."""
        provider = MockIdentityProvider(
            spiffe_id="spiffe://test.local/agent/auto-rotate",
            rotation_interval=2,  # 2 seconds
            auto_rotate=True,
        )

        svid1 = await provider.get_svid()

        # Start auto-rotation
        await provider.start_auto_rotation()

        # Wait for rotation
        await asyncio.sleep(3)

        svid2 = await provider.get_svid()

        # Should have rotated
        assert svid2.cert_chain != svid1.cert_chain

        # Stop auto-rotation
        await provider.stop_auto_rotation()

    @pytest.mark.asyncio
    async def test_stop_auto_rotation(self):
        """Test stopping auto-rotation."""
        provider = MockIdentityProvider(
            spiffe_id="spiffe://test.local/agent/auto-rotate",
            rotation_interval=1,
            auto_rotate=True,
        )

        await provider.start_auto_rotation()

        # Stop rotation
        await provider.stop_auto_rotation()

        svid1 = await provider.get_svid()

        # Wait beyond rotation interval
        await asyncio.sleep(2)

        svid2 = await provider.get_svid()

        # Should NOT have rotated (same SVID)
        assert svid2.cert_chain == svid1.cert_chain


class TestTrustDomainExtraction:
    """Test trust domain extraction from SPIFFE IDs."""

    @pytest.mark.parametrize(
        "spiffe_id,expected_domain",
        [
            ("spiffe://test.local/agent/test", "test.local"),
            ("spiffe://example.com/service/api", "example.com"),
            ("spiffe://multi.part.domain.com/path/to/service", "multi.part.domain.com"),
        ],
    )
    def test_extract_trust_domain(self, spiffe_id, expected_domain):
        """Test extracting trust domain from SPIFFE ID."""
        provider = MockIdentityProvider(spiffe_id=spiffe_id)
        assert provider.trust_domain == expected_domain

    def test_invalid_spiffe_id_format(self):
        """Test that invalid SPIFFE ID format raises error."""
        with pytest.raises(ValueError, match="Invalid SPIFFE ID"):
            MockIdentityProvider(spiffe_id="not-a-spiffe-id")

        with pytest.raises(ValueError, match="Invalid SPIFFE ID"):
            MockIdentityProvider(spiffe_id="http://test.local/agent/test")


class TestSPIFFEIdentityProvider:
    """Test real SPIFFE identity provider (requires SPIRE)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connect_to_spire(self):
        """Test connecting to SPIRE Workload API."""
        # This test requires a running SPIRE agent
        # Skip if not available
        pytest.skip("Requires running SPIRE agent")

        # from agentweave.identity import SPIFFEIdentityProvider
        #
        # provider = SPIFFEIdentityProvider(
        #     endpoint="unix:///run/spire/sockets/agent.sock"
        # )
        #
        # svid = await provider.get_svid()
        # assert svid is not None
        # assert svid.spiffe_id.startswith("spiffe://")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fetch_trust_bundles(self):
        """Test fetching trust bundles from SPIRE."""
        pytest.skip("Requires running SPIRE agent")

        # from agentweave.identity import SPIFFEIdentityProvider
        #
        # provider = SPIFFEIdentityProvider()
        # bundle = await provider.get_trust_bundle("test.local")
        # assert bundle is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_watch_svid_updates(self):
        """Test watching for SVID updates from SPIRE."""
        pytest.skip("Requires running SPIRE agent")

        # from agentweave.identity import SPIFFEIdentityProvider
        #
        # provider = SPIFFEIdentityProvider()
        # updates = []
        #
        # async for svid in provider.watch_updates():
        #     updates.append(svid)
        #     if len(updates) >= 1:
        #         break
        #
        # assert len(updates) > 0


class TestIdentityProviderInterface:
    """Test identity provider interface compliance."""

    @pytest.mark.asyncio
    async def test_provider_has_required_methods(self, mock_identity_provider):
        """Test that provider implements required interface."""
        assert hasattr(mock_identity_provider, "get_svid")
        assert hasattr(mock_identity_provider, "get_trust_bundle")
        assert hasattr(mock_identity_provider, "get_spiffe_id")
        assert hasattr(mock_identity_provider, "watch_updates")

    @pytest.mark.asyncio
    async def test_get_svid_is_async(self, mock_identity_provider):
        """Test that get_svid is async."""
        import inspect
        assert inspect.iscoroutinefunction(mock_identity_provider.get_svid)

    @pytest.mark.asyncio
    async def test_watch_updates_is_async_generator(self, mock_identity_provider):
        """Test that watch_updates is async generator."""
        import inspect
        result = mock_identity_provider.watch_updates()
        assert inspect.isasyncgen(result)

        # Clean up
        await result.aclose()
