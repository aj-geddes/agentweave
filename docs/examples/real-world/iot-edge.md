---
layout: page
title: IoT/Edge Computing Use Case
permalink: /examples/real-world/iot-edge/
parent: Real-World Scenarios
grand_parent: Examples Overview
nav_order: 3
---

# IoT/Edge: Smart Building System

**Industry**: IoT / Building Management
**Scenario**: Secure edge device communication with cloud analytics
**Challenges**: Constrained resources, intermittent connectivity, device attestation
**Time to Complete**: 60 minutes

## Business Problem

**SmartBuilding Corp** manages commercial buildings with IoT devices:

1. **Edge Devices**: Sensors (HVAC, occupancy, energy) run lightweight agents
2. **Edge Gateway**: Local processing and buffering
3. **Cloud Platform**: Analytics, ML, dashboards
4. **Security Requirements**:
   - Device attestation (prove device is genuine)
   - Encrypted communication (even on local network)
   - Offline operation (store-and-forward)
   - OTA updates (secure firmware distribution)
   - Resource constraints (limited CPU, memory)

### Challenges

| Challenge | Traditional IoT | AgentWeave Solution |
|-----------|----------------|---------------------|
| **Device Identity** | Hardcoded API keys | SPIFFE workload attestation |
| **Firmware Updates** | Insecure HTTP | Signed, verified via SPIFFE |
| **Offline Operation** | Data loss | Store-and-forward agents |
| **Resource Usage** | Heavy cloud SDKs | Lightweight SPIFFE agent |
| **Authorization** | Coarse (device vs cloud) | Fine-grained OPA policies |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Smart Building (Edge)                        │
│                                                                 │
│  ┌───────────────┐   ┌───────────────┐   ┌─────────────────┐  │
│  │  HVAC Sensor  │   │   Occupancy   │   │  Energy Meter   │  │
│  │    Agent      │   │  Sensor Agent │   │     Agent       │  │
│  │               │   │               │   │                 │  │
│  │ • Temp: 72°F  │   │ • Count: 15   │   │ • kWh: 450     │  │
│  │ • Humidity    │   │ • Motion      │   │ • Demand       │  │
│  └───────┬───────┘   └───────┬───────┘   └────────┬────────┘  │
│          │                   │                     │           │
│          │   mTLS (local)    │                     │           │
│          └───────────────────┼─────────────────────┘           │
│                              │                                 │
│                    ┌─────────▼──────────┐                      │
│                    │   Edge Gateway     │                      │
│                    │      Agent         │                      │
│                    │                    │                      │
│                    │ • Aggregate data   │                      │
│                    │ • Local buffering  │                      │
│                    │ • Sync to cloud    │                      │
│                    └─────────┬──────────┘                      │
│                              │                                 │
└──────────────────────────────┼─────────────────────────────────┘
                               │
                               │ mTLS over Internet
                               │ (intermittent)
                               │
┌──────────────────────────────▼─────────────────────────────────┐
│                      Cloud Platform                            │
│                                                                │
│  ┌─────────────────┐     ┌──────────────┐    ┌──────────────┐│
│  │   Ingestion     │────►│  Analytics   │───►│  Dashboard   ││
│  │     Agent       │     │    Agent     │    │    Agent     ││
│  └─────────────────┘     └──────────────┘    └──────────────┘│
│                                                                │
│  ┌─────────────────┐     ┌──────────────┐                     │
│  │   OTA Update    │     │   Device     │                     │
│  │     Agent       │     │  Management  │                     │
│  └─────────────────┘     └──────────────┘                     │
└────────────────────────────────────────────────────────────────┘

Security:
- Every device has SPIFFE identity
- mTLS for all communication (even local)
- Device attestation via SPIRE
- OPA policies for device capabilities
```

## Device Attestation Flow

```
Sensor Device Boots
    │
    ▼
