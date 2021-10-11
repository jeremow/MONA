# # -*- coding: utf-8 -*-
#
# # Run this app with `python app.py` and
# # visit http://127.0.0.1:8050/ in your web browser.

import time
import io
import base64
import os
import webbrowser
import logging as log

import dash
import plotly.data
from dash.dependencies import Input, Output, State
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from dash import dash_table
import plotly.express as px
import plotly.graph_objects as go

# obspy
from obspy import read, read_inventory
from obspy.core import UTCDateTime

# pandas
import pandas as pd

# style and config
from assets.style import *
from config import *

# sidebar connection
from connection import *

app = dash.Dash(__name__, suppress_callback_exceptions=True, update_title="")

# global variables which are useful, dash will say remove these variables, I say let them exist
server = app.server
app.title = 'Mona-Lisa'
client = ServerSeisComP3('0.0.0.0', '18000')
time_graphs_names = []
time_graphs = []
fig_list = []
network_list = []
interval_time_graphs = []

# logo file and decoding to display in browser
logo_filename = 'assets/logo.jpg'
encoded_logo = base64.b64encode(open(logo_filename, 'rb').read())


# SIDEBAR TOP: LOGO, TITLE, CONNECTION AND CHOICE OF STATIONS FOR TIME-SERIE GRAPHS
sidebar_top = html.Div(
    [
        html.H2([html.Img(src='data:image/jpg;base64,{}'.format(encoded_logo.decode()), height=80), " MONA-LISA"], className="display-5"),
        html.P(
            [
                "Monitoring App of the IAG - " + NAME_AREA
            ],
            className="lead"
        ),
        dbc.Button('Open Grafana', id='btn-grafana', n_clicks=0, className="mr-1",
                   style={'display': 'inline-block', 'width': '100%'}),
        html.Br(), html.Br(),
        html.Div(id="hidden-div", style={"display": "none"}),
        dbc.Tabs(id="tabs-connection",
                 children=[
                     dbc.Tab(label='Server', tab_id='server'),
                     dbc.Tab(label='Folder', tab_id='folder', disabled=True),
                     dbc.Tab(label='File', tab_id='file', disabled=True),
                 ],
                 active_tab='server'),
        html.Div(id='tabs-connection-inline'),  # TABS FOR SERVER, FILE, ...

    ],

    style=SIDEBAR_TOP_STYLE,
)

# Grafana button to open in a new tab the constants of Roddes, Ripex, ...


@app.callback(Output('hidden-div', 'children'),
              Input('btn-grafana', 'n_clicks'))
def open_grafana(btn1):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'btn-grafana' in changed_id:
        webbrowser.open(GRAFANA_LINK)

# INSIDE OF THE TABS


@app.callback(Output('tabs-connection-inline', 'children'),
              Input('tabs-connection', 'active_tab'))
def render_connection(tab):
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
    dash.dependencies.Output('container-button-basic', 'children'),
    [dash.dependencies.Input('connect-server-button', 'n_clicks')],
    [dash.dependencies.State('input-on-submit', 'value')]
)
def connect_update_server(n_clicks, value):
    global network_list
    if value is not None:
        global client
        client, ip_address, port = create_client(value)

        connection_client(client, ip_address, port, network_list)

        return [
            dcc.Dropdown(id='network-list-active',
                         placeholder='Select stations for time graphs',
                         options=network_list, multi=True, style={'color': 'black'}),
            html.P('Connection active to {}:{}'.format(ip_address, port), style={'color': 'green'}),
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
        html.Div(id='station_list_div', children=dcc.Dropdown(id='station-list-one-choice',
                                                              placeholder='Select a station', options=network_list,
                                                              multi=False, style={'color': 'black'})),

        html.Div(id='health-states',
                 children=dbc.Table()
                 )

    ],
    style=SIDEBAR_BOTTOM_STYLE,
)

# HEALTH STATE FUNCTION TO RECOVER THE STATION FROM THE SERVER AND DISPLAY IT INTO A GOOD WAY


@app.callback(Output('station_list_div', 'children'),
              Input('container-button-basic', 'children'))
def update_list_station(children):
    return [dcc.Dropdown(id='station-list-one-choice', placeholder='Select a station',
                         options=network_list, multi=False, style={'color': 'black'})]


@app.callback(Output('health-states', 'children'),
              Input('station-list-one-choice', 'value'),
              Input('interval-states', 'n_intervals'),
              prevent_initial_call=True)
def update_states(station_name, n_intervals):
    states = []
    states_list = []
    if station_name is not None:
        split_name = station_name.split('.')
        state_network = split_name[0]
        state_station = split_name[1]
        try:
            states_server = ET.parse('log/server/{}_states.xml'.format(client.ip_address + '.' + str(client.port)))
            states_server_root = states_server.getroot()
            for state in states_server_root.findall("./network[@name='{0}']/station[@name='{1}']/"
                                                    "state".format(state_network, state_station)):
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
            else:
                text_badge = "Critic"
                color = "danger"

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


