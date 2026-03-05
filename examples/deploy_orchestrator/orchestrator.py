"""
CI/CD Deployment Orchestrator

Demonstrates:
- Multi-environment deployment orchestration
- Production safety gates (staging must succeed first)
- Automatic rollback on verification failure
- Deployment state machine
- Audit logging of all deployment operations
"""

import asyncio
from enum import Enum
from datetime import datetime, timezone
from typing import Optional

from agentweave import (
    SecureAgent,
    AgentConfig,
    capability,
    requires_peer,
    audit_log,
    get_current_context,
)


class DeployState(str, Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class EnvironmentAgent(SecureAgent):
    """
    Manages a single deployment environment (staging or production).
    Only the orchestrator can deploy or rollback.
    """

    def __init__(self, config: AgentConfig, env_name: str = "staging", **kwargs):
        super().__init__(config=config, **kwargs)
        self.env_name = env_name
        self._current_version: Optional[str] = None
        self._previous_version: Optional[str] = None
        self._healthy = True
        self._deploy_history: list[dict] = []

    @capability("health_check")
    @audit_log()
    async def health_check(self) -> dict:
        """Check environment health. Any devops agent can call this."""
        return {
            "environment": self.env_name,
            "healthy": self._healthy,
            "current_version": self._current_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @capability("apply_deployment")
    @requires_peer("spiffe://devops.example/agent/orchestrator")
    @audit_log()
    async def apply_deployment(self, service: str, version: str) -> dict:
        """
        Deploy a service version. Only the orchestrator can call this.
        """
        self._previous_version = self._current_version
        self._current_version = version

        self._deploy_history.append({
            "action": "deploy",
            "service": service,
            "version": version,
            "previous_version": self._previous_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self.env_name,
        })

        return {
            "environment": self.env_name,
            "service": service,
            "version": version,
            "previous_version": self._previous_version,
            "status": "deployed",
        }

    @capability("verify_deployment")
    @requires_peer("spiffe://devops.example/agent/orchestrator")
    @audit_log()
    async def verify_deployment(self, service: str, version: str) -> dict:
        """
        Verify a deployment is healthy. Only the orchestrator can call this.
        Returns success if the current version matches and environment is healthy.
        """
        version_match = self._current_version == version
        return {
            "environment": self.env_name,
            "service": service,
            "version": version,
            "current_version": self._current_version,
            "healthy": self._healthy and version_match,
            "version_match": version_match,
        }

    @capability("rollback")
    @requires_peer("spiffe://devops.example/agent/orchestrator")
    @audit_log()
    async def rollback(self, service: str, reason: str) -> dict:
        """
        Rollback to previous version. Only the orchestrator can call this.
        """
        rolled_back_from = self._current_version
        self._current_version = self._previous_version
        self._previous_version = None

        self._deploy_history.append({
            "action": "rollback",
            "service": service,
            "rolled_back_from": rolled_back_from,
            "rolled_back_to": self._current_version,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": self.env_name,
        })

        return {
            "environment": self.env_name,
            "service": service,
            "rolled_back_from": rolled_back_from,
            "current_version": self._current_version,
            "status": "rolled_back",
            "reason": reason,
        }

    @capability("get_deploy_history")
    @audit_log()
    async def get_deploy_history(self) -> dict:
        """Get deployment history for this environment."""
        return {
            "environment": self.env_name,
            "history": self._deploy_history,
            "current_version": self._current_version,
        }


class DeployOrchestrator(SecureAgent):
    """
    Orchestrates deployments across environments.

    Enforces:
    - Staging must succeed before production
    - Automatic rollback on verification failure
    - Full audit trail of all deployment operations
    """

    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__(config=config, **kwargs)
        self._deployments: dict[str, dict] = {}
        self._staging_successes: dict[str, str] = {}  # service -> version

    def _create_deployment(self, service: str, version: str,
                           environment: str) -> dict:
        """Create a deployment record."""
        deploy_id = f"deploy-{service}-{version}-{environment}-{len(self._deployments)}"
        record = {
            "deploy_id": deploy_id,
            "service": service,
            "version": version,
            "environment": environment,
            "state": DeployState.PENDING,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "steps": [],
        }
        self._deployments[deploy_id] = record
        return record

    def _update_state(self, deploy_id: str, state: DeployState, detail: str = ""):
        """Update deployment state and log the step."""
        record = self._deployments[deploy_id]
        record["state"] = state
        record["steps"].append({
            "state": state.value,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @capability("deploy")
    @audit_log()
    async def deploy(self, service: str, version: str,
                     environment: str) -> dict:
        """
        Deploy a service to an environment.

        For production: requires the same service+version to have
        succeeded in staging first.
        """
        # Production safety gate
        if environment == "production":
            staged_version = self._staging_successes.get(service)
            if staged_version != version:
                return {
                    "error": "Production deployment blocked",
                    "reason": f"Version {version} of {service} has not been "
                              f"successfully deployed to staging. "
                              f"Staged version: {staged_version}",
                    "environment": environment,
                }

        record = self._create_deployment(service, version, environment)
        deploy_id = record["deploy_id"]

        # Step 1: Mark as deploying
        self._update_state(deploy_id, DeployState.DEPLOYING,
                          f"Starting deployment of {service} v{version} to {environment}")

        # Step 2: Simulate calling environment agent to apply deployment
        # In a real scenario: await self.call_agent(target=env_spiffe_id, ...)
        self._update_state(deploy_id, DeployState.VERIFYING,
                          "Deployment applied, verifying...")

        # Step 3: Mark as complete (in real use, verification could fail)
        self._update_state(deploy_id, DeployState.COMPLETE,
                          f"Deployment verified successfully")

        # Track staging successes for production gate
        if environment == "staging":
            self._staging_successes[service] = version

        return {
            "deploy_id": deploy_id,
            "service": service,
            "version": version,
            "environment": environment,
            "state": DeployState.COMPLETE.value,
            "steps": record["steps"],
        }

    @capability("deploy_with_rollback")
    @audit_log()
    async def deploy_with_rollback(self, service: str, version: str,
                                    environment: str,
                                    simulate_failure: bool = False) -> dict:
        """
        Deploy with automatic rollback on verification failure.
        Set simulate_failure=True to test rollback behavior.
        """
        if environment == "production":
            staged_version = self._staging_successes.get(service)
            if staged_version != version:
                return {
                    "error": "Production deployment blocked",
                    "reason": f"Version {version} not staged",
                }

        record = self._create_deployment(service, version, environment)
        deploy_id = record["deploy_id"]

        self._update_state(deploy_id, DeployState.DEPLOYING,
                          f"Deploying {service} v{version}")

        self._update_state(deploy_id, DeployState.VERIFYING, "Verifying...")

        if simulate_failure:
            # Verification failed - trigger rollback
            self._update_state(deploy_id, DeployState.ROLLING_BACK,
                              "Verification failed, rolling back")
            self._update_state(deploy_id, DeployState.ROLLED_BACK,
                              "Rollback complete")
            return {
                "deploy_id": deploy_id,
                "state": DeployState.ROLLED_BACK.value,
                "reason": "Post-deploy verification failed",
                "steps": record["steps"],
            }

        self._update_state(deploy_id, DeployState.COMPLETE, "Verified OK")

        if environment == "staging":
            self._staging_successes[service] = version

        return {
            "deploy_id": deploy_id,
            "state": DeployState.COMPLETE.value,
            "steps": record["steps"],
        }

    @capability("get_deployment")
    @audit_log()
    async def get_deployment(self, deploy_id: str) -> dict:
        """Get deployment status by ID."""
        record = self._deployments.get(deploy_id)
        if not record:
            return {"error": "Deployment not found", "deploy_id": deploy_id}
        return record

    @capability("list_deployments")
    @audit_log()
    async def list_deployments(self, environment: Optional[str] = None) -> dict:
        """List all deployments, optionally filtered by environment."""
        deployments = list(self._deployments.values())
        if environment:
            deployments = [d for d in deployments if d["environment"] == environment]
        return {
            "count": len(deployments),
            "deployments": deployments,
        }


async def demo():
    """Demonstrate the deployment orchestrator."""
    print("CI/CD Deployment Orchestrator")
    print("=" * 50)
    print()
    print("Deployment State Machine:")
    print("  pending -> deploying -> verifying -> complete")
    print("                                    -> rolling_back -> rolled_back")
    print()
    print("Safety Rules:")
    print("  1. Production requires successful staging first")
    print("  2. Failed verification triggers automatic rollback")
    print("  3. Only orchestrator SPIFFE ID can deploy to environments")
    print("  4. All operations are audit-logged")


if __name__ == "__main__":
    asyncio.run(demo())