┌─────────────────┐
│ SPIRE Agent     │ ← Runs on device
│ (Lightweight)   │
└────────┬────────┘
         │
         │ 1. Attest workload
         │    (TPM, k8s, Docker, etc.)
         ▼
┌─────────────────┐
│  SPIRE Server   │
│  (Edge Gateway) │
└────────┬────────┘
         │
         │ 2. Verify attestation
         │    (TPM signature, etc.)
         ▼
┌─────────────────┐
│  Issue SVID     │ ← X.509 certificate
│  (Short-lived)  │   Valid: 1 hour
└────────┬────────┘
         │
         │ 3. Use SVID for mTLS
         ▼
┌─────────────────┐
│  Sensor Agent   │ ← Now has identity
│  Ready to send  │   Can communicate
└─────────────────┘
```

## Complete Code

### HVAC Sensor Agent (Edge Device)

```python
# hvac_sensor_agent.py
"""
HVAC Sensor Agent - Runs on constrained edge device.

Constraints:
- Limited CPU (ARM Cortex-M)
- Limited RAM (256MB)
- Intermittent connectivity
- Battery-powered (power efficiency)

Features:
- Lightweight SPIFFE agent
- Store-and-forward buffering
- Efficient mTLS
"""

import asyncio
from typing import Dict, Any
from datetime import datetime
import json

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart


class HVACSensorAgent(SecureAgent):
    """
    Lightweight sensor agent for edge devices.

    Optimized for:
    - Low memory footprint
    - Minimal CPU usage
    - Offline operation
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.edge_gateway = "spiffe://building-1.smart.local/agent/gateway"

        # Local buffer for offline operation
        self._buffer = []
        self._max_buffer_size = 1000  # Store up to 1000 readings

        # Sensor configuration
        self.sensor_id = "HVAC-SENSOR-001"
        self.location = "Floor-2-Zone-A"

    @capability("read_sensors")
    async def read_sensors(self) -> TaskResult:
        """
        Read sensor data.

        Called by edge gateway periodically.
        """
        reading = await self._read_hardware()

        # Add to local buffer
        self._buffer.append(reading)

        # Keep buffer size limited
        if len(self._buffer) > self._max_buffer_size:
            self._buffer.pop(0)

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data=reading)]
            )]
        )

    @capability("sync_buffered")
    async def sync_buffered(self) -> TaskResult:
        """
        Sync buffered readings to gateway.

        This enables store-and-forward:
        - Device buffers readings when offline
        - Gateway pulls when connection restored
        """
        if not self._buffer:
            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={"count": 0})]
                )]
            )

        # Return all buffered readings
        buffered = self._buffer.copy()
        self._buffer.clear()

        self.logger.info(
            f"Syncing {len(buffered)} buffered readings",
            extra={"sensor_id": self.sensor_id}
        )

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "count": len(buffered),
                    "readings": buffered
                })]
            )]
        )

    async def _read_hardware(self) -> Dict[str, Any]:
        """
        Read actual sensor hardware.

        In production, interfaces with:
        - I2C temperature sensor
        - SPI humidity sensor
        - GPIO for fan status
        """
        # Simulate sensor reading
        import random

        return {
            "sensor_id": self.sensor_id,
            "location": self.location,
            "timestamp": datetime.utcnow().isoformat(),
            "temperature_f": round(68 + random.uniform(-5, 5), 1),
            "humidity_percent": round(45 + random.uniform(-10, 10), 1),
            "fan_speed_rpm": random.randint(800, 1200),
            "fan_status": "running",
            "power_mode": "normal"
        }

    async def _periodic_reading(self):
        """
        Periodic sensor reading (background task).

        Runs continuously, even when offline.
        Buffers readings for later sync.
        """
        while True:
            try:
                reading = await self._read_hardware()
                self._buffer.append(reading)

                # Trim buffer
                if len(self._buffer) > self._max_buffer_size:
                    self._buffer.pop(0)

                # Try to send to gateway (fire and forget)
                try:
                    await self.call_agent(
                        target=self.edge_gateway,
                        task_type="receive_reading",
                        payload={"reading": reading},
                        timeout=5.0
                    )
                except Exception:
                    # Gateway unavailable, reading buffered
                    pass

                # Read every 60 seconds
                await asyncio.sleep(60)

            except Exception as e:
                self.logger.error(f"Sensor reading failed: {e}")
                await asyncio.sleep(60)


async def main():
    """
    Run sensor agent.

    On constrained devices, this runs as systemd service.
    """
    agent = HVACSensorAgent.from_config("config/hvac_sensor.yaml")

    # Start periodic reading in background
    asyncio.create_task(agent._periodic_reading())

    # Start agent server (lightweight)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Edge Gateway Agent

```python
# edge_gateway_agent.py
"""
Edge Gateway Agent - Aggregates data from edge devices.

