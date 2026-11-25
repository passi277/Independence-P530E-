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

# Grill programme (read-only on purpose: the grill drives its gas burners from these)
DP_TARGET_DIRECT = "110"  # target temperature "Direktes Grillen", °C
DP_TARGET_INDIRECT = "111"  # target temperature "Indirektes Grillen", °C
DP_TARGET_LOW_SLOW = "112"  # target temperature "Low & Slow", °C
DP_GRILL_MODE = "114"
GRILL_MODES = {
    0: "direct",
    1: "stage",
    2: "free",
    3: "low_slow",
    4: "indirect",
}

# Kitchen timer of the app
DP_TIMER_REMAINING = "124"  # remaining minutes (rounded up)
DP_TIMER_STATE = "126"
TIMER_STATES = {
    0: "stopped",
    1: "paused",
    2: "running",
    3: "idle",  # seen after power-up, before the timer was used
}

# Lighting
DP_KNOB_LIGHT = "116"  # 0 = off, 3 = on (the app briefly reports 1 while switching on)
KNOB_LIGHT_ON = 3
KNOB_LIGHT_OFF = 0
DP_KNOB_COLOR = "118"
KNOB_COLORS = [
    "red",
    "orange",
    "yellow",
    "green",
    "light_green",
    "deep_blue",
    "purple",
    "pink",
]
DP_LOGO_LIGHT = "128"
DP_CHAMBER_LIGHT = "129"
