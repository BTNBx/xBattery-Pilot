"""Constantes do xBattery Pilot."""

DOMAIN = "xbattery_pilot"

CONF_SOC_SENSOR = "soc_sensor"
CONF_LOAD_SENSOR = "load_sensor"
CONF_FORECAST_ENTRY = "forecast_entry"
CONF_CAPACITY = "capacity_wh"
CONF_MIN_SOC = "min_soc"
CONF_CHARGE_START = "charge_start"
CONF_CHARGE_END = "charge_end"
CONF_CHARGE_POWER = "charge_power_w"
CONF_PV_SCALING = "pv_scaling"
CONF_PRICE_VAZIO = "price_vazio"
CONF_PRICE_CHEIAS = "price_cheias"
CONF_PRICE_PONTA = "price_ponta"

DEFAULTS = {
    CONF_SOC_SENSOR: "sensor.deye_battery",
    CONF_LOAD_SENSOR: "sensor.deye_load_l1_power",
    CONF_CAPACITY: 10240,
    CONF_MIN_SOC: 20,
    CONF_CHARGE_START: "04:00:00",
    CONF_CHARGE_END: "08:00:00",
    CONF_CHARGE_POWER: 2000,
    CONF_PV_SCALING: 1.0,
    CONF_PRICE_VAZIO: 0.1082,
    CONF_PRICE_CHEIAS: 0.1681,
    CONF_PRICE_PONTA: 0.2584,
}

FORECAST_DOMAINS = ("forecast_solar", "solcast_solar", "open_meteo_solar_forecast")

EFF_CHARGE = 0.95
EFF_DISCHARGE = 0.95
TARGET_STEP = 5
UPDATE_MINUTES = 15
DEFAULT_LOAD_W = 400
LOAD_FACTOR_MIN = 0.8
LOAD_FACTOR_MAX = 1.3
CALIBRATION_DAYS = 7