Responsibilities:
- Collect from multiple sensors
- Buffer for cloud sync
- Local processing
- Manage device updates
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart
from agentweave.exceptions import AgentCallError


class EdgeGatewayAgent(SecureAgent):
    """
    Edge gateway for local sensor network.

    Runs on edge hardware (Raspberry Pi, industrial PC, etc.)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cloud_ingestion = "spiffe://smart-building.cloud/agent/ingestion"

        # Local storage
        self._sensor_buffer = defaultdict(list)
        self._max_buffer_per_sensor = 500

        # Sensor registry
        self._sensors = {
            "HVAC-SENSOR-001": "spiffe://building-1.smart.local/agent/hvac-001",
            "OCCUPANCY-001": "spiffe://building-1.smart.local/agent/occupancy-001",
            "ENERGY-001": "spiffe://building-1.smart.local/agent/energy-001"
        }

        # Cloud sync state
        self._cloud_available = True
        self._last_sync = None

    @capability("receive_reading")
    async def receive_reading(self, reading: Dict[str, Any]) -> TaskResult:
        """
        Receive reading from sensor.

        Called by sensors when they have new data.
        """
        sensor_id = reading["sensor_id"]

        # Buffer locally
        self._sensor_buffer[sensor_id].append(reading)

        # Trim buffer
        if len(self._sensor_buffer[sensor_id]) > self._max_buffer_per_sensor:
            self._sensor_buffer[sensor_id].pop(0)

        self.logger.debug(
            "Reading received",
            extra={
                "sensor_id": sensor_id,
                "buffer_size": len(self._sensor_buffer[sensor_id])
            }
        )

        # Try immediate cloud sync (async)
        asyncio.create_task(self._try_cloud_sync(reading))

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={"received": True})]
            )]
        )

    @capability("aggregate_sensors")
    async def aggregate_sensors(self) -> TaskResult:
        """
        Aggregate all sensor data.

        Provides local dashboard/API.
        """
        aggregated = {}

        for sensor_id, agent_id in self._sensors.items():
            try:
                result = await self.call_agent(
                    target=agent_id,
                    task_type="read_sensors",
                    payload={},
                    timeout=5.0
                )

                if result.status == "completed":
                    reading = result.artifacts[0]["data"]
                    aggregated[sensor_id] = reading

            except AgentCallError as e:
                # Sensor unavailable
                aggregated[sensor_id] = {"status": "offline", "error": str(e)}

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "timestamp": datetime.utcnow().isoformat(),
                    "sensors": aggregated,
                    "total_sensors": len(self._sensors),
                    "online_sensors": sum(
                        1 for s in aggregated.values()
                        if s.get("status") != "offline"
                    )
                })]
            )]
        )

    @capability("sync_to_cloud")
    async def sync_to_cloud(self) -> TaskResult:
        """
        Sync buffered data to cloud.

        Called periodically or on-demand.
        """
        if not self._sensor_buffer:
            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={"synced": 0})]
                )]
            )

        total_synced = 0
        failed_sensors = []

        for sensor_id, readings in self._sensor_buffer.items():
            if not readings:
                continue

            try:
                # Send batch to cloud
                result = await self.call_agent(
                    target=self.cloud_ingestion,
                    task_type="ingest_batch",
                    payload={
                        "sensor_id": sensor_id,
                        "readings": readings,
                        "gateway_id": str(self.spiffe_id)
                    },
                    timeout=30.0
                )

                if result.status == "completed":
                    # Clear buffered readings
                    total_synced += len(readings)
                    self._sensor_buffer[sensor_id].clear()
                else:
                    failed_sensors.append(sensor_id)

            except AgentCallError as e:
                # Cloud unavailable, keep buffered
                self.logger.warning(
                    f"Cloud sync failed for {sensor_id}: {e}"
                )
                failed_sensors.append(sensor_id)
                self._cloud_available = False

        if not failed_sensors:
            self._cloud_available = True
            self._last_sync = datetime.utcnow()

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "synced_readings": total_synced,
                    "failed_sensors": failed_sensors,
                    "cloud_available": self._cloud_available,
                    "last_sync": self._last_sync.isoformat() if self._last_sync else None
                })]
            )]
        )

    async def _try_cloud_sync(self, reading: Dict[str, Any]):
        """
        Try to sync single reading to cloud (fire and forget).
        """
        if not self._cloud_available:
            return  # Don't try if known to be down

        try:
            await self.call_agent(
                target=self.cloud_ingestion,
                task_type="ingest_reading",
                payload={"reading": reading},
                timeout=5.0
            )

            # Success - remove from buffer
            sensor_id = reading["sensor_id"]
            if reading in self._sensor_buffer[sensor_id]:
                self._sensor_buffer[sensor_id].remove(reading)

        except AgentCallError:
            # Failed, reading stays in buffer
            self._cloud_available = False

    async def _periodic_cloud_sync(self):
        """
        Periodic cloud sync (background task).

        Attempts every 5 minutes when cloud available,
        every 30 seconds when trying to reconnect.
        """
        while True:
            try:
                await self.sync_to_cloud()

                # Successful sync or no data
                interval = 300  # 5 minutes

            except Exception as e:
                self.logger.error(f"Periodic sync failed: {e}")
                interval = 30  # Retry in 30 seconds

            await asyncio.sleep(interval)


async def main():
    agent = EdgeGatewayAgent.from_config("config/edge_gateway.yaml")

    # Start periodic sync
    asyncio.create_task(agent._periodic_cloud_sync())

    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### OTA Update Agent (Cloud)

```python
# ota_update_agent.py
"""
OTA (Over-The-Air) Update Agent - Secure firmware distribution.

