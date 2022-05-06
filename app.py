# -*- coding: utf-8 -*-
#
# # Run this app with `python app.py` and
# # visit http://127.0.0.1:8050/ in your web browser.
#
# MONA-LISA APP
# Created in Mongolia in 2021 by Jeremy Hraman
# Based on Dash with Plotly (dashboard of Python)
#
# Separated on different files:
# - app.py with the main interface and algorithm
# - retrieve_data.py for the real-time data from SeedLink server
# - state_health.py for the Oracle Client of the HAT database of the IAG

import base64
import gc
import os
import psutil
import webbrowser
import logging as log

import dash
from dash.dependencies import Input, Output, State, MATCH
from dash import dcc
from dash import html

import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from obspy import read
import pandas as pd

# style and config
from assets.style import *
# from config import *
from state_health import *
from utils import get_network_list, delete_residual_data
from bs4 import BeautifulSoup as BS

# sidebar connection
from connection import *
from retrieve_data import EasySLC, SLThread
from subprocess import Popen

# for alarms
import simpleaudio as sa
from simpleaudio._simpleaudio import SimpleaudioError
# from alarms import create_alarm_from_HAT


app = dash.Dash(__name__, suppress_callback_exceptions=True, update_title="MONA-LISA - Updating Data",
                external_stylesheets=[dbc.themes.CYBORG])

# app.css.config.serve_locally = True
# app.scripts.config.serve_locally = True

app.title = 'MONA-LISA'
server = app.server
# global variables which are useful, dash will say remove these variables, I say let them exist, else I will have
# problems between some callbacks.

try:
    del time_graphs_names, time_graphs, fig_list, network_list, network_list_values, interval_time_graphs, client, \
        client_oracle_xat, client_oracle_soh
except NameError:
    pass

time_graphs_names = []
time_graphs = []
fig_list = []
network_list = []
network_list_values = []
interval_time_graphs = []
client = None
client_thread = None
client_oracle_xat = HatOracleClient()
client_oracle_soh = SOHOracleClient()

# Remove all the data residual files if they exist
delete_residual_data()

# logo file and decoding to display in browser
logo_filename = 'assets/logo.jpg'
encoded_logo = base64.b64encode(open(logo_filename, 'rb').read())


# SIDEBAR TOP: LOGO, TITLE, CONNECTION AND CHOICE OF STATIONS FOR TIME-SERIE GRAPHS
sidebar_top = html.Div(
    [
        # Picture and title
        html.H2([html.Img(src='data:image/jpg;base64,{}'.format(encoded_logo.decode()), height=80), " MONA-LISA"], className="display-5"),
        html.P(
            [
                "Monitoring App of the IAG - " + NAME_AREA
            ],
            className="lead"
        ),
        # Button to open Grafana, Button to deactivate the alarm sound
        dcc.Link(dbc.Button(children='Open Grafana', target="_blank", id='btn-grafana', n_clicks=0, className="mr-1",
                 style={'display': 'inline-block', 'width': '100%'}), href=GRAFANA_LINK, target="_blank"),
        html.Br(), html.Br(),
        dbc.Button('Alarm sound: ON', id='btn-alarm-sound', n_clicks=0, color='success', className='me-1',
                   style={'display': 'inline-block', 'width': '100%'}),
        html.Br(), html.Br(),
        html.Div(id="hidden-div", style={"display": "none"}),
        # Different tabs to include further options, only server is available for the moment
        dbc.Tabs(id="tabs-connection",
                 children=[
                     dbc.Tab(label='Server', tab_id='server'),
                     dbc.Tab(label='SDS Folder', tab_id='folder', disabled=False),
                     dbc.Tab(label='File', tab_id='file', disabled=True),
                 ],
                 active_tab='server'),
        html.Div(id='tabs-connection-inline'),  # TABS FOR SERVER, FILE, ...

    ],

    # style=CHILD,
)


@app.callback(Output('btn-alarm-sound', 'color'),
              Output('btn-alarm-sound', 'children'),
              Input('btn-alarm-sound', 'n_clicks'),
              prevent_inital_call=True)
def change_btn(n_clicks):
    """
    Callback to turn off the alarm, and change the appearance of the button
    :param n_clicks:
    :return:
    """
    if n_clicks % 2 == 0:
        return 'danger', 'Alarm sound: OFF'
    else:
        return 'success', 'Alarm sound: ON'

# INSIDE OF THE TABS


@app.callback(Output('tabs-connection-inline', 'children'),
              Input('tabs-connection', 'active_tab'))
def render_connection(tab):
    """
    Callback of the tab for the connection. If server tab is active, you can access the network list for the time graphs
    and also to see if the connection is active
    :param tab:
    :return:
    """
    if tab == 'server':
        return [
            html.Div(dbc.Input(id='input-on-submit', placeholder='URL:port', type="text", className="mb-1"),
                     style={'display': 'inline-block', 'width': '69%', 'textarea:color': 'white'}),
            html.Div(children=' ', style={'display': 'inline-block', 'width': '2%'}),
            html.Div(dbc.Button("Connect", id="connect-server-button", className="mr-1"),
                     style={'display': 'inline-block', 'width': '29%'}),
            html.Br(),
            dcc.Interval(
                id='interval-time-graph',
                interval=UPDATE_TIME_GRAPH,  # in milliseconds
                n_intervals=0,
                disabled=True),
            dcc.Interval(
                id='interval-data',
                interval=UPDATE_DATA,  # in milliseconds
                n_intervals=0,
                disabled=True),
            dcc.Interval(
                id='interval-states',
                interval=UPDATE_TIME_STATES,  # in milliseconds
                n_intervals=0),
            dcc.Interval(
                id='interval-alarms',
                interval=UPDATE_TIME_ALARMS,  # in milliseconds
                n_intervals=0),
            html.Br(),
            html.H4('Time graphs stations'),
            html.Div(id='container-button-basic',
                     children=[
                             dcc.Dropdown(id='network-list-active',
                                             placeholder='Select stations for time graphs',
                                             options=network_list, multi=True, style={'color': 'black'}),
                             html.P('Connection not active', style={'color': 'red'})
                             ]
                     ),
            dbc.RadioItems(
                id='realtime-radiobox',
                options=[
                    {'label': 'Real-Time', 'value': 'realtime'},
                    {'label': 'Data Retrieval', 'value': 'retrieval', 'disabled': True}
                ],
                value='realtime',
                inline=True
            ),
            html.Div(id='date-picker', children=[]),
            html.Br()
            ]
    elif tab == 'folder':
        return [
            html.Div(dbc.Input(id='input-on-submit', placeholder='/path/to/SDS', type="text", className="mb-1"),
                     style={'display': 'inline-block', 'width': '69%', 'textarea:color': 'white'}),
            html.Div(children=' ', style={'display': 'inline-block', 'width': '2%'}),
            html.Div(dbc.Button("Connect", id="connect-server-button", className="mr-1"),
                     style={'display': 'inline-block', 'width': '29%'}),
            html.Br(),
            dcc.Interval(
                id='interval-time-graph',
                interval=UPDATE_TIME_GRAPH,  # in milliseconds
                n_intervals=0,
                disabled=True),
            dcc.Interval(
                id='interval-data',
                interval=UPDATE_DATA,  # in milliseconds
                n_intervals=0,
                disabled=True),
            dcc.Interval(
                id='interval-states',
                interval=UPDATE_TIME_STATES,  # in milliseconds
                n_intervals=0),
            dcc.Interval(
                id='interval-alarms',
                interval=UPDATE_TIME_ALARMS,  # in milliseconds
                n_intervals=0),
            html.Br(),

            html.H4('Time graphs stations'),
            html.Div(id='container-button-basic',
                     children=[
                             dcc.Dropdown(id='network-list-active',
                                             placeholder='Select stations for time graphs',
                                             options=network_list, multi=True, style={'color': 'black'}),
                             html.P('Folder not active', style={'color': 'red'})
                             ]
                     ),
            dbc.RadioItems(
                id='realtime-radiobox',
                options=[
                    {'label': 'Real-Time', 'value': 'realtime'},
                    {'label': 'Data Retrieval', 'value': 'retrieval', 'disabled': True}
                ],
                value='realtime',
                inline=True
            ),
            html.Div(id='date-picker', children=[]),
            html.Br()
            ]
    # elif tab == 'file':
    #     return html.Div([
    #         html.H6('Connection through file'),
    #         dcc.Upload(
    #             id='upload-data',
    #             children=html.Div([
    #                 'Drag and Drop or ',
    #                 html.A('Select seismic file')
    #             ]),
    #             style={
    #                 'width': '90%',
    #                 'height': '30px',
    #                 'lineHeight': '30px',
    #                 'borderWidth': '1px',
    #                 'borderStyle': 'dashed',
    #                 'borderRadius': '2px',
    #                 'textAlign': 'center',
    #
    #             },
    #             # Allow multiple files to be uploaded
    #             multiple=True
    #         )
    #     ])

# CONNECTION TO THE SERVER TAB


@app.callback(Output('date-picker', 'children'),
              Input('realtime-radiobox', 'value'),
              Input('tabs-connection', 'active_tab'))
def display_data_retrieval(value, tab):
    global client
    global client_thread
    if value == 'realtime':
        if tab == 'server':
            delete_residual_data(delete_streams=False)
            try:
                client.data_retrieval = False
                client_thread.close()
                client_thread = SLThread('Client SL Realtime', client)
                client_thread.start()
            except AttributeError:
                pass
        return []
    else:
        if tab == 'server':
            try:
                client.data_retrieval = True
                client_thread.close()
            except AttributeError:
                pass

        return [dcc.DatePickerSingle(id='date-picker-dcc', date=UTCDateTime().date,
                                     display_format='YYYY/MM/DD', number_of_months_shown=2,
                                     style={'display': 'inline-block', 'width': '40%'}),
                dbc.Input(id="input-hour", type="number", placeholder="HH", min=0, max=23, step=1,
                          style={'display': 'inline-block', 'width': '20%'}),
                dbc.Input(id="input-min", type="number", placeholder="MM", min=0, max=59, step=1,
                          style={'display': 'inline-block', 'width': '20%'}),
                dbc.Input(id="input-sec", type="number", placeholder="SS", min=0, max=59, step=1,
                          style={'display': 'inline-block', 'width': '20%'}),
                html.Br(),
                'Duration: ',
                dbc.Input(id="input-period", type="number", value=1, min=1, max=59, step=1,
                          style={'display': 'inline-block', 'width': "20%"}),
                dbc.Select(id='select-period',
                           options=[
                               {"label": "day", "value": "day"},
                               {"label": "hour", "value": "hour"},
                               {"label": "min", "value": "min"},
                               {"label": "sec", "value": "sec"},
                           ],
                           value='hour',
                           style={'display': 'inline-block', 'width':"20%"}),
                '  ',
                dbc.Button("Retrieve Data", id='retrieve-data-btn', color="success",
                           className="mb-1", n_clicks=0, style={'display': 'inline-block'}),
                html.Br()]


