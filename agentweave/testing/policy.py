"""
Policy testing utilities for AgentWeave SDK.

This module provides utilities for testing OPA policies without
requiring a running OPA server.
"""

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    reason: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class PolicySimulator:
    """
    Policy simulator for testing Rego policies locally.

    Allows testing OPA policies without a running OPA server by using
    the OPA CLI to evaluate policies against test inputs.

    Example:
        simulator = PolicySimulator("policies/authz.rego")

        # Test allow scenario
        decision = simulator.check(
            caller="spiffe://test.local/agent/orchestrator",
            callee="spiffe://test.local/agent/search",
            action="search"
        )
        assert decision.allowed == True

        # Test deny scenario
        decision = simulator.check(
            caller="spiffe://evil.com/agent/attacker",
            callee="spiffe://test.local/agent/search",
            action="search"
        )
        assert decision.allowed == False
    """

    def __init__(
        self,
        policy_path: Optional[str] = None,
        policy_content: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize policy simulator.

        Args:
            policy_path: Path to Rego policy file
            policy_content: Rego policy as string (alternative to policy_path)
            data: Optional policy data to load

        Raises:
            ValueError: If neither policy_path nor policy_content provided
        """
        if not policy_path and not policy_content:
            raise ValueError("Must provide either policy_path or policy_content")

        self.policy_path = Path(policy_path) if policy_path else None
        self.policy_content = policy_content
        self.data = data or {}
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None

        # Check if OPA CLI is available
        self._check_opa_available()

    def _check_opa_available(self):
        """Check if OPA CLI is available."""
        try:
            result = subprocess.run(
                ["opa", "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError("OPA CLI not working properly")
        except FileNotFoundError:
            raise RuntimeError(
                "OPA CLI not found. Install it from: https://www.openpolicyagent.org/docs/latest/#running-opa"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("OPA CLI timed out")

    def check(
        self,
        caller: str,
        action: str,
        callee: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """
        Check if a request would be allowed by the policy.

        Args:
            caller: Caller SPIFFE ID
            action: Action being performed
            callee: Callee SPIFFE ID (for outbound checks)
            context: Additional context

        Returns:
            PolicyDecision with allow/deny result

        Example:
            decision = simulator.check(
                caller="spiffe://test.local/agent/orchestrator",
                callee="spiffe://test.local/agent/search",
                action="search"
            )
            assert decision.allowed
        """
        # Build input document
        input_doc = {
            "caller_spiffe_id": caller,
            "action": action,
            "context": context or {},
        }

        if callee:
            input_doc["callee_spiffe_id"] = callee

        return self.evaluate(input_doc)

    def evaluate(self, input_doc: Dict[str, Any]) -> PolicyDecision:
        """
        Evaluate policy against input document.

        Args:
            input_doc: Input document to evaluate

        Returns:
            PolicyDecision with evaluation result
        """
        # Create temp directory for policy and input if needed
        if not self._temp_dir:
            self._temp_dir = tempfile.TemporaryDirectory()

        temp_path = Path(self._temp_dir.name)

        # Write policy to temp file if provided as content
        if self.policy_content:
            policy_file = temp_path / "policy.rego"
            with open(policy_file, "w") as f:
                f.write(self.policy_content)
            policy_path = policy_file
        else:
            policy_path = self.policy_path

        # Write input to temp file
        input_file = temp_path / "input.json"
        with open(input_file, "w") as f:
            json.dump(input_doc, f)

        # Write data to temp file if provided
        data_file = None
        if self.data:
            data_file = temp_path / "data.json"
            with open(data_file, "w") as f:
                json.dump(self.data, f)

        # Run OPA evaluation
        cmd = [
            "opa",
            "eval",
            "--data", str(policy_path),
            "--input", str(input_file),
            "--format", "json",
        ]

        if data_file:
            cmd.extend(["--data", str(data_file)])

        # Query for the allow decision
        cmd.append("data.agentweave.authz.allow")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise RuntimeError(f"OPA evaluation failed: {result.stderr}")

            # Parse result
            output = json.loads(result.stdout)

            # Extract allow decision
            if "result" in output and output["result"]:
                expressions = output["result"][0].get("expressions", [])
                if expressions:
                    allowed = expressions[0].get("value", False)

                    return PolicyDecision(
                        allowed=allowed,
                        result=output,
                    )

            # Default deny if no result
            return PolicyDecision(
                allowed=False,
                reason="No policy result",
                result=output,
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("OPA evaluation timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse OPA output: {e}")

    def test_scenarios(self, scenarios: List[Dict[str, Any]]) -> Dict[str, PolicyDecision]:
        """
        Test multiple scenarios against the policy.

        Args:
            scenarios: List of test scenarios with input and expected result

        Returns:
            Dict mapping scenario name to decision

        Example:
            results = simulator.test_scenarios([
                {
                    "name": "orchestrator_can_search",
                    "input": {
                        "caller_spiffe_id": "spiffe://test.local/agent/orchestrator",
                        "callee_spiffe_id": "spiffe://test.local/agent/search",
                        "action": "search",
                    },
                    "expected": True,
                },
                {
                    "name": "unknown_agent_denied",
                    "input": {
                        "caller_spiffe_id": "spiffe://evil.com/agent/bad",
                        "callee_spiffe_id": "spiffe://test.local/agent/search",
                        "action": "search",
                    },
                    "expected": False,
                }
            ])

            for name, decision in results.items():
                print(f"{name}: {'PASS' if decision.allowed else 'FAIL'}")
        """
        results = {}

        for scenario in scenarios:
            name = scenario.get("name", f"scenario_{len(results)}")
            input_doc = scenario["input"]

            decision = self.evaluate(input_doc)
            results[name] = decision

            # Check expected result if provided
            if "expected" in scenario:
                expected = scenario["expected"]
                if decision.allowed != expected:
                    print(f"SCENARIO FAILED: {name}")
                    print(f"  Expected: {expected}")
                    print(f"  Got: {decision.allowed}")

        return results

    def assert_allow(
        self,
        caller: str,
        action: str,
        callee: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Assert that a request is allowed.

        Args:
            caller: Caller SPIFFE ID
            action: Action being performed
            callee: Callee SPIFFE ID
            context: Additional context

        Raises:
            AssertionError: If request is denied

        Example:
            simulator.assert_allow(
                caller="spiffe://test.local/agent/orchestrator",
                callee="spiffe://test.local/agent/search",
                action="search"
            )
        """
        decision = self.check(caller, action, callee, context)
        if not decision.allowed:
            raise AssertionError(
                f"Expected request to be allowed but was denied. "
                f"Caller: {caller}, Callee: {callee}, Action: {action}"
            )

    def assert_deny(
        self,
        caller: str,
        action: str,
        callee: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Assert that a request is denied.

        Args:
            caller: Caller SPIFFE ID
            action: Action being performed
            callee: Callee SPIFFE ID
            context: Additional context

        Raises:
            AssertionError: If request is allowed

        Example:
            simulator.assert_deny(
                caller="spiffe://evil.com/agent/bad",
                callee="spiffe://test.local/agent/search",
                action="search"
            )
        """
        decision = self.check(caller, action, callee, context)
        if decision.allowed:
            raise AssertionError(
                f"Expected request to be denied but was allowed. "
                f"Caller: {caller}, Callee: {callee}, Action: {action}"
            )

    def load_data(self, data: Dict[str, Any]):
        """
        Load policy data.

        Args:
            data: Policy data to load

        Example:
            simulator.load_data({
                "federation": {
                    "allowed_domains": ["test.local", "partner.example.com"]
                },
                "allowed_actions": {
                    "spiffe://test.local/agent/search": ["search", "index"]
                }
            })
        """
        self.data = data

    def __del__(self):
        """Clean up temporary directory."""
        if self._temp_dir:
            self._temp_dir.cleanup()


def create_test_policy(
    trust_domain: str = "test.local",
    allowed_actions: Optional[Dict[str, List[str]]] = None,
    federated_domains: Optional[List[str]] = None,
) -> str:
    """
    Create a test policy with common patterns.

    Args:
        trust_domain: Trust domain for agents
        allowed_actions: Dict mapping agent SPIFFE IDs to allowed actions
        federated_domains: List of federated trust domains

    Returns:
        Rego policy as string

    Example:
        policy = create_test_policy(
            trust_domain="test.local",
            allowed_actions={
                "spiffe://test.local/agent/search": ["search", "index"],
                "spiffe://test.local/agent/orchestrator": ["*"],
            },
            federated_domains=["partner.example.com"]
        )
        simulator = PolicySimulator(policy_content=policy)
    """
    allowed_actions = allowed_actions or {}
    federated_domains = federated_domains or []

    policy = f"""
package agentweave.authz

import rego.v1

default allow := false

# Allow agents within same trust domain
allow if {{
    same_trust_domain
    valid_action
}}

# Allow federated domains
allow if {{
    federated_trust_domain
    valid_action
}}

same_trust_domain if {{
    startswith(input.caller_spiffe_id, "spiffe://{trust_domain}/")
    startswith(input.callee_spiffe_id, "spiffe://{trust_domain}/")
}}

federated_trust_domain if {{
    some domain in {json.dumps(federated_domains)}
    startswith(input.caller_spiffe_id, concat("", ["spiffe://", domain, "/"]))
}}

valid_action if {{
    input.callee_spiffe_id in data.allowed_actions
    allowed := data.allowed_actions[input.callee_spiffe_id]
    input.action in allowed
}}

# Wildcard action support
valid_action if {{
    input.callee_spiffe_id in data.allowed_actions
    allowed := data.allowed_actions[input.callee_spiffe_id]
    "*" in allowed
}}
"""

    return policy
