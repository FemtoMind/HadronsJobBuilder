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


startup_controls = dbc.Container(
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
                        id="options-switches",
                        options=[{"label": "Reload the state file if it exists", "value": "reload_state"},
                                 {"label": "Run the workflow agent", "value": "use_agent"},
                                 {"label": "Run the workflow manager", "value": "use_workflow_manager"}
                                 ],
                        value=["use_agent", "use_workflow_manager"],
                        switch=True,
                        className="mt-3",
                    ),
                    dbc.Button(
                        "Start",
                        id="start",
                        color="primary",
                        className="mt-3",
                    )
                ]
            ),
            className="mb-3",
        ),
    ],
    fluid=True,
    className="py-3",
)


chat_tab = dbc.Container(
    [
      ChatComponent(
        id="chat-component",
        messages=[],
        class_name="my-chat",
      )
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
    html.Div(id="startup-controls", children=startup_controls),
    
    html.Div(id="tabs-wrapper", children=[
      dcc.Tabs(id="tabs"),
      html.Div(id="chat-tab-pane", children=chat_tab),
      html.Div(id="job-tab-pane", children=job_tab)    
    ], style={"display": "none"}),

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

def setupTabs(use_agent: bool, use_wflow_man : bool):
    tabs_children = []
    if use_agent and use_wflow_man:
        tabs_children.append( dcc.Tab(label="Workflow Creation Agent", value="chatbot") )        
        tabs_children.append( dcc.Tab(label="Job Monitor", value="job_status") )
    tabs_value = "chatbot" if use_agent else "job_status"
    return tabs_children, tabs_value

@callback(
    Output("tabs-wrapper", "style"), #switch on the tabs
    Output("tabs", "children"), #populate the active tabs
    Output("tabs", "value"), #set default tab
    Output("startup-controls", "style"), #hide control panel
    Output("start", "disabled"), #disable start button
    Output("ws","send",allow_duplicate=True), #sent start signal to backend
    Input("start", "n_clicks"),
    State("state-file", "value"),
    State("options-switches", "value"),
    prevent_initial_call=True,
)
def start_agent(n_clicks, state_file, option_values):
    if not n_clicks:
        raise PreventUpdate

    option_values = option_values or []
    
    state_file = (state_file or "").strip() or "ckpoint_state.json"
    reload_state = "reload_state" in option_values
    use_agent = "use_agent" in option_values
    use_workflow_manager = "use_workflow_manager" in option_values
    
    workflow_config = {"state_file": state_file, "reload_state": reload_state, "use_agent" : use_agent, "use_workflow_manager" : use_workflow_manager }

    tabs_children, tabs_value = setupTabs(use_agent, use_workflow_manager)
    
    return {"display": "block"}, tabs_children, tabs_value,  {"display" : "none" },  True,  json.dumps({'task' : 'start', 'content' : json.dumps(workflow_config)})

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