@app.callback(
    Output('retrieve-data-btn', 'n_clicks'),
    Input('retrieve-data-btn', 'n_clicks'),
    Input('date-picker-dcc', 'date'),
    Input('input-hour', 'value'),
    Input('input-min', 'value'),
    Input('input-sec', 'value'),
    Input('input-period', 'value'),
    Input('select-period', 'value'),
    Input('tabs-connection', 'active_tab'),
    prevent_initial_call=True
)
def get_data_from_retrieval(n_clicks, date, hour, min, sec, period_value, period, tab):
    if tab == 'server':
        global client
        global client_thread
        if n_clicks > 0:
            delete_residual_data(delete_streams=False)
            try:
                date = date.split('-')
                year = date[0]
                month = date[1]
                day = date[2]
                begin_time = f'{year},{month},{day},{hour},{min},{sec}'
                client.begin_time = begin_time
                if period == 'day':
                    factor = 86400
                elif period == 'hour':
                    factor = 3600
                elif period == 'min':
                    factor = 60
                else:
                    factor = 1
                duration = factor * period_value
                end_time = (UTCDateTime(begin_time) + duration).format_seedlink()
                client.end_time = end_time
                client_thread = SLThread('Client SL Data Retrieval', client)
                client_thread.start()
            except AttributeError:
                print('Client not initialised')

    return 0


@app.callback(
    Output('container-button-basic', 'children'),
    Input('connect-server-button', 'n_clicks'),
    State('input-on-submit', 'value'),
    Input('tabs-connection', 'active_tab'),
)
def connect_update_server(n_clicks, value, tab):
    """
    Connect to the server with the EasySLC class. This is a Seedlink client which waits for the user of MONA-LISA to
    choose some stations. When one is selected, it will start to retrieve the data from the server.
    :param n_clicks:
    :param value:
    :return:
    """

    global client
    global client_thread
    global network_list
    global network_list_values
    network_list = []
    network_list_values = []

    if tab == 'server':
        if value is not None:
            try:
                pass
                client = EasySLC(value, network_list, network_list_values)
                # client = SeedLinkClient(value, network_list, network_list_values)
            except SeedLinkException:
                client.connected = 0

            if client.connected == 1:
                try:
                    client_thread.close()
                except AttributeError:
                    pass
                if client.data_retrieval is False:
                    client_thread = SLThread('Client SL Realtime', client)
                    client_thread.start()
                return [
                    dcc.Dropdown(id='network-list-active',
                                 placeholder='Select stations for time graphs',
                                 options=network_list, multi=True, style={'color': 'black'}),
                    html.P('Connection active to {}'.format(value), style={'color': 'green'}),
                    dcc.Interval(
                        id='interval-data',
                        interval=UPDATE_DATA,  # in milliseconds
                        n_intervals=0,
                        disabled=False),
                ]
            elif client.connected == -1:
                return [
                    dcc.Dropdown(id='network-list-active',
                                 placeholder='Select stations for time graphs',
                                 options=network_list, multi=True, style={'color': 'black'}),
                    html.P('Config file of server missing.', style={'color': 'red'}),
                ]
            else:
                return [
                    dcc.Dropdown(id='network-list-active',
                                 placeholder='Select stations for time graphs',
                                 options=network_list, multi=True, style={'color': 'black'}),
                    html.P('Verify the config file, no station found.', style={'color': 'red'}),
                ]
        else:
            return [
                dcc.Dropdown(id='network-list-active',
                             placeholder='Select stations for time graphs',
                             options=[], multi=True, style={'color': 'black'}),
                html.P('Connection not active', style={'color': 'red'}),
            ]
    elif tab == 'folder':
        if value is not None and os.path.isdir(value):
            connected = get_network_list('folder', network_list, network_list_values, folder_file='stations.xml')
            if connected is not None:
                if connected == 1:
                    return [
                            dcc.Dropdown(id='network-list-active',
                                         placeholder='Select stations for time graphs',
                                         options=network_list, multi=True, style={'color': 'black'}),
                            html.P('Connection active to {}'.format(value), style={'color': 'green'}),
                            dcc.Interval(
                                id='interval-data',
                                interval=UPDATE_DATA,  # in milliseconds
                                n_intervals=0,
                                disabled=False)
                        ]
                elif connected == -1:
                    return [
                        dcc.Dropdown(id='network-list-active',
                                     placeholder='Select stations for time graphs',
                                     options=network_list, multi=True, style={'color': 'black'}),
                        html.P('Config file of folder missing.', style={'color': 'red'}),
                    ]
                else:
                    return [
                        dcc.Dropdown(id='network-list-active',
                                     placeholder='Select stations for time graphs',
                                     options=network_list, multi=True, style={'color': 'black'}),
                        html.P('Verify the config file, no station found.', style={'color': 'red'}),
                    ]
        else:
            return [
                dcc.Dropdown(id='network-list-active',
                             placeholder='Select stations for time graphs',
                             options=[], multi=True, style={'color': 'black'}),
                html.P('Connection not active', style={'color': 'red'}),
            ]



