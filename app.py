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
import os
import webbrowser
import logging as log
import time

import dash
from dash.dependencies import Input, Output, State, MATCH
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# obspy
from obspy import read

# pandas
import pandas as pd

# style and config
from assets.style import *
from config import *
from state_health import *

# sidebar connection
from connection import *
from retrieve_data import EasySLC, SLThread
from subprocess import Popen

# for alarms
import simpleaudio as sa

app = dash.Dash(__name__, suppress_callback_exceptions=True, update_title="MONA-LISA - Updating Data")
app.title = 'MONA-LISA'
server = app.server
# global variables which are useful, dash will say remove these variables, I say let them exist, else I will have
# problems between some callbacks.

try:
    del time_graphs_names, time_graphs, fig_list, network_list, network_list_values, interval_time_graphs, client
except NameError:
    pass

time_graphs_names = []
time_graphs = []
fig_list = []
network_list = []
network_list_values = []
interval_time_graphs = []
client = None

# Remove all the data residual files if they exist
try:
    for file in os.listdir(BUFFER_DIR):
        os.remove(BUFFER_DIR+'/'+file)
except PermissionError:
    log.warning('Folder in the data directory not removed.')
except FileNotFoundError:
    os.mkdir(BUFFER_DIR)


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
                     dbc.Tab(label='Folder', tab_id='folder', disabled=True),
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
    if n_clicks % 2 == 1:
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
                     style={'display': 'inline-block', 'width': '69%'}),
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
                     )
            ]
    # elif tab == 'folder':
    #     return html.Div([
    #         html.H6('Connection to folder not implemented')
    #     ])
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


@app.callback(
    Output('container-button-basic', 'children'),
    Input('connect-server-button', 'n_clicks'),
    State('input-on-submit', 'value'),
)
def connect_update_server(n_clicks, value):
    """
    Connect to the server with the EasySLC class. This is a Seedlink client which waits for the user of MONA-LISA to
    choose some stations. When one is selected, it will start to retrieve the data from the server.
    :param n_clicks:
    :param value:
    :return:
    """

    global network_list
    global network_list_values
    global client

    if value is not None:
        try:
            pass
            client = EasySLC(value, network_list, network_list_values)
            # client = SeedLinkClient(value, network_list, network_list_values)
        except SeedLinkException:
            client.connected = 0

        server = value.split(':')

        if len(server) == 1:
            server_hostname = server[0]
            server_port = '18000'
        else:
            server_hostname = server[0]
            server_port = server[1]

        if client.connected == 1:
            client_thread = SLThread('Client Thread', client)
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
    station_hat_list = []
    try:
        config_hat_server = ET.parse('log/server/states.xml')
        config_hat_server_root = config_hat_server.getroot()

        for station in config_hat_server_root.findall("./station"):
            station_name = station.attrib['name']
            station_hat_list.append({'label': station_name, 'value': station_name})
    except FileNotFoundError:
        print('No file for Health States found. Please verify log/server/states.xml')
    return [dcc.Dropdown(id='station-list-one-choice', placeholder='Select a station',
                         options=station_hat_list, multi=False, style={'color': 'black'})]


@app.callback(Output('health-states', 'children'),
              Input('station-list-one-choice', 'value'),
              Input('interval-states', 'n_intervals'),
              prevent_initial_call=True)
def update_states(station_name, n_intervals):
    """
    Callback to update the health state on the left side.
    :param station_name: choose the name of the station to display info
    :param n_intervals: update every n_intervals the table.
    :return:
    """
    states = []
    states_list = []
    try:
        state_server = HatOracleClient()
        state_server.write_state_health()
        state_server.close()
        del state_server
    except cx_Oracle.ProgrammingError:
        print('Connection error for HatOracleClient')
    except cx_Oracle.DatabaseError:
        print('Connection error for HatOracleClient')

    if station_name is not None:
        try:
            states_server = ET.parse('log/server/states.xml')
            states_server_root = states_server.getroot()
            for state in states_server_root.findall(f"./station[@name='{station_name}']/state"):
                states.append([state.attrib['name'], state.attrib['value'], int(state.attrib['problem'])])
            del states_server, states_server_root
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
        sound = True
    else:
        sound = False
    if sound:
        wave_obj = sa.WaveObject.from_wave_file("assets/alert-sound.wav")
    else:
        wave_obj = sa.WaveObject.from_wave_file("assets/alert-no-sound.wav")

    if nb_alarms == 0:
        sa.stop_all()
        return [], old_nb_alarms
    elif nb_alarms <= old_nb_alarms:
        sa.stop_all()
        wave_obj.play()
        return dbc.Alert('Warning, alarm(s)!', color='warning', dismissable=True, is_open=True), old_nb_alarms
    else:
        sa.stop_all()
        wave_obj.play()
        return dbc.Alert('Warning, new alarm(s)!', color='danger', dismissable=True, is_open=True), nb_alarms