Security:
- Firmware signed with private key
- Devices verify signature before installing
- SPIFFE identity ensures only authorized devices
"""

import asyncio
from typing import Dict, Any
import hashlib
import base64

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart


class OTAUpdateAgent(SecureAgent):
    """
    Distributes firmware updates to edge devices.

    Security model:
    1. Firmware signed with private key (offline)
    2. Devices verify signature with public key
    3. Only authorized devices (SPIFFE ID) can download
    4. Version tracking prevents downgrades
    """

    @capability("check_update")
    async def check_update(
        self,
        device_id: str,
        current_version: str,
        device_type: str
    ) -> TaskResult:
        """
        Check if firmware update available.

        Called by edge devices periodically.
        """
        # Get caller's SPIFFE ID
        caller_id = self.context.caller_spiffe_id

        # Verify device is authorized
        if not self._is_authorized_device(caller_id, device_id):
            return TaskResult(
                status="failed",
                error="Device not authorized for updates"
            )

        # Check for available update
        latest = await self._get_latest_firmware(device_type)

        if latest["version"] > current_version:
            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={
                        "update_available": True,
                        "version": latest["version"],
                        "size_bytes": latest["size"],
                        "release_notes": latest["notes"],
                        "signature": latest["signature"]
                    })]
                )]
            )
        else:
            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={"update_available": False})]
                )]
            )

    @capability("download_firmware")
    async def download_firmware(
        self,
        device_id: str,
        version: str,
        device_type: str
    ) -> TaskResult:
        """
        Download firmware update.

        Returns firmware binary with cryptographic signature.
        Device MUST verify signature before installing.
        """
        caller_id = self.context.caller_spiffe_id

        if not self._is_authorized_device(caller_id, device_id):
            return TaskResult(
                status="failed",
                error="Device not authorized"
            )

        firmware = await self._get_firmware(device_type, version)

        if not firmware:
            return TaskResult(
                status="failed",
                error=f"Firmware {version} not found"
            )

        # Log firmware download for audit
        self.logger.info(
            "Firmware downloaded",
            extra={
                "device_id": device_id,
                "device_spiffe_id": caller_id,
                "version": version,
                "size": len(firmware["binary"])
            }
        )

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "version": version,
                    "binary": base64.b64encode(firmware["binary"]).decode(),
                    "signature": firmware["signature"],
                    "public_key": firmware["public_key"]
                })]
            )]
        )

    def _is_authorized_device(self, spiffe_id: str, device_id: str) -> bool:
        """
        Verify device is authorized for updates.

        Checks:
        - SPIFFE ID matches expected pattern
        - Device ID registered
        - Device not revoked
        """
        # Device must be in correct trust domain
        if not spiffe_id.startswith("spiffe://building-1.smart.local/agent/"):
            return False

        # In production, check device registry
        return True

    async def _get_latest_firmware(self, device_type: str) -> Dict[str, Any]:
        """Get latest firmware version."""
        # In production, query firmware database
        return {
            "version": "2.1.0",
            "size": 524288,  # 512KB
            "notes": "Security fixes and performance improvements",
            "signature": "..."
        }

    async def _get_firmware(
        self,
        device_type: str,
        version: str
    ) -> Dict[str, Any]:
        """Get firmware binary."""
        # In production, fetch from secure storage
        firmware_data = b"FIRMWARE_BINARY_DATA..."

        # Calculate signature (in production, use HSM)
        signature = self._sign_firmware(firmware_data)

        return {
            "version": version,
            "binary": firmware_data,
            "signature": signature,
            "public_key": "PUBLIC_KEY_PEM"
        }

    def _sign_firmware(self, firmware: bytes) -> str:
        """
        Sign firmware with private key.

        In production:
        - Private key stored in HSM
        - Use RSA or Ed25519
        - Include timestamp
        """
        # Simplified: hash only
        return hashlib.sha256(firmware).hexdigest()


async def main():
    agent = OTAUpdateAgent.from_config("config/ota_update.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration for Constrained Devices

```yaml
# config/hvac_sensor.yaml (Edge Device)
agent:
  name: "hvac-sensor-001"
  trust_domain: "building-1.smart.local"
  description: "HVAC sensor on floor 2"

  capabilities:
    - name: "read_sensors"
      description: "Read temperature, humidity, fan status"
    - name: "sync_buffered"
      description: "Sync buffered readings"

identity:
  provider: "spiffe"
  # Lightweight agent for constrained devices
  spiffe_endpoint: "unix:///var/run/spire/agent.sock"

  # Resource-constrained configuration
  lightweight: true
  svid_cache_size: 1  # Minimal cache
  bundle_refresh_interval: 3600  # 1 hour

authorization:
  provider: "opa"
  opa_endpoint: "http://edge-gateway:8181"
  # Cache policy decisions to reduce network calls
  policy_cache_ttl: 300  # 5 minutes

transport:
  tls_min_version: "1.3"
  # Optimize for low-power devices
  connection_reuse: true
  keepalive_interval: 60

server:
  host: "0.0.0.0"
  port: 8443
  # Lightweight HTTP server
  max_connections: 5
  request_timeout: 30

observability:
  metrics:
    enabled: false  # Disable to save resources
  logging:
    level: "WARNING"  # Minimal logging
    # Log to syslog instead of files
    destination: "syslog"
```

## SPIRE Configuration for IoT

### Device Attestation with TPM

```hcl
# spire/agent.conf (Edge Device)
agent {
    data_dir = "/var/lib/spire"
    log_level = "INFO"
    server_address = "edge-gateway"
    server_port = "8081"
    socket_path = "/var/run/spire/agent.sock"
    trust_domain = "building-1.smart.local"
}

plugins {
    # TPM-based attestation for hardware identity
    NodeAttestor "tpm" {
        plugin_data {
            tpm_path = "/dev/tpm0"
        }
    }

    KeyManager "memory" {
        plugin_data {}
    }

    # Lightweight workload attestation
    WorkloadAttestor "unix" {
        plugin_data {}
    }
}
```

## Running the Example

### Setup Edge Environment

```bash
# On edge gateway (Raspberry Pi, etc.)
./scripts/setup-edge-gateway.sh

# Register edge gateway with cloud SPIRE
docker exec cloud-spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://smart-building.cloud/gateway/building-1 \
    -parentID spiffe://smart-building.cloud/node/federated \
    -selector tpm:manufacturer:STMicro

# On sensor device
./scripts/setup-sensor-device.sh HVAC-SENSOR-001
```

### Test Offline Operation

```bash
# Disconnect network
sudo ifconfig eth0 down

# Sensor continues buffering
curl http://localhost:8443/metrics

# Reconnect network
sudo ifconfig eth0 up

# Gateway auto-syncs buffered data
# Check logs for sync confirmation
journalctl -u edge-gateway -f
```

### OTA Update

```bash
# Device checks for updates
agentweave call \
    --target spiffe://smart-building.cloud/agent/ota \
    --capability check_update \
    --data '{
        "device_id": "HVAC-SENSOR-001",
        "current_version": "2.0.0",
        "device_type": "hvac_sensor"
    }'
```

## Key Takeaways

### Lightweight SPIFFE for IoT

Traditional SPIFFE agents may be too heavy for constrained devices:

```
Standard Agent: ~100MB RAM
Lightweight Agent: ~20MB RAM  ← Optimized for IoT
```

### Store-and-Forward

Devices buffer data when offline:

```python
# Buffer locally
self._buffer.append(reading)

# Sync when connected
await self.sync_to_cloud()
```

### Device Attestation

TPM-based hardware identity:

```
Device → TPM Attestation → SPIRE → SVID → mTLS
```

### Secure OTA Updates

Cryptographically signed firmware:

```
Firmware → Sign (HSM) → Distribute → Verify (Device) → Install
```

## Resource Comparison

| Aspect | Cloud Agent | Edge Gateway | Sensor Device |
|--------|-------------|--------------|---------------|
| **RAM** | 512MB+ | 256MB | 64MB |
| **CPU** | 2+ cores | 1 core | 200MHz ARM |
| **Storage** | 10GB+ | 1GB | 128MB |
| **Network** | Always on | Intermittent | Offline-capable |
| **SPIRE Agent** | Full | Full | Lightweight |
| **OPA** | Full | Embedded | Cache only |

## Production Considerations

### Power Efficiency

- **SVID caching**: Reduce crypto operations
- **Connection reuse**: Minimize TLS handshakes
- **Batched uploads**: Reduce radio usage
- **Sleep modes**: Compatible with device sleep

### Scalability

- **Edge gateway**: Supports 100+ sensor devices
- **Cloud platform**: Handles millions of devices
- **Hierarchical trust**: Building → Campus → Corporate

### Security

- **Hardware root of trust**: TPM attestation
- **Secure boot**: Verified firmware chain
- **Remote attestation**: Prove device is genuine
- **Revocation**: Disable compromised devices

---

**Complete Code**: [GitHub Repository](https://github.com/agentweave/examples/tree/main/real-world/iot-edge)
