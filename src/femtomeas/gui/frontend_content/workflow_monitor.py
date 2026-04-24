import time
import dash
from dash import callback, html, Input, Output, State, dcc
from dash_chat import ChatComponent
import dash_extensions as de
from dash.exceptions import PreventUpdate
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import json
from ..utils import make_scroll_callback

def getJobMonitorLayout():
    job_tab = dbc.Container(
        [
            # Row 1: Tables
        dbc.Row(
            [                
                dbc.Col([
                    html.H5("Transfer Monitor", className="mb-2"),
                    dag.AgGrid(
                        id="transfer-monitor",
                        columnDefs=[
                            {"field": "job ID", "flex" : 1},
                            {"field": "api ID", "flex" : 1},
                            {"field": "origin", "flex" : 2},
                            {"field": "destination", "flex" : 3},
                            {"field": "status", "flex" : 1},
                        ],                        
                        defaultColDef={
                            "wrapText": True,
                            "autoHeight": True,
                        },
                        getRowId="params.data['api ID']",
                        style={"height": 400, "width": "100%"},
                    )],
                        width=6,
                        ),
                dbc.Col([
                    html.H5("Compute Monitor", className="mb-2"),
                    dag.AgGrid(
                        id="compute-monitor",
                        columnDefs=[
                            {"field": "job ID", "flex" : 1},
                            {"field": "api ID", "flex" : 1},
                            {"field": "machine", "flex" : 1},
                            {"field": "queue", "flex" : 1},
                            {"field": "time", "flex" : 1},
                            {"field": "status", "flex" : 1},
                        ],
                        defaultColDef={
                            "wrapText": True,
                            "autoHeight": True,
                        },
                        getRowId="params.data['api ID']",
                        #columnSize="autoSize",
                        style={"height": 400, "width": "100%"},
                    )],
                        width=6,
                        ),
            ],
            className="mb-3",
        ),

        # Row 2: Logs
        dbc.Row(
            [
                dbc.Col([
                    html.H5("Workflow Manager Logs", className="mb-2"),
                    dcc.Textarea(
                        id='wfman-log',
                        style={'width': '100%', 'height': 300},
                        disabled=True,
                        readOnly=True
                    )],
                        width=6,
                        ),
                dbc.Col(
                    [
                        html.H5("API Logs", className="mb-2"),
                        dcc.Textarea(
                            id='wfapi-log',
                            style={'width': '100%', 'height': 300},
                            disabled=True,
                            readOnly=True
                        )],
                    width=6,
                ),
            ]
        ),
        ],
        fluid=True,
        className="py-3",
    )
    return job_tab




@callback( Output("wfman-log", "value"),
           Input("ws", "message"),
           State("wfman-log", "value")
          )
def receiveWfmanLogOutput(server_message, log):
    if server_message and (j := json.loads(server_message['data']))['task'] == 'wfman_log':
        return (log if log else "") + j['content']
    raise PreventUpdate

@callback( Output("wfapi-log", "value"),
           Input("ws", "message"),
           State("wfapi-log", "value")
          )
def receiveWfapiLogOutput(server_message, log):
    if server_message and (j := json.loads(server_message['data']))['task'] == 'wfapi_log':
        return (log if log else "") + j['content']
    raise PreventUpdate


@callback( Output("transfer-monitor", "rowTransaction"),
           Input("ws", "message")
          )
def addOrUpdateTransferEntry(server_message):
    if server_message and (j := json.loads(server_message['data']) )['task'] in ('add_transfer', 'update_transfer'):
        print("TRANSFER INSTRUCTION",j)
        content = json.loads(j['content'])
        
        row = { "job ID" : content['job_id'], "api ID" : content['api_key'], "origin" : content['origin'], "destination" : content['destination'], "status" : content['api_status'] }
        cmd = 'add' if j['task'] == 'add_transfer' else 'update'
        print("TRANSFER CMD",cmd,"UPDATED ROW",row)
        
        return { cmd : [ row ] }
    raise PreventUpdate


@callback( Output("compute-monitor", "rowTransaction"),
           Input("ws", "message")
          )
def addOrUpdateComputeEntry(server_message):
    if server_message and (j := json.loads(server_message['data']) )['task'] in ('add_compute', 'update_compute'):
        print("COMPUTE INSTRUCTION",j)
        content = json.loads(j['content'])
        
        row = { "job ID" : content['job_id'], "api ID" : content['api_key'], "machine" : content['machine'], "queue" : content['queue'], "time" : content['time'], "status" : content['api_status'] }
        cmd = 'add' if j['task'] == 'add_compute' else 'update'
        print("COMPUTE CMD",cmd,"UPDATED ROW",row)
        
        return { cmd : [ row ] }
    raise PreventUpdate


@callback( Output("error-display", "value"),
           Output("error-display", "style"),
           Output("error-display-wrapper", "style"),
           Input("ws", "message"),
           State("error-display", "value")
          )
def receiveServerError(server_message, log):
    if server_message and (j := json.loads(server_message['data']))['task'] == 'server_error':
        err = json.loads(j['content'])
        content = (log if log else "") + json.dumps(err,indent=4)
        lines = content.count("\n") + 1 if content else 1
        height = max(300, lines * 20)
        
        return content , {'width': '100%', 'height': height, 'color' : 'red'},   {"display" : "block"}
    raise PreventUpdate


