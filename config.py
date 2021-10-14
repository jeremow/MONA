# VARIABLES TO CHANGE FOR STATION, COUNTRIES, ...
# SERVER
import pandas as pd

SERVER_DASH_IP: str = "127.0.0.1"
SERVER_DASH_PORT: int = 8050
SERVER_DASH_PROTOCOL: str = "http://"
DEBUG: bool = True

# AREA AND STATIONS
NAME_AREA: str = "Mongolia"
LAT_MAP: int = 47
LON_MAP: int = 104
ZOOM_MAP: float = 4.5

LIST_NAME_STA: list = ['SB1M', 'SB2M', 'SB3M', 'SB4M', 'SB5M']
LIST_LAT_STA: list = ['47.8630', '47.9630', '47.6630', '47.5630', '47.9830']
LIST_LON_STA: list = ['106.4039', '107.4039', '108.4039', '109.4039', '110.4039']


# GRAFANA LINK
GRAFANA_DOMAIN: str = "https://monalisa.jeremec.fr/"
GRAFANA_DASHBOARD: str = 'd/pX7YlZH7k/ping-and-cpu?orgId=1'
GRAFANA_REFRESH: str = '10s'
GRAFANA_T_FROM: str = 'now-6h'
GRAFANA_T_TO: str = 'now'

GRAFANA_LINK: str = GRAFANA_DOMAIN + GRAFANA_DASHBOARD + '&refresh=' + \
               GRAFANA_REFRESH + '&from=' + GRAFANA_T_FROM + '&to=' + GRAFANA_T_TO

# UPDATE VAR
UPDATE_TIME_GRAPH: int = 30000  # in ms
UPDATE_TIME_STATES: int = 30000  # in ms
UPDATE_TIME_ALARMS: int = 30000  # in ms

# STYLE
COLOR_TIME_GRAPH: str = "#ffe476"
TIME_DELTA: pd.Timedelta = pd.Timedelta(60, unit='sec')

# DATA BUFFER
BUFFER_DIR: str = 'data'