graph_top = html.Div(id='content_top_output',
                        style=GRAPH_TOP_STYLE
                     )

# CLAIREMENT LE BORDEL ICI CA VA ETRE REECRIT NO WORRY


@app.callback(Output('content_top_output', 'children'),
              Input('tabs-connection', 'active_tab'),
              Input('network-list-active', 'value'),
              Input('interval-time-graph', 'n_intervals'),
              # Input('Trace', 'fig'),
              prevent_initial_call=True)
def render_content_top(tab, sta_list, n_intervals):
    if tab == 'server':
        global time_graphs_names
        global time_graphs
        global fig_list
        global client
        global interval_time_graphs
        if sta_list is None:
            sta_list = []
            time_graphs_names = []
            time_graphs = []
            fig_list = []
        else:
            for i, name in enumerate(time_graphs_names):
                if name not in sta_list:
                    time_graphs_names.pop(i)
                    time_graphs.pop(i)
                    fig_list.pop(i)

            t = UTCDateTime()
            for station in sta_list:
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

                    log.info(full_sta_name)
                    st = client.get_waveforms(net, sta, loc, cha, t-10-UPDATE_TIME_GRAPH/1000, t-10)
                    tr = st[0]

                    x = tr.times('UTCDateTime')
                    fig = plotly.subplots.make_subplots(rows=1, cols=1)
                    fig.append_trace(go.Scattergl(x=x, y=tr.data, mode='lines', showlegend=False,
                                                  line=dict(color=COLOR_TIME_GRAPH)), row=1, col=1)

                    fig.update_layout(template='plotly_dark', title=station, xaxis={'autorange': True}, yaxis={'autorange': True})
                    fig_list.append(fig)
                    time_graphs_names.append(station)
                    time_graphs.append(dcc.Graph(figure=fig, id=station, config={'displaylogo': False}))

                    interval_time_graphs = dcc.Interval(
                        id='interval-time-graph',
                        interval=UPDATE_TIME_GRAPH,  # in milliseconds
                        n_intervals=0,
                        disabled=False)
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

                    st = client.get_waveforms(net, sta, loc, cha, t-10-UPDATE_TIME_GRAPH/1000, t-10)
                    tr = st[0]

                    x = tr.times('UTCDateTime')
                    fig_list[i].append_trace(go.Scattergl(x=x, y=tr.data, mode='lines', showlegend=False,
                                                          line=dict(color=COLOR_TIME_GRAPH)), row=1, col=1)
                    # time_graphs.pop(i)
                    # time_graphs.insert(i, fig_list[i])

        return html.Div([
            # html.H6('Connection server tab active'),
            html.Div(children=time_graphs),
            html.Div(children=interval_time_graphs)
        ])
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
                 active_tab='map'),
        html.Div(id='tabs-content-inline')
    ],
    style=GRAPH_BOTTOM_STYLE
)


@app.callback(Output('tabs-content-inline', 'children'),
              Input('tabs-styled-with-inline', 'active_tab'),
              Input('interval-alarms', 'n_intervals'),
              prevent_initial_call=True)
def render_content_bottom(tab, n_intervals):
    if tab == 'map':
        fig = go.Figure(data=go.Scattermapbox(lat=['46.932439'], lon=['104.593273'],  mode='markers',
                                              marker=go.scattermapbox.Marker(size=14)))
        fig.update_layout(height=450, margin={"r": 0, "t": 0, "l": 0, "b": 0},
                          mapbox=dict(zoom=ZOOM_MAP, style='stamen-terrain', bearing=0,
                                      center=go.layout.mapbox.Center(lat=LAT_MAP, lon=LON_MAP), pitch=0))

        return html.Div([
            dcc.Graph(figure=fig, config={'displaylogo': False})
        ])
    elif tab == 'alarms_in_progress':
        nc_alarms_list = []
        try:
            alarms_server = ET.parse('log/server/{}_alarms.xml'.format(client.ip_address + '.' + str(client.port)))
            alarms_server_root = alarms_server.getroot()

            # display all the ongoing alarms
            nc_alarms_inside = []
            for alarm in alarms_server_root.findall("./ongoing/alarm"):
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

                nc_alarms_inside.append(html.Tr([html.Td(alarm_datetime),
                                                 html.Td(alarm_station),
                                                 html.Td(alarm_state),
                                                 html.Td(alarm_detail),
                                                 html.Td(dbc.Badge(text_badge, color=color, className="mr-1"))]))

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

        return html.Div(id='tabs-content-inline', children=nc_alarms_list)
    elif tab == 'alarms_completed':
        c_alarms_list = []
        try:
            alarms_server = ET.parse('log/server/{}_alarms.xml'.format(client.ip_address + '.' + str(client.port)))
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

        return html.Div(id='tabs-content-inline', children=c_alarms_list)


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


app.layout = html.Div([dcc.Location(id="url"), sidebar_top, sidebar_bottom, graph_top, graph_bottom])


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

    app.run_server(host= SERVER_DASH_IP, port=SERVER_DASH_PORT, debug=DEBUG)
