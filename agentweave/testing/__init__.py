"""
AgentWeave SDK - Testing Utilities

This module provides testing utilities, mocks, and fixtures for testing
agents built with the AgentWeave SDK.

Export all public testing utilities for easy import:
    from agentweave.testing import MockIdentityProvider, mock_identity_provider

"""

from .mocks import (
    MockIdentityProvider,
    MockAuthorizationProvider,
    MockTransport,
)

from .fixtures import (
    mock_identity_provider,
    mock_identity_provider_with_rotation,
    mock_authz_provider,
    mock_authz_provider_permissive,
    mock_transport,
    test_agent,
    test_config,
    test_config_dev,
    spiffe_ids,
    sample_tasks,
)

from .cluster import TestCluster

from .policy import PolicySimulator

__all__ = [
    # Mock providers
    "MockIdentityProvider",
    "MockAuthorizationProvider",
    "MockTransport",

    # Fixtures
    "mock_identity_provider",
    "mock_identity_provider_with_rotation",
    "mock_authz_provider",
    "mock_authz_provider_permissive",
    "mock_transport",
    "test_agent",
    "test_config",
    "test_config_dev",
    "spiffe_ids",
    "sample_tasks",

    # Test infrastructure
    "TestCluster",
    "PolicySimulator",
]
