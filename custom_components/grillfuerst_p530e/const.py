"""Constants for the Grillfürst Independence P530E integration."""

from __future__ import annotations

DOMAIN = "grillfuerst_p530e"

CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_PROTOCOL_VERSION = "protocol_version"

DEFAULT_PROTOCOL_VERSION = "3.5"
PROTOCOL_VERSIONS = ["3.3", "3.4", "3.5"]

SCAN_INTERVAL_SECONDS = 15

MANUFACTURER = "Grillfürst"
MODEL = "Independence P530E"

# Verified data points (DPs). All weights are sent in 0.1 kg steps.
DP_GAS_REMAINING = "119"  # scale weight - tare, clamped at 0
DP_GAS_LEVEL_STEP = "120"  # "1" (empty) ... "7" (full), used by the app graphic
DP_SCALE_WEIGHT = "121"  # gross weight on the scale
DP_CYLINDER_SIZE = "122"  # configured cylinder size
DP_CYLINDER_TARE = "123"  # configured empty-cylinder weight (min 4.0 kg)

WEIGHT_SCALE = 10