# SIDEBAR BOTTOM: HEALTH STATES


sidebar_bottom = html.Div(
    [
        html.H4('Health states'),
        html.Div(id='station-list-div', children=dcc.Dropdown(id='station-list-one-choice',
                                                              placeholder='Select a station', options=network_list,
                                                              multi=False, style={'color': 'black'})),

        html.Div(id='health-states',
                 children=dbc.Table()
                 )

    ],
    # style=CHILD,
)

# HEALTH STATE FUNCTION TO RECOVER THE STATION FROM THE SERVER AND DISPLAY IT INTO A GOOD WAY


@app.callback(Output('station-list-div', 'children'),
              Input('input-on-submit', 'n_clicks'),
              prevent_initial_call=True)
def update_list_station(n_clicks):
    """
    Callback for the list of stations with the States of Health (HAT Oracle server). Made especially for Mongolia.
    :param n_clicks:
    :return Dropdown to select the stations available:
    """
    global client_oracle_xat
    global client_oracle_soh
    stations = []

    for sta in client_oracle_xat.stations:
        stations.append({'label': sta, 'value': sta})
    for sta in client_oracle_soh.stations:
        stations.append({'label': sta, 'value': sta})


    return [dcc.Dropdown(id='station-list-one-choice', placeholder='Select a station',
                         options=stations, multi=False, style={'color': 'black'})]


@app.callback(Output('health-states', 'children'),
              Input('station-list-one-choice', 'value'),
              Input('interval-states', 'n_intervals'),
              State('tabs-connection', 'active_tab'),
              prevent_initial_call=True)
def update_states(station_name, n_intervals, tab):
    """
    Callback to update the health state on the left side.
    :param station_name: choose the name of the station to display info
    :param n_intervals: update every n_intervals the table.
    :return:
    """
    states = []
    states_list = []
    global client_oracle_xat

    try:
        client_oracle_xat.write_state_health()
    except cx_Oracle.ProgrammingError:
        print('Connection error for HatOracleClient')
    except cx_Oracle.DatabaseError:
        print('Connection error for HatOracleClient')
    except AttributeError:
        print('Connection not available for new data.')

    if station_name is not None:
        try:
            with open(f'log/{tab}/states_xat.xml', 'r', encoding='utf-8') as fp:
                content = fp.read()
                bs_states = BS(content, 'lxml-xml')
            bs_station = bs_states.find('station', {'name': station_name})
            for state in bs_station.find_all('state'):
                states.append([state.get('name'), state.get('value'), int(state.get('problem'))])

        except FileNotFoundError:
            pass

        table_inside = []
        for state in states:
            if state[2] == 0:
                text_badge = "OK"
                color = "success"
            elif state[2] == 1:
                text_badge = "Warning"
                color = "warning"
            elif state[2] == 2:
                text_badge = "Critic"
                color = "danger"
            else:
                text_badge = "N/A"
                color = "secondary"

            table_inside.append(html.Tr(
                [html.Td(state[0]),
                 html.Td(state[1]),
                 html.Td(dbc.Badge(text_badge, color=color, className="mr-1"))
                 ]
            ))

        table_body = [html.Tbody(table_inside)]

        states_list = dbc.Table(table_body,
                                bordered=True,
                                dark=True,
                                hover=True,
                                responsive=True,
                                striped=True
                                )

    # try:
    #     create_alarm_from_HAT(tab)
    # except AttributeError:
    #     print('Wrong server to create alarms')

    return html.Div(id='health-states', children=states_list)

# PART FOR ALARMS ALERT AND GRAPHS


graph_top = html.Div(children=[
    html.Div(id='alarm-alert', children=[]),
    html.Div(id='old-number-alarms', children=0, hidden=True),
    html.Div(id='content_top_output'),
    html.Div(children=None, id='data-output', hidden=True),
    html.Br()])

# CLAIREMENT LE BORDEL ICI CA VA ETRE REECRIT NO WORRY


@app.callback(Output('alarm-alert', 'children'),
              Output('old-number-alarms', 'children'),
              Input('number-alarms', 'children'),
              Input('old-number-alarms', 'children'),
              Input('btn-alarm-sound', 'n_clicks'),
              prevent_initial_call=True)
def create_alert(nb_alarms, old_nb_alarms, n_clicks):
    if n_clicks % 2 == 0:
        sound = False
    else:
        sound = True
    if sound:
        wave_obj = sa.WaveObject.from_wave_file("assets/alert-sound.wav")
    else:
        wave_obj = sa.WaveObject.from_wave_file("assets/alert-no-sound.wav")

    if nb_alarms == 0:
        sa.stop_all()
        return [], old_nb_alarms
    elif nb_alarms <= old_nb_alarms:
        sa.stop_all()
        try:
            wave_obj.play()
        except SimpleaudioError:
            pass
        return dbc.Alert('Warning, alarm(s)!', color='warning', dismissable=True, is_open=True), old_nb_alarms
    else:
        sa.stop_all()
        try:
            wave_obj.play()
        except SimpleaudioError:
            pass
        return dbc.Alert('Warning, new alarm(s)!', color='danger', dismissable=True, is_open=True), nb_alarms

