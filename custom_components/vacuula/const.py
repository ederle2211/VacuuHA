from datetime import timedelta

DOMAIN = "vacuula"

CONF_HOST = "host"
CONF_PORT = "port"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

ZEROCONF_SERVICE_TYPE = "_vacuula._tcp.local."

API_ROBOTS_PATH = "/api/robots"