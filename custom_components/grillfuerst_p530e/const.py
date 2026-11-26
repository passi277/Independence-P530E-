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

# Temperatures (°C). 101-105 follow the DP pattern but are not yet confirmed with a hot grill.
DP_CHAMBER_TEMP = "101"  # built-in sensor below the grate (assumed)
DP_PROBE_TEMPS = ["102", "103", "104", "105"]  # probes F1-F4 (F1 verified)
DP_PROBE_TARGETS = ["106", "107", "108", "109"]  # probe target temperatures F1-F4 (F1-F3 verified)
PROBE_TARGET_MIN = 0
PROBE_TARGET_MAX = 200

# Doneness presets of the app (option key -> probe target °C). The grill only stores the number.
PROBE_PRESETS: dict[str, int] = {
    "beef_well_done": 66,
    "beef_medium_well": 61,
    "beef_medium": 56,
    "beef_medium_rare": 53,
    "beef_rare": 50,
    "veal_well_done": 74,
    "veal_medium_well": 71,
    "veal_medium": 66,
    "veal_medium_rare": 63,
    "lamb_well_done": 68,
    "lamb_medium_well": 66,
    "lamb_medium": 62,
    "lamb_medium_rare": 56,
    "lamb_rare": 50,
    "pork_well_done": 70,
    "pork_medium_well": 66,
    "pork_medium": 62,
    "burger": 74,
    "chicken": 78,
    "turkey": 78,
    "fish": 60,
}

# Grill programme (the grill drives its gas burners from these)
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
TIMER_STOPPED = 0
TIMER_PAUSED = 1
TIMER_RUNNING = 2
TIMER_MAX_MINUTES = 23 * 60 + 59  # app picker: hours + minutes

# Lighting
DP_KNOB_LIGHT = "116"  # knob light mode, see KNOB_LIGHT_MODES
KNOB_LIGHT_ON = 3  # "individual" = fixed colour from DP 118
KNOB_LIGHT_OFF = 0
KNOB_LIGHT_MODES = {
    0: "off",
    1: "random",
    2: "temperature",
    3: "individual",
    4: "magic",
}
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
DP_SOUND = "130"  # grill buzzer on/off
