"""Constants for the WWIVD integration."""

DOMAIN = "wwivd"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_ENABLE_INSTANCES = "enable_instances"
CONF_ENABLE_BLOCKING = "enable_blocking"
CONF_ENABLE_SYSOP = "enable_sysop"
CONF_ENABLE_LASTON = "enable_laston"
CONF_MODEM_ENABLED = "modem_enabled"
CONF_MODEM_HOST = "modem_host"
CONF_MODEM_PORT = "modem_port"
CONF_MODEM_REFRESH_INTERVAL = "modem_refresh_interval"

# Default values
DEFAULT_PORT = 8080
DEFAULT_REFRESH_INTERVAL = 30
DEFAULT_MODEM_PORT = 8080
DEFAULT_MODEM_REFRESH_INTERVAL = 30
MIN_REFRESH_INTERVAL = 5

# WWIVD API paths
ENDPOINT_INSTANCES = "/instances"
ENDPOINT_BLOCKING = "/blocking"
ENDPOINT_SYSOP = "/sysop"
ENDPOINT_LASTON = "/laston"
ENDPOINT_MODEM_STATUS = "/modem_status"

# Sensor keys (used in coordinator data dict)
SENSOR_USED_INSTANCES = "used_instances"
SENSOR_AUTO_BLOCKED_COUNT = "auto_blocked_count"
SENSOR_CALLS_TODAY = "calls_today"
SENSOR_EMAIL_TODAY = "email_today"
SENSOR_FEEDBACK_TODAY = "feedback_today"
SENSOR_FEEDBACK_WAITING = "feedback_waiting"
SENSOR_LASTON_COUNT = "laston_count"
SENSOR_LASTON = "laston"

# Modem Manager sensor key
SENSOR_MODEM_STATUS = "modem_status"

# Attribute names for sensors
ATTR_LAST_UPDATED = "last_updated"
