# VARIABLES TO CHANGE FOR STATION, COUNTRIES, ...
# SERVER
import pandas as pd

SERVER_DASH_IP: str = "127.0.0.1"
SERVER_DASH_PORT: int = 8050
SERVER_DASH_PROTOCOL: str = "http://"
DEBUG: bool = True

# AREA AND STATIONS
NAME_AREA: str = "UB (France)"
LAT_MAP: int = 48
LON_MAP: int = 107
ZOOM_MAP: float = 7

LIST_NAME_STA: list = ['SEMM', 'ARTM', 'UGDM', 'ALFM']
LIST_LAT_STA: list = ['47.561488', '47.926953', '47.638031', '48.00351']
LIST_LON_STA: list = ['106.977964', '107.270435', '107.400533', '106.771986']


# GRAFANA LINK
GRAFANA_DOMAIN: str = "https://monalisa.jeremec.fr/"
GRAFANA_DASHBOARD: str = 'd/pX7YlZH7k/ping-and-cpu?orgId=1'
GRAFANA_REFRESH: str = '10s'
GRAFANA_T_FROM: str = 'now-6h'
GRAFANA_T_TO: str = 'now'

GRAFANA_LINK: str = GRAFANA_DOMAIN + GRAFANA_DASHBOARD + '&refresh=' + \
               GRAFANA_REFRESH + '&from=' + GRAFANA_T_FROM + '&to=' + GRAFANA_T_TO

# UPDATE VAR
UPDATE_TIME_GRAPH: int = 15000  # in ms
UPDATE_DATA: int = 30000
UPDATE_TIME_STATES: int = 100000  # in ms
UPDATE_TIME_ALARMS: int = 60000  # in ms

# STYLE
COLOR_TIME_GRAPH: str = "#ffe476"
TIME_DELTA: pd.Timedelta = pd.Timedelta(60, unit='sec')

# DATA BUFFER
BUFFER_DIR: str = 'data'

# HAT ORACLE CLIENT
CLIENT_ORACLE: str = r'C:\Oracle\instantclient_11_2'
HOST_ORACLE: str = '192.168.1.76'
PORT_ORACLE: str = '1521'
USER_ORACLE: str = 'hat'
PWD_ORACLE: str = 'hat'

# SEISMIC CONFIG
XML_INVENTORY: str = ""