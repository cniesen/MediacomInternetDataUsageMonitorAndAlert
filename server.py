#!/usr/bin/env python3

#  Mediacom Internet Data Usage Monitor & Alert

#  Copyright (C) 2020  Claus Niesen
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import dash
import dash_core_components as dcc
import dash_html_components as html
import flask
import sqlite3


def read_data_from_database(data):
    data['datetime'].clear()
    data['total'].clear()
    data['upload'].clear()
    data['download'].clear()
    data['allowance'].clear()
    data['allowance_to_day'].clear()
    conn = sqlite3.connect('MediacomUsage.db')
    cur = conn.cursor()
    cur.execute('SELECT DATETIME, TOTAL, UPLOAD, DOWNLOAD, ALLOWANCE, ALLOWANCE_TO_DAY FROM USAGE ORDER BY DATETIME ASC')
    rows = cur.fetchall()
    for row in rows:
        data['datetime'].append(row[0])
        data['total'].append(row[1])
        data['upload'].append(row[2])
        data['download'].append(row[3])
        data['allowance'].append(row[4])
        data['allowance_to_day'].append(row[5])


def make_annotations(data):
    annotations = []
    data_length = len(data['datetime'])
    for i in range(data_length):
        if (i == data_length -1) or (data['datetime'][i][0:10] != data['datetime'][i + 1][0:10]):
            annotations.append({
                'x': data['datetime'][i],
                'y': data['total'][i],
                'yshift': 50,
                'text': str(data['total'][i]) + " GB",
                'textangle': 270,
                'showarrow': False,
            })
    return annotations


def serve_layout():
    read_data_from_database(data)
    annotations = make_annotations(data)

    return html.Div(children=[
    html.H1(children='Mediacom Internet Data Usage'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': data['datetime'], 'y': data['upload'], 'type': 'bar', 'marker': {'color': 'blue'}, 'name': 'Upload'},
                {'x': data['datetime'], 'y': data['download'], 'type': 'bar', 'marker': {'color': 'green'}, 'name': 'Download'},
                {'x': data['datetime'], 'y': data['allowance_to_day'], 'mode': 'lines', 'marker': {'color': 'gray'}, 'name': 'Daily Allowance'},
                {'x': data['datetime'], 'y': data['allowance'], 'mode': 'lines',  'marker': {'color': 'red'}, 'name': 'Data Allowance'},
                {'x': data['datetime'], 'y': data['total'], 'mode': 'none', 'name': 'Total', 'texttemplate': '%{y}', 'showlegend': False}
            ],
            'layout': {
                'title': 'Mediacom Internet Data Usage',
                'barmode': 'stack',
                'hovermode': 'x unified',
                'hoverlabel': {
                    'font': {
                        'size': 12
                    }
                },
                'xaxis': {
                    'title': '',
                },
                'yaxis': {
                    'title': '',
                    'ticksuffix': ' GB',
                    'fixedrange': True
                },
                'font': {
                    'size': 16
                },
                'annotations': annotations
            }
        },
        config={
            'scrollZoom': True,
            'displaylogo': False
        }
    )
])


server = flask.Flask(__name__) # define flask app.server

data = {
    'datetime': [],
    'total': [],
    'upload': [],
    'download': [],
    'allowance': [],
    'allowance_to_day': []
}

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, server=server) # call flask server

app.layout = serve_layout