# FUNCTION TO RETRIEVE DATA AND STORE IT IN DATA BUFFER FOLDER


@app.callback(Output('content_top_output', 'children'),
              Input('tabs-connection', 'active_tab'),
              Input('network-list-active', 'value'),
              Input('interval-time-graph', 'n_intervals'),
              # Input('Trace', 'fig'),
              prevent_initial_call=True)
def render_figures_top(tab, sta_list, n_intervals):

    if VERBOSE == 2:
        pid = os.getpid()
        python_process = psutil.Process(pid)
        memory_use = python_process.memory_info()[0]/2.**30
        print('memory use:', round(memory_use,3))

    gc.collect()

    if tab == 'server':
        global client
        global time_graphs_names
        global time_graphs
        global fig_list
        global interval_time_graphs
        if sta_list is None:
            time_graphs_names = []
            time_graphs = []
            fig_list = []
        else:
            for i, name in enumerate(time_graphs_names):
                if name not in sta_list:
                    time_graphs_names.pop(i)
                    time_graphs.pop(i)
                    fig_list.pop(i)

            for station in sta_list:
                # ADDING NEW STATION TO THE GRAPH LIST

                if station not in time_graphs_names:
                    if os.path.isdir(BUFFER_DIR) is not True:
                        os.mkdir(BUFFER_DIR)

                    try:
                        data_sta = pd.read_feather(BUFFER_DIR+'/'+station+'.data')
                    except FileNotFoundError:
                        data_sta = pd.DataFrame({'Date': [pd.to_datetime(UTCDateTime().timestamp, unit='s')], 'Data_Sta': [0]})

                    date_x = data_sta['Date'].values
                    data_sta_y = data_sta['Data_Sta'].values

                    fig = go.Figure(go.Scattergl(x=date_x, y=data_sta_y, mode='lines', showlegend=False,
                                                 line=dict(color=COLOR_TIME_GRAPH),
                                                 hovertemplate='<b>Date:</b> %{x}<br>' +
                                                               '<b>Val:</b> %{y}<extra></extra>'))

                    range_x = [pd.Timestamp(date_x[-1])-TIME_DELTA, pd.Timestamp(date_x[-1])]

                    fig.update_layout(template='plotly_dark', title=station,
                                      xaxis={'range': range_x},
                                      yaxis={'autorange': True},
                                      height=HEIGHT_GRAPH,
                                      margin=dict(l=LEFT_GRAPH, r=RIGHT_GRAPH, b=BOTTOM_GRAPH, t=TOP_GRAPH, pad=4))

                    fig_list.append(fig)
                    time_graphs_names.append(station)
                    time_graphs.append(dcc.Graph(figure=fig, id=station, config={'displaylogo': False}))

                    interval_time_graphs = dcc.Interval(
                        id='interval-time-graph',
                        interval=UPDATE_TIME_GRAPH,  # in milliseconds
                        n_intervals=0,
                        disabled=False)

                # UPDATING THE EXISTING GRAPHS
                else:
                    i = time_graphs_names.index(station)

                    try:
                        data_sta = pd.read_feather(BUFFER_DIR+'/'+station+'.data')
                    except FileNotFoundError:
                        data_sta = pd.DataFrame({'Date': [pd.to_datetime(UTCDateTime().timestamp, unit='s')], 'Data_Sta': [0]})

                    date_x = data_sta['Date'].values
                    data_sta_y = data_sta['Data_Sta'].values

                    fig_list[i].data = []
                    fig_list[i].add_trace(go.Scattergl(x=date_x, y=data_sta_y, mode='lines', showlegend=False,
                                                       line=dict(color=COLOR_TIME_GRAPH),
                                                       hovertemplate='<b>Date:</b> %{x}<br>' +
                                                                     '<b>Val:</b> %{y}<extra></extra>'))
                    try:
                        if client.data_retrieval is False:
                            range_x = [pd.Timestamp(date_x[-1]) - TIME_DELTA, pd.Timestamp(date_x[-1])]
                            fig_list[i].update_xaxes(range=range_x)
                        else:
                            range_x = [pd.Timestamp(date_x[0]), pd.Timestamp(date_x[-1])]
                            fig_list[i].update_xaxes(range=range_x)
                    except AttributeError:
                        range_x = [pd.Timestamp(date_x[-1]) - TIME_DELTA, pd.Timestamp(date_x[-1])]
                        fig_list[i].update_xaxes(range=range_x)

        return html.Div([
            # html.H6('Connection server tab active'),
            html.Div(children=time_graphs),
            html.Div(children=interval_time_graphs)
        ])


@app.callback(Output('data-output', 'children'),
              Input('tabs-connection', 'active_tab'),
              # Input('interval-data', 'n_intervals'),
              Input('network-list-active', 'value'),
              State('input-on-submit', 'value'),
              # Input('data-output', 'children'),
              prevent_initial_call=True)
