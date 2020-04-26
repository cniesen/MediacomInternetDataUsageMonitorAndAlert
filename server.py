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

def read_data_from_database():
    conn = sqlite3.connect('MediacomUsage.db')
    cur = conn.cursor()
    cur.execute('SELECT DATETIME, TOTAL, UPLOAD, DOWNLOAD, ALLOWANCE FROM USAGE ORDER BY DATETIME ASC')
    rows = cur.fetchall()
    datetime = []
    total = []
    upload = []
    download = []
    allowance = []
    for row in rows:
        datetime.append(row[0])
        total.append(row[1])
        upload.append(row[2])
        download.append(row[3])
        allowance.append(row[4])
    return {
        'datetime': datetime,
        'total': total,
        'upload': upload,
        'download': download,
        'allowance': allowance
    }


server = flask.Flask(__name__) # define flask app.server

data = read_data_from_database()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

#app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, server=server) # call flask server

app.layout = html.Div(children=[
    html.H1(children='Mediacom Internet Data Usage'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': data['datetime'], 'y': data['upload'], 'type': 'bar', 'name': 'Upload', 'hovertemplate': 'Upload: %{y}'},
                {'x': data['datetime'], 'y': data['download'], 'type': 'bar', 'marker': {'color': 'green', 'title': {'text': 'hey'}}, 'hovertemplate': 'Download: %{y}', 'name': 'Download'},
                {'x': data['datetime'], 'y': data['total'], 'mode': 'text', 'name': 'Total', 'texttemplate': '%{y}', 'showlegend': False, 'textposition': 'top center'},
                {'x': data['datetime'], 'y': data['allowance'], 'mode': 'lines',  'marker': {'color': 'red'}, 'name': 'Data Allowance', 'hovertemplate': 'Allowance: %{y}'}
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
                    'ticksuffix': ' GB'
                },
                'font': {
                    'size': 16
                }
            }
        },
        config={
            'scrollZoom': True,
            'displaylogo': False
        }
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)