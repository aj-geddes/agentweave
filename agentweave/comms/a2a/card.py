"""
Agent Card implementation for A2A protocol.

Agent Cards advertise capabilities, endpoints, and authentication requirements
according to the A2A protocol specification.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Capability(BaseModel):
    """Represents an agent capability as per A2A protocol."""

    name: str = Field(..., description="Capability identifier")
    description: str = Field(..., description="Human-readable description")
    input_modes: List[str] = Field(
        default_factory=lambda: ["application/json"],
        description="Supported input content types"
    )
    output_modes: List[str] = Field(
        default_factory=lambda: ["application/json"],
        description="Supported output content types"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON Schema for capability parameters"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "description": self.description,
            "input_modes": self.input_modes,
            "output_modes": self.output_modes,
        }
        if self.parameters:
            result["parameters"] = self.parameters
        return result


class AuthScheme(BaseModel):
    """Authentication scheme specification."""

    type: str = Field(..., description="Auth type: spiffe, oauth2, api_key, etc.")
    description: Optional[str] = Field(None, description="Scheme description")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Scheme-specific metadata"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"type": self.type}
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class AgentCard(BaseModel):
    """
    A2A Agent Card for capability advertisement.

    Served at /.well-known/agent.json endpoint to advertise agent capabilities,
    authentication requirements, and metadata.
    """

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    url: str = Field(..., description="Agent base URL")
    version: str = Field(default="1.0.0", description="Agent version")

    capabilities: List[Capability] = Field(
        default_factory=list,
        description="List of agent capabilities"
    )

    authentication: Dict[str, Any] = Field(
        default_factory=lambda: {"schemes": []},
        description="Authentication configuration"
    )

    extensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom extensions (e.g., spiffe_id)"
    )

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v

    @classmethod
    def from_config(
        cls,
        name: str,
        description: str,
        url: str,
        spiffe_id: str,
        version: str = "1.0.0",
        capabilities: Optional[List[Capability]] = None,
        auth_schemes: Optional[List[AuthScheme]] = None
    ) -> "AgentCard":
        """
        Create an AgentCard from agent configuration.

        Args:
            name: Agent name
            description: Agent description
            url: Agent base URL
            spiffe_id: SPIFFE ID for this agent
            version: Agent version
            capabilities: List of capabilities
            auth_schemes: List of authentication schemes

        Returns:
            AgentCard instance
        """
        # Default to SPIFFE authentication if not specified
        if auth_schemes is None:
            auth_schemes = [
                AuthScheme(
                    type="spiffe",
                    description="SPIFFE/SPIRE mutual TLS authentication",
                    metadata={"spiffe_id": spiffe_id}
                )
            ]

        authentication = {
            "schemes": [scheme.to_dict() for scheme in auth_schemes]
        }

        return cls(
            name=name,
            description=description,
            url=url,
            version=version,
            capabilities=capabilities or [],
            authentication=authentication,
            extensions={"spiffe_id": spiffe_id}
        )

    def to_json(self) -> str:
        """
        Serialize AgentCard to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert AgentCard to dictionary.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "authentication": self.authentication,
            "extensions": self.extensions
        }

    @classmethod
    def from_json(cls, json_str: str) -> "AgentCard":
        """
        Deserialize AgentCard from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            AgentCard instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        """
        Create AgentCard from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AgentCard instance
        """
        # Parse capabilities
        capabilities = []
        for cap_data in data.get("capabilities", []):
            capabilities.append(Capability(**cap_data))

        return cls(
            name=data["name"],
            description=data["description"],
            url=data["url"],
            version=data.get("version", "1.0.0"),
            capabilities=capabilities,
            authentication=data.get("authentication", {"schemes": []}),
            extensions=data.get("extensions", {})
        )

    def get_spiffe_id(self) -> Optional[str]:
        """
        Extract SPIFFE ID from extensions.

        Returns:
            SPIFFE ID if present, None otherwise
        """
        return self.extensions.get("spiffe_id")

    def has_capability(self, capability_name: str) -> bool:
        """
        Check if agent has a specific capability.

        Args:
            capability_name: Name of the capability to check

        Returns:
            True if capability exists, False otherwise
        """
        return any(cap.name == capability_name for cap in self.capabilities)

    def get_capability(self, capability_name: str) -> Optional[Capability]:
        """
        Get a capability by name.

        Args:
            capability_name: Name of the capability to retrieve

        Returns:
            Capability if found, None otherwise
        """
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None