def update_data(tab, network_list_active, submit_value):
    if tab == 'server':
        # global network_list_values
        global network_list
        global network_list_values

        if network_list_active:
            if os.path.isdir(BUFFER_DIR) is not True:
                os.mkdir(BUFFER_DIR)

            with open(BUFFER_DIR+'/streams.data', 'w') as streams:
                for sta in network_list_active:
                    streams.write('\n'+sta)
        else:
            try:
                os.remove(BUFFER_DIR+'/streams.data')
            except FileNotFoundError:
                pass

        if network_list_active is not None:
            return html.Div(children=network_list_active.copy(), id='data-output', hidden=True)
        else:
            return html.Div(children=[], id='data-output', hidden=True)

    elif tab == 'folder':

        return html.Div([
            html.H6('Connection to Folder not implemented'),

        ])
    # elif tab == 'file':
    #     return html.Div([
    #             # html.H3(id='title-obspy'),
    #             dcc.Loading(
    #                 id="loading",
    #                 type="default",
    #                 children=html.Div(id="loading-output")
    #             ),
    #             dcc.Loading(id="loading-icon",
    #                         children=dcc.Graph(children=fig,
    #                                            config={'displaylogo': False}),
    #                         type="graph"),
    #
    #             html.Br(),
    #             # html.H3(children='Information about data'),
    #             # html.Div(id='output-data-upload')
    #         ]
    #     )


graph_bottom = html.Div(
    [
        html.H5("State of Health", className="display-5"),
        dbc.Tabs(id="tabs-styled-with-inline",
                 children=[
                     dbc.Tab(label='Map', tab_id='map'),
                     dbc.Tab(label='State of Health', tab_id='soh'),
                     dbc.Tab(label='Alarms in progress', tab_id='alarms_in_progress'),
                     dbc.Tab(label='Alarms completed', tab_id='alarms_completed'),
                    ],
                 active_tab='alarms_in_progress'),
        html.Div(id='tabs-content-inline')
    ],
    # style=CHILD
)


@app.callback(Output({'type': 'btn-alarm', 'id_alarm': MATCH}, 'children'),
              Input({'type': 'btn-alarm', 'id_alarm': MATCH}, 'n_clicks'),
              Input({'type': 'btn-alarm', 'id_alarm': MATCH}, 'id'),
              # State('input-on-submit', 'value'),
              State('tabs-connection', 'active_tab'))
def complete_alarm(n_clicks, _id, tab):
    if n_clicks == 0:
        return 'Complete Alarm?'
    elif n_clicks == 1:
        return 'Are you sure?'
    elif n_clicks == 2:
        try:
            with open(f'log/{tab}/alarms.xml', 'r', encoding='utf-8') as fp:
                content = fp.read()
                bs_alarms = BS(content, 'lxml-xml')
            bs_alarms_tag = bs_alarms.find('alarms')
            bs_ongoing = bs_alarms.find('ongoing')
            bs_completed = bs_alarms.find('completed')

            if bs_completed is None:
                bs_completed = bs_alarms_tag.new_tag('completed')

            bs_alarm_to_move = bs_ongoing.find('alarm', {'id': _id['id_alarm']})
            bs_completed.append(bs_alarm_to_move)
            bs_alarms_tag.append(bs_completed)

            with open(f"log/{tab}/alarms.xml", 'w', encoding='utf-8') as fp:
                fp.write(bs_alarms.prettify())
        except FileNotFoundError:
            print('No alarm file found in log.')
            pass

        return dbc.Badge('Alarm completed', color='success')
    else:
        return dbc.Badge('Alarm completed', color='success')


@app.callback(Output('tabs-content-inline', 'children'),
              Input('tabs-styled-with-inline', 'active_tab'),
              Input('interval-alarms', 'n_intervals'),
              State('tabs-connection', 'active_tab'),
              Input('station-list-one-choice', 'value'),
              prevent_initial_call=True)
