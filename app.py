# # -*- coding: utf-8 -*-
#
# # Run this app with `python app.py` and
# # visit http://127.0.0.1:8050/ in your web browser.
#
# import dash
# import dash_core_components as dcc
# import dash_html_components as html
# # from dash.dependencies import Input, Output
# import plotly.express as px
# import pandas as pd
# from obspy import read
#
# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
#
# app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
#
# # assume you have a "long-form" data frame
# # see https://plotly.com/python/px-arguments/ for more options
#
#
# st = read()
# tr = st[0]
#
# x = tr.times()
#
# stats = tr.stats
#
# df = pd.DataFrame({
#     "Time": tr.times("utcdatetime"),
#     "Amplitude": tr.data
# })
#
# fig = px.line(df, x="Time", y="Amplitude")
#
# app.layout = html.Div(children=[
#
#
#     dcc.Graph(
#         id='example-graph',
#         figure=fig
#     ),
#     html.Div(children=
#              [html.Div(children='{}: {}'.format(key, element)) for key, element in stats.items()]
#              ),
# ])
#
# if __name__ == '__main__':
#     app.run_server(debug=True)

import time
import io
import base64
import os

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
import plotly.express as px
import plotly.graph_objects as go

# obspy
from obspy import read, read_inventory
from obspy.core import UTCDateTime

# pandas
import pandas as pd

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], external_scripts=["https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML" ])

server = app.server

MARGIN_LEFT = "20%"

SIDEBAR_TOP_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": MARGIN_LEFT,
    "height": "60%",
    "padding": "1rem 1rem",
    "margin-right": "2rem",
    "background-color": "#111111",
    "font-family": "Tw Cen MT"
}
SIDEBAR_BOTTOM_STYLE = {
    "position": "fixed",
    "top": "60%",
    "left": 0,
    "bottom": 0,
    "width": MARGIN_LEFT,
    "padding": "1rem 1rem",
    "margin-right": "2rem",
    "background-color": "#111111",
    "font-family": "Tw Cen MT"
}

GRAPH_TOP_STYLE = {
    "margin-left": MARGIN_LEFT,
    "height": "70%",
    "margin-right": "2rem",
    "padding": "1rem 2rem",
    "font-family": "Tw Cen MT"
}

GRAPH_BOTTOM_STYLE = {
    "top": "70%",
    "margin-left": MARGIN_LEFT,
    "margin-right": "2rem",
    "padding": "1rem 2rem",
    "font-family": "Tw Cen MT"
}

logo_filename = 'logo.jpg'
encoded_logo = base64.b64encode(open(logo_filename, 'rb').read())

sidebar_top = html.Div(
    [
        html.H2([html.Img(src='data:image/jpg;base64,{}'.format(encoded_logo.decode())), " MONA"], className="display-4"),
        html.P(
            [
                "Monitoring App of the IAG - Mongolia"
            ],
            className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("Connect to Server", href="/server", active="exact"),
                dbc.NavLink("Connect to Folder", href="/folder", active="exact"),
                dbc.NavLink("Import File", href="/file", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),

        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select seismic file')
            ]),
            style={
                'width': '90%',
                'height': '30px',
                'lineHeight': '30px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '2px',
                'textAlign': 'center',

            },
            # Allow multiple files to be uploaded
            multiple=True
        ),
    ],

    style=SIDEBAR_TOP_STYLE,
)

sidebar_bottom = html.Div(
    [
        html.H2("Here's the constant", className="display-4"),

    ],
    style=SIDEBAR_BOTTOM_STYLE,
)

graph_top = html.Div(id='page-content',
                        style=GRAPH_TOP_STYLE,
                        children=[
                                # html.H3(id='title-obspy'),
                                dcc.Loading(
                                    id="loading",
                                    type="default",
                                    children=html.Div(id="loading-output")
                                ),
                                dcc.Loading(id="loading-icon",
                                            children=dcc.Graph(id='Trace', config={'displaylogo': False}), type="graph"),

                                html.Br(),
                                # html.H3(children='Information about data'),
                                # html.Div(id='output-data-upload')
                        ]
                     )


graph_bottom = html.Div(
    [
        html.H3("Graphics of constants", className="display-5"),
        dbc.Tabs(id="tabs-styled-with-inline",
                 children=[
                    dbc.Tab(label='PSD', tab_id='PSD'),
                    dbc.Tab(label='Voltage', tab_id='voltage'),
                    dbc.Tab(label='Current', tab_id='current'),
                    dbc.Tab(label='Intrusions', tab_id='intrusions'),
                    ],
                 active_tab='PSD'),
        html.Div(id='tabs-content-inline')
    ],
    style=GRAPH_BOTTOM_STYLE
)


@app.callback(Output('tabs-content-inline', 'children'),
              Input('tabs-styled-with-inline', 'active_tab'))
def render_content(tab):
    if tab == 'PSD':
        return html.Div([
            html.H3("Here is the PSD")
        ])
    elif tab == 'voltage':
        return html.Div([
            html.H3('Graphic of voltage')
        ])
    elif tab == 'current':
        return html.Div([
            html.H3('Graphic of the current')
        ])
    elif tab == 'intrusions':
        return html.Div([
            html.H3('Resume of the different sensors Loop, intrusion ....')
        ])

@app.callback(# Output('output-data-upload', 'children'),
              Output('Trace', 'figure'),
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
                                   mode='lines+markers',
                                   name='lines+markers',
                                   ))
        # fig = px.line(df, x="Time", y="Amplitude", title='Display Trace and information of {}'.format(names[0]))

        fig.update_layout(template='plotly_dark', title=names[0])
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
    app.run_server(debug=True)