# FUNCTION TO RETRIEVE DATA AND STORE IT IN DATA BUFFER FOLDER


@app.callback(Output('content_top_output', 'children'),
              Input('tabs-connection', 'active_tab'),
              Input('network-list-active', 'value'),
              Input('interval-time-graph', 'n_intervals'),
              # Input('Trace', 'fig'),
              prevent_initial_call=True)
def render_figures_top(tab, sta_list, n_intervals):
    if tab == 'server':
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
                    full_sta_name = station.split('.')
                    if len(full_sta_name) == 3:
                        net = full_sta_name[0]
                        sta = full_sta_name[1]
                        loc = ''
                        cha = full_sta_name[2]
                    else:
                        net = full_sta_name[0]
                        sta = full_sta_name[1]
                        loc = full_sta_name[2]
                        cha = full_sta_name[3]

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
                                      yaxis={'autorange': True})

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

                    full_sta_name = station.split('.')
                    if len(full_sta_name) == 3:
                        net = full_sta_name[0]
                        sta = full_sta_name[1]
                        loc = ''
                        cha = full_sta_name[2]
                    else:
                        net = full_sta_name[0]
                        sta = full_sta_name[1]
                        loc = full_sta_name[2]
                        cha = full_sta_name[3]

                    try:
                        data_sta = pd.read_feather(BUFFER_DIR+'/'+station+'.data')
                    except FileNotFoundError:
                        data_sta = pd.DataFrame({'Date': [pd.to_datetime(UTCDateTime().timestamp, unit='s')], 'Data_Sta': [0]})

                    date_x = data_sta['Date'].values
                    data_sta_y = data_sta['Data_Sta'].values

                    fig_list[i].add_trace(go.Scattergl(x=date_x, y=data_sta_y, mode='lines', showlegend=False,
                                                       line=dict(color=COLOR_TIME_GRAPH),
                                                       hovertemplate='<b>Date:</b> %{x}<br>' +
                                                                     '<b>Val:</b> %{y}<extra></extra>'))

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
            # if type(client) == EasySLC:
            #
            #     client.on_terminate()
            #     # client.conn.begin_time = t
            #     for station in network_list_active:
            #         full_sta_name = station.split('.')
            #         if len(full_sta_name) == 3:
            #             net = full_sta_name[0]
            #             sta = full_sta_name[1]
            #             cha = full_sta_name[2]
            #         else:
            #             net = full_sta_name[0]
            #             sta = full_sta_name[1]
            #             cha = full_sta_name[2] + full_sta_name[3]
            #
            #         client.select_stream(net, sta, cha)
            #     client.run()


                # t = UTCDateTime()
                # client.set_delta_time(t)
                # print(old_list_active)
                # if old_list_active != network_list_active:
                #     print(network_list_active)
                #     client.list_to_multiselect(network_list_active)
                #     print(client.multiselect)
                # client.run()

            # for station in network_list_values:
            #
            #     full_sta_name = station.split('.')
            #     if len(full_sta_name) == 3:
            #         net = full_sta_name[0]
            #         sta = full_sta_name[1]
            #         loc = ''
            #         cha = full_sta_name[2]
            #     else:
            #         net = full_sta_name[0]
            #         sta = full_sta_name[1]
            #         loc = full_sta_name[2]
            #         cha = full_sta_name[3]
            #
            #     st = client.get_waveforms(net, sta, loc, cha, t-10-UPDATE_DATA/1000, t-10)
            #     tr = st[0]
            #
            #     x = pd.to_datetime(tr.times('timestamp'), unit='s')
            #     new_data_sta = pd.DataFrame({'Date': x, 'Data_Sta': tr.data})
            #
            #     try:
            #         data_sta = pd.read_pickle(BUFFER_DIR+'/'+station+'.pkl')
            #         if len(data_sta) <= 60000:
            #             data_sta = pd.concat([data_sta, new_data_sta])
            #         else:
            #             data_sta = pd.concat([data_sta[round(-len(data_sta)/2):], new_data_sta])
            #     except FileNotFoundError:
            #         data_sta = new_data_sta
            #
            #     data_sta.to_pickle(BUFFER_DIR+'/'+station+'.pkl')
        if network_list_active is not None:
            return html.Div(children=network_list_active.copy(), id='data-output', hidden=True)
        else:
            return html.Div(children=[], id='data-output', hidden=True)
    # elif tab == 'folder':
    #     return html.Div([
    #         html.H6('Connection to Folder not implemented'),
    #
    #     ])
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
        html.H5("Alarms", className="display-5"),
        dbc.Tabs(id="tabs-styled-with-inline",
                 children=[
                    dbc.Tab(label='Map', tab_id='map'),
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
              State('input-on-submit', 'value'))
def complete_alarm(n_clicks, id, server):
    if n_clicks == 0:
        return 'Complete Alarm?'
    elif n_clicks == 1:
        return 'Are you sure?'
    elif n_clicks == 2:
        if server is None:
            server = "0.0.0.0:18000"
        server = server.split(':')
        if len(server) == 1:
            server_hostname = server[0]
            server_port = '18000'
        else:
            server_hostname = server[0]
            server_port = server[1]

        try:
            alarms_server = ET.parse('log/server/{}_alarms.xml'.format(server_hostname+'.'+server_port))
            alarms_server_root = alarms_server.getroot()
            alarm_to_move = alarms_server_root.find("./ongoing/alarm[@id='{}']".format(id['id_alarm']))
            alarms_server_root[1][-1].tail = '\n\t\t'
            alarms_server_root[1].text = "\n\t\t"
            alarms_server_root[1].append(alarm_to_move)
            alarms_server_root[0].remove(alarm_to_move)
            try:
                alarms_server_root[0][-1].tail = "\n\t"
            except IndexError:
                pass
            alarms_server_root[0].text = "\n\t\t"
            alarms_server_root[0].tail = '\n\n\t'
            alarms_server.write('log/server/{}_alarms.xml'.format(server_hostname+'.'+server_port))
        except FileNotFoundError:
            print('No alarm file found in log.')
            pass

        return dbc.Badge('Alarm completed', color='success')
    else:
        return dbc.Badge('Alarm completed', color='success')


@app.callback(Output('tabs-content-inline', 'children'),
              Input('tabs-styled-with-inline', 'active_tab'),
              Input('interval-alarms', 'n_intervals'),
              State('input-on-submit', 'value'),
              prevent_initial_call=True)
def render_content_bottom(tab, n_intervals, server):
    if server is None:
        server = "0.0.0.0:18000"
    server = server.split(':')
    if len(server) == 1:
        server_hostname = server[0]
        server_port = '18000'
    else:
        server_hostname = server[0]
        server_port = server[1]

    # COUNTING THE ALARMS WHATEVER THE TAB
    i = 0
    try:
        alarms_server = ET.parse('log/server/{}_alarms.xml'.format(server_hostname + '.' + server_port))
        alarms_server_root = alarms_server.getroot()

        for alarm in alarms_server_root.findall("./ongoing/alarm"):
            i = i + 1
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
    elif tab == 'alarms_in_progress':
        nc_alarms_list = []
        i = 0
        try:
            alarms_server = ET.parse('log/server/{}_alarms.xml'.format(server_hostname + '.' + server_port))
            alarms_server_root = alarms_server.getroot()

            # display all the ongoing alarms
            nc_alarms_inside = []

            for alarm in alarms_server_root.findall("./ongoing/alarm"):
                i = i + 1
                alarm_station = alarm.attrib['station']
                alarm_state = alarm.attrib['state']
                alarm_detail = alarm.attrib['detail']
                alarm_id = alarm.attrib['id']

                alarm_problem = int(alarm.attrib['problem'])
                if alarm_problem == 1:
                    text_badge = "Warning"
                    color = "warning"
                else:
                    text_badge = "Critic"
                    color = "danger"

                alarm_dt = alarm.attrib['datetime']
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
            alarms_server = ET.parse('log/server/{}_alarms.xml'.format(server_hostname + '.' + server_port))
            alarms_server_root = alarms_server.getroot()

            # display all the ongoing alarms
            c_alarms_inside = []
            for alarm in alarms_server_root.findall("./completed/alarm"):
                alarm_station = alarm.attrib['station']
                alarm_state = alarm.attrib['state']
                alarm_detail = alarm.attrib['detail']

                alarm_problem = int(alarm.attrib['problem'])
                if alarm_problem == 1:
                    text_badge = "Warning"
                    color = "warning"
                else:
                    text_badge = "Critic"
                    color = "danger"

                alarm_dt = alarm.attrib['datetime']
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