def update_alarms(tab, n_intervals, type_connection, sta):
    # COUNTING THE ALARMS WHATEVER THE TAB
    i = 0
    try:

        with open(f'log/{type_connection}/alarms.xml', 'r', encoding='utf-8') as fp:
            content = fp.read()
            bs_alarms = BS(content, 'lxml-xml')

        bs_ongoing = bs_alarms.find('ongoing')

        if bs_ongoing is not None:
            i = len(bs_ongoing.find_all('alarm'))

    except FileNotFoundError:
        pass

    if tab == 'map':
        fig = go.Figure(data=go.Scattermapbox(lat=LIST_LAT_STA, lon=LIST_LON_STA,
                                              text=LIST_NAME_STA, mode='markers',
                                              hovertemplate='<b>Sta:</b> %{text}<br>' +
                                                            '<b>Pos:</b> (%{lat}, %{lon})<extra></extra>',
                                              marker=dict(size=12, color='rgba(17, 119, 51, 0.6)')))
        fig.update_layout(height=450, margin={"r": 0, "t": 0, "l": 0, "b": 0},
                          mapbox=dict(zoom=ZOOM_MAP, style='stamen-terrain', bearing=0,
                                      center=go.layout.mapbox.Center(lat=LAT_MAP, lon=LON_MAP), pitch=0))

        return html.Div([
            dcc.Graph(figure=fig, config={'displaylogo': False}),
            html.Div(id='number-alarms', children=i, hidden=True)
        ])
    elif tab == 'soh':
        states_xat = []
        states_xat_table = []
        states_soh = []
        states_soh_table = []
        try:
            with open(f'log/{type_connection}/states_xat.xml', 'r', encoding='utf-8') as fp:
                content = fp.read()
                bs_states_xat = BS(content, 'lxml-xml')
            bs_station = bs_states_xat.find('station', {'name': sta})
            if bs_station is not None:
                for state in bs_station.find_all('state'):
                    state_dt = state.get('datetime')
                    state_datetime = state_dt[1:5] + '-' + state_dt[5:7] + '-' + \
                                     state_dt[7:9] + ' ' + state_dt[10:12] + ':' + \
                                     state_dt[12:14] + ':' + state_dt[14:]
                    states_xat_table.append(html.Tr(
                        [html.Td(state_datetime),
                         html.Td(state.get('name')),
                         html.Td(state.get('value'))
                         ]
                    ))

                table_body = [html.Tbody(states_xat_table)]

                states_xat = dbc.Table(table_body,
                                       bordered=True,
                                       dark=True,
                                       hover=True,
                                       responsive=True,
                                       striped=True
                                       )
        except FileNotFoundError:
            print(f'states_xat.xml file not found in log/{type_connection}')

        try:
            with open(f'log/{type_connection}/states_soh.xml', 'r', encoding='utf-8') as fp:
                content = fp.read()
                bs_states_soh = BS(content, 'lxml-xml')
            bs_station = bs_states_soh.find('station', {'name': sta})
            if bs_station is not None:
                for state in bs_station.find_all('state'):
                    state_dt = state.get('datetime')
                    state_datetime = state_dt[1:5] + '-' + state_dt[5:7] + '-' + \
                                     state_dt[7:9] + ' ' + state_dt[10:12] + ':' + \
                                     state_dt[12:14] + ':' + state_dt[14:]
                    states_soh_table.append(html.Tr(
                        [html.Td(state_datetime),
                         html.Td(state.get('name')),
                         html.Td(state.get('value'))
                         ]
                    ))

                table_body = [html.Tbody(states_soh_table)]

                states_soh = dbc.Table(table_body,
                                       bordered=True,
                                       dark=True,
                                       hover=True,
                                       responsive=True,
                                       striped=True
                                       )
        except FileNotFoundError:
            print(f'states_soh.xml file not found in log/{type_connection}')

        return [html.Div(id='tabs-content-inline', children=[states_xat, states_soh]),
                html.Div(id='number-alarms', children=i, hidden=True)]

    elif tab == 'alarms_in_progress':
        nc_alarms_list = []
        i = 0
        try:
            with open(f'log/{type_connection}/alarms.xml', 'r', encoding='utf-8') as fp:
                content = fp.read()
                bs_alarms = BS(content, 'lxml-xml')

            bs_ongoing = bs_alarms.find('ongoing')

            # display all the ongoing alarms
            nc_alarms_inside = []

            if bs_ongoing is not None:
                for alarm in bs_ongoing.find_all('alarm'):
                    i = i + 1
                    alarm_station = alarm.get('station')
                    alarm_state = alarm.get('state')
                    alarm_detail = alarm.get('detail')
                    alarm_id = alarm.get('id')

                    alarm_problem = int(alarm.get('problem'))
                    if alarm_problem == 1:
                        text_badge = "Warning"
                        color = "warning"
                    else:
                        text_badge = "Critic"
                        color = "danger"

                    alarm_dt = alarm.get('datetime')
                    alarm_datetime = alarm_dt[1:5] + '-' + alarm_dt[5:7] + '-' + \
                                     alarm_dt[7:9] + ' ' + alarm_dt[10:12] + ':' + \
                                     alarm_dt[12:14] + ':' + alarm_dt[14:]

                    nc_alarms_inside.append(html.Tr([html.Td(alarm_datetime),
                                                     html.Td(alarm_station),
                                                     html.Td(alarm_state),
                                                     html.Td(alarm_detail),
                                                     html.Td(dbc.Badge(text_badge, color=color, className="mr-1")),
                                                     html.Td([dbc.Button('Complete Alarm?',
                                                                         id={'type': 'btn-alarm',
                                                                             'id_alarm': alarm_id},
                                                                         className="mr-1", n_clicks=0)
                                                              ]),
                                                     ]))

            table_body = [html.Tbody(nc_alarms_inside)]

            nc_alarms_list = dbc.Table(table_body,
                                       bordered=True,
                                       dark=True,
                                       hover=True,
                                       responsive=True,
                                       striped=True
                                       )
        except FileNotFoundError:
            pass

        return [html.Div(id='tabs-content-inline', children=nc_alarms_list),
                html.Div(id='number-alarms', children=i, hidden=True)]
    elif tab == 'alarms_completed':
        c_alarms_list = []
        try:

            with open(f'log/{type_connection}/alarms.xml', 'r', encoding='utf-8') as fp:
                content = fp.read()
                bs_alarms = BS(content, 'lxml-xml')

            bs_completed = bs_alarms.find('completed')
            # display all the ongoing alarms
            c_alarms_inside = []
            if bs_completed is not None:
                for alarm in bs_completed.find_all('alarm'):
                    alarm_station = alarm.get('station')
                    alarm_state = alarm.get('state')
                    alarm_detail = alarm.get('detail')

                    alarm_problem = int(alarm.get('problem'))
                    if alarm_problem == 1:
                        text_badge = "Warning"
                        color = "warning"
                    else:
                        text_badge = "Critic"
                        color = "danger"

                    alarm_dt = alarm.get('datetime')
                    alarm_datetime = alarm_dt[1:5] + '-' + alarm_dt[5:7] + '-' + \
                                     alarm_dt[7:9] + ' ' + alarm_dt[10:12] + ':' + \
                                     alarm_dt[12:14] + ':' + alarm_dt[14:]

                    c_alarms_inside.append(html.Tr([html.Td(alarm_datetime),
                                                    html.Td(alarm_station),
                                                    html.Td(alarm_state),
                                                    html.Td(alarm_detail),
                                                    html.Td(dbc.Badge(text_badge, color=color, className="mr-1"))]))

            table_body = [html.Tbody(c_alarms_inside)]

            c_alarms_list = dbc.Table(table_body,
                                      bordered=True,
                                      dark=True,
                                      hover=True,
                                      responsive=True,
                                      striped=True
                                      )
        except FileNotFoundError:
            pass

        return [html.Div(id='tabs-content-inline', children=c_alarms_list),
                html.Div(id='number-alarms', children=i, hidden=True)]


