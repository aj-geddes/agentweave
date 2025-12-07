"""
Agent discovery implementation.

Provides discovery mechanisms for finding and caching agent information
via well-known endpoints and service mesh integration.
"""

import asyncio
import time
from typing import Optional, Dict, List
from dataclasses import dataclass
import httpx

from agentweave.comms.a2a.card import AgentCard


@dataclass
class CachedAgentCard:
    """Cached agent card with expiration."""

    card: AgentCard
    cached_at: float
    ttl: int = 300  # 5 minutes default TTL

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return (time.time() - self.cached_at) > self.ttl


class DiscoveryError(Exception):
    """Base exception for discovery errors."""
    pass


class DiscoveryClient:
    """
    Client for discovering agents.

    Supports discovery via well-known endpoints with caching and
    optional service mesh integration.
    """

    def __init__(
        self,
        cache_ttl: int = 300,
        timeout: float = 10.0,
        enable_cache: bool = True
    ):
        """
        Initialize discovery client.

        Args:
            cache_ttl: Cache TTL in seconds
            timeout: Request timeout in seconds
            enable_cache: Enable agent card caching
        """
        self._cache_ttl = cache_ttl
        self._timeout = timeout
        self._enable_cache = enable_cache
        self._cache: Dict[str, CachedAgentCard] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._cache_lock = asyncio.Lock()

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """
        Ensure HTTP client is initialized.

        Returns:
            HTTP client instance
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def discover_agent(
        self,
        url: str,
        force_refresh: bool = False
    ) -> AgentCard:
        """
        Discover agent by URL.

        Fetches agent card from /.well-known/agent.json endpoint with caching.

        Args:
            url: Base URL of the agent
            force_refresh: Force cache refresh

        Returns:
            AgentCard for the discovered agent

        Raises:
            DiscoveryError: If discovery fails
        """
        # Normalize URL
        base_url = url.rstrip('/')

        # Check cache first
        if self._enable_cache and not force_refresh:
            async with self._cache_lock:
                cached = self._cache.get(base_url)
                if cached and not cached.is_expired():
                    return cached.card

        # Fetch agent card
        card = await self._fetch_agent_card(base_url)

        # Update cache
        if self._enable_cache:
            async with self._cache_lock:
                self._cache[base_url] = CachedAgentCard(
                    card=card,
                    cached_at=time.time(),
                    ttl=self._cache_ttl
                )

        return card

    async def _fetch_agent_card(self, base_url: str) -> AgentCard:
        """
        Fetch agent card from well-known endpoint.

        Args:
            base_url: Base URL of the agent

        Returns:
            AgentCard

        Raises:
            DiscoveryError: If fetch fails
        """
        client = await self._ensure_client()
        card_url = f"{base_url}/.well-known/agent.json"

        try:
            response = await client.get(card_url)
            response.raise_for_status()

            card_data = response.json()
            return AgentCard.from_dict(card_data)

        except httpx.HTTPError as e:
            raise DiscoveryError(
                f"Failed to fetch agent card from {base_url}: {e}"
            ) from e
        except (ValueError, KeyError) as e:
            raise DiscoveryError(
                f"Invalid agent card format from {base_url}: {e}"
            ) from e

    async def discover_by_spiffe_id(
        self,
        spiffe_id: str,
        service_mesh_resolver: Optional[callable] = None
    ) -> AgentCard:
        """
        Discover agent by SPIFFE ID.

        Requires a service mesh resolver to map SPIFFE ID to URL.

        Args:
            spiffe_id: SPIFFE ID of the agent
            service_mesh_resolver: Function to resolve SPIFFE ID to URL

        Returns:
            AgentCard for the agent

        Raises:
            DiscoveryError: If discovery fails
            ValueError: If service_mesh_resolver not provided
        """
        if not service_mesh_resolver:
            raise ValueError(
                "service_mesh_resolver required for SPIFFE ID discovery"
            )

        try:
            # Resolve SPIFFE ID to URL
            url = await service_mesh_resolver(spiffe_id)
            if not url:
                raise DiscoveryError(
                    f"Could not resolve SPIFFE ID to URL: {spiffe_id}"
                )

            # Discover via URL
            return await self.discover_agent(url)

        except Exception as e:
            raise DiscoveryError(
                f"Failed to discover agent by SPIFFE ID {spiffe_id}: {e}"
            ) from e

    async def discover_multiple(
        self,
        urls: List[str],
        ignore_errors: bool = False
    ) -> List[AgentCard]:
        """
        Discover multiple agents concurrently.

        Args:
            urls: List of agent URLs
            ignore_errors: Continue on errors (skip failed discoveries)

        Returns:
            List of discovered agent cards

        Raises:
            DiscoveryError: If any discovery fails and ignore_errors=False
        """
        tasks = [self.discover_agent(url) for url in urls]

        if ignore_errors:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Filter out exceptions
            return [r for r in results if isinstance(r, AgentCard)]
        else:
            return await asyncio.gather(*tasks)

    async def clear_cache(self, url: Optional[str] = None) -> None:
        """
        Clear agent card cache.

        Args:
            url: Specific URL to clear (None = clear all)
        """
        async with self._cache_lock:
            if url:
                base_url = url.rstrip('/')
                self._cache.pop(base_url, None)
            else:
                self._cache.clear()

    async def get_cached_cards(self) -> Dict[str, AgentCard]:
        """
        Get all cached agent cards.

        Returns:
            Dictionary mapping URLs to agent cards
        """
        async with self._cache_lock:
            return {
                url: cached.card
                for url, cached in self._cache.items()
                if not cached.is_expired()
            }

    async def cleanup_expired_cache(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        async with self._cache_lock:
            expired_urls = [
                url for url, cached in self._cache.items()
                if cached.is_expired()
            ]

            for url in expired_urls:
                del self._cache[url]

            return len(expired_urls)

    async def verify_agent_capability(
        self,
        url: str,
        capability_name: str
    ) -> bool:
        """
        Verify that an agent has a specific capability.

        Args:
            url: Agent URL
            capability_name: Name of capability to check

        Returns:
            True if agent has capability, False otherwise

        Raises:
            DiscoveryError: If discovery fails
        """
        card = await self.discover_agent(url)
        return card.has_capability(capability_name)

    async def find_agents_with_capability(
        self,
        urls: List[str],
        capability_name: str
    ) -> List[AgentCard]:
        """
        Find all agents with a specific capability.

        Args:
            urls: List of agent URLs to check
            capability_name: Capability to search for

        Returns:
            List of agent cards with the capability
        """
        cards = await self.discover_multiple(urls, ignore_errors=True)
        return [
            card for card in cards
            if card.has_capability(capability_name)
        ]

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = len(self._cache)
        expired = sum(
            1 for cached in self._cache.values()
            if cached.is_expired()
        )

        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired
        }


class ServiceMeshDiscovery:
    """
    Service mesh integration for agent discovery.

    Placeholder for service mesh-specific discovery logic (e.g., Kubernetes, Consul).
    """

    def __init__(self, namespace: Optional[str] = None):
        """
        Initialize service mesh discovery.

        Args:
            namespace: Service mesh namespace
        """
        self.namespace = namespace

    async def resolve_spiffe_id_to_url(self, spiffe_id: str) -> Optional[str]:
        """
        Resolve SPIFFE ID to service URL.

        This would integrate with service mesh (e.g., Kubernetes Service Discovery,
        Consul, Istio) to map SPIFFE IDs to service endpoints.

        Args:
            spiffe_id: SPIFFE ID to resolve

        Returns:
            Service URL if found, None otherwise
        """
        # TODO: Implement service mesh integration
        # Example for Kubernetes:
        # - Parse SPIFFE ID to extract service name
        # - Query Kubernetes API for service endpoint
        # - Return https://<service>.<namespace>.svc.cluster.local

        # Placeholder implementation
        raise NotImplementedError(
            "Service mesh integration not yet implemented. "
            "Provide custom resolver function."
        )

    async def discover_all_agents(self) -> List[str]:
        """
        Discover all agents in the service mesh.

        Returns:
            List of agent URLs

        Raises:
            NotImplementedError: Service mesh integration not implemented
        """
        # TODO: Implement service mesh-wide discovery
        raise NotImplementedError(
            "Service mesh-wide discovery not yet implemented"
        )
