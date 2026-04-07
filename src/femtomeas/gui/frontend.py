import time
import dash
from dash import callback, html, Input, Output, State, dcc
from dash_chat import ChatComponent
import dash_extensions as de
from dash.exceptions import PreventUpdate
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import json

app_dash = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

#                     )#   , external_stylesheets=[dbc.themes.SLATE]) #mount on / instead


chat_tab = dbc.Container(
    [
        dbc.Card(
            dbc.CardBody(
                [
                    dbc.Label("State file", html_for="state-file"),
                    dbc.Input(
                        id="state-file",
                        type="text",
                        placeholder="ckpoint_state.json",
                        value="",
                        debounce=True,
                    ),
                    dbc.Checklist(
                        id="reload-state",
                        options=[{"label": "Reload the state file if it exists", "value": "reload"}],
                        value=[],
                        switch=True,
                        className="mt-3",
                    ),
                    dbc.Button(
                        "Start agent",
                        id="start-agent",
                        color="primary",
                        className="mt-3",
                    )
                ]
            ),
            className="mb-3",
        ),
        html.Div(
            id="chat-wrapper",
            style={"display": "none"},
            children=[
                ChatComponent(
                    id="chat-component",
                    messages=[],
                    class_name="my-chat",
                )
            ],
        ),
    ],
    fluid=True,
    className="py-3",
)

job_tab = dbc.Container(
    [
        dag.AgGrid(
            id="transfer_monitor",
            columnDefs=[
                {"field": "ID"},
                {"field": "origin"},
                {"field": "destination"},
                {"field": "status"},
            ],
        )
    ],
    fluid=True,
    className="py-3",
)

app_dash.layout = html.Div([
    de.WebSocket(url="ws://localhost:8050/ws", id="ws"),
    dcc.Tabs(id="tabs", value="chatbot", children=[
        dcc.Tab(label="Workflow Creation Agent", value="chatbot"),
        dcc.Tab(label="Job Monitor", value="job_status")
    ]),
    html.Div(id="chat-tab-pane", children=chat_tab),
    html.Div(id="job-tab-pane", children=job_tab)
])

@callback(
    Output("chat-tab-pane", "style"),
    Output("job-tab-pane", "style"),
    Input("tabs", "value"),
)
def toggle_tabs(active_tab):
    if active_tab == "chatbot":
        return {"display": "block"}, {"display": "none"}
    return {"display": "none"}, {"display": "block"}


@callback(
    Output("chat-wrapper", "style"),
    Output("start-agent", "disabled"),
    Output("ws","send",allow_duplicate=True),
    Input("start-agent", "n_clicks"),
    State("state-file", "value"),
    State("reload-state", "value"),
    prevent_initial_call=True,
)
def start_agent(n_clicks, state_file, reload_values):
    if not n_clicks:
        raise PreventUpdate

    state_file = (state_file or "").strip() or "ckpoint_state.json"
    reload_state = "reload" in (reload_values or [])

    agent_config = {"state_file": state_file, "reload_state": reload_state}
    
    return {"display": "block"}, True, json.dumps({'task' : 'start', 'content' : json.dumps(agent_config)})

@callback( Output("chat-component", "messages", allow_duplicate=True),
           Input("ws", "message"),
           State("chat-component", "messages"),
           prevent_initial_call=True
          )
def receiveAgentResponse(server_message, messages):
    if server_message and (j := json.loads(server_message['data']))['task'] == 'agent_output':
        agent_message = j['content']        
        print("RECEIVED AGENT RESPONSE", agent_message)
        return messages + [ { "role" : "assistant", "content" : agent_message } ]
    raise PreventUpdate


@callback(
    [ Output("chat-component", "messages"), Output("ws","send",allow_duplicate=True) ],
    Input("chat-component", "new_message"),
    State("chat-component", "messages"),
    prevent_initial_call=True,
)
def handleUserInput(new_message, messages):
    if new_message == None:
        raise PreventUpdate
    
    print("USER MESSAGE",new_message)    
    return messages + [ new_message ], json.dumps({ "task" : "user_response", "content" : new_message['content']})