@app.callback(# Output('output-data-upload', 'children'),
              Output('Trace', 'fig'),
              # Output('title-obspy', 'children'),
              # Output('data-obspy', 'data'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'),
              prevent_initial_call=True)
def update_output(contents, names):
    if names is not None:
        content_type, content_string = contents[0].split(',')
        decoded = base64.b64decode(content_string)

        # Write the file on the server
        name = names[0].split('.')[:-1]
        path = 'mseed_files'
        for directory in name:
            try:
                path = os.path.join(path, directory)
                os.mkdir(path)
            except FileExistsError:
                pass

        file_path = os.path.join(path, names[0])
        if os.path.isfile(file_path) is not True:
            with open(file_path, mode='wb') as file:
                file.write(decoded)
                file.close()

        st = read(file_path, 'mseed')  # read data
        tr = st[0]
        stats = tr.stats

        endtime = stats.endtime
        # if stats.npts > 1000000:
        #     reduced_factor = 750
        # elif stats.ntps > 100000:
        #     reduced_factor = 75
        # else:
        #     reduced_factor = 20
        reduced_factor = 10
        sr = stats.sampling_rate
        nb_pts = int(sr * 3600)

        # df = pd.DataFrame({
        #     "Time": tr.times("utcdatetime")[-nb_pts::reduced_factor],
        #     "Amplitude": tr.data[-nb_pts::reduced_factor]
        # })

        x = [UTCDateTime(t) for t in tr.times('timestamp')[-nb_pts::reduced_factor]]
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=x,
                                   y=tr.data[-nb_pts::reduced_factor],
                                   mode='lines',
                                   name='lines',
                                   ))
        # fig = px.line(df, x="Time", y="Amplitude", title='Display Trace and information of {}'.format(names[0]))

        fig.update_layout(template='plotly_dark', title=names[0], xaxis={'autorange': True})
        children = [html.Div('{}: {}'.format(key, element)) for key, element in stats.items()]
        return fig
        # return children, fig


sidebar = dbc.Col([sidebar_top, sidebar_bottom], width=True, style=SIDEBAR_STYLE)
graph = dbc.Col([graph_top, graph_bottom], width=9, style=GRAPH_STYLE)


app.layout = dbc.Container(dbc.Row([dcc.Location(id="url"), sidebar, graph], style=ROW),
                           fluid=True, style={"height": "100vh"})


# @app.callback(Output("page-content", "children"),
#               [Input("url", "pathname")])
# def render_page_content(pathname):
#     if pathname == "/":
#         return html.P("This is the content of the home page!")
#     elif pathname == "/page-1":
#         return html.P("This is the content of page 1. Yay!")
#     elif pathname == "/page-2":
#         return html.P("Oh cool, this is page 2!")
#     # If the user tries to reach a different page, return a 404 message
#     return dbc.Jumbotron(
#         [
#             html.H1("404: Not found", className="text-danger"),
#             html.Hr(),
#             html.P(f"The pathname {pathname} was not recognised..."),
#         ]
#     )


# Read data
# @app.callback(
#     Output('output-data-upload', 'children'),
#     Input('upload-data', 'contents'),
#     prevent_initial_call=False
# )
# def update_output(contents):
#     content = contents[0]
#     print(contents)
#     st = read(content) # read data
#     tr = st[0]
#     stats = tr.stats
#     return [html.Div('{}: {}'.format(key, element)) for key, element in stats.items()]


if __name__ == '__main__':
    if DEBUG is not True:
        webbrowser.open(SERVER_DASH_PROTOCOL + SERVER_DASH_IP + ':' + str(SERVER_DASH_PORT))
    else:
        log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)

    app.run_server(host=SERVER_DASH_IP, port=SERVER_DASH_PORT, debug=DEBUG, threaded=True)

    # ACTIONS TO EXECUTE IF SOFTWARE QUIT
    # #1 DELETE THE BUFFER FILES
    for _, name in enumerate(time_graphs_names):
        os.remove(BUFFER_DIR+'/'+name+'.data')
        os.remove(BUFFER_DIR+'/streams.data')

    if type(client) == EasySLC:
        client.close()
        del client
    else:
        del client

    client_oracle_xat.close()
    del client_oracle_xat
