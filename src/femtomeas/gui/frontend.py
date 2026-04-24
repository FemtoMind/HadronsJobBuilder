import time
import dash
from dash import callback, html, Input, Output, State, dcc
from dash_chat import ChatComponent
import dash_extensions as de
from dash.exceptions import PreventUpdate
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import json
from femtomeas.workflow_manager.manager_config import parseManagerConfigStr
import base64
from .utils import make_scroll_callback

#app_dash = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app_dash = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

from .frontend_content.configure_page import *
from .frontend_content.chat_tab import *
from .frontend_content.workflow_monitor import *
from .frontend_content.user_input_popup import *

app_dash.layout = html.Div([
    getUserInputPopupLayout(),
    de.WebSocket(url="ws://localhost:8050/ws", id="ws"),
    html.Div(id="startup-controls", children=getConfigurePageLayout() ),
    
    html.Div(id="tabs-wrapper", children=[
      dcc.Tabs(id="tabs"),
      html.Div(id="chat-tab-pane", children=getChatTabContent() ),
      html.Div(id="job-tab-pane", children=getJobMonitorLayout() )    
    ], style={"display": "none"}),

    html.Div(id="error-display-wrapper",
             children = [
                 html.H5("Server errors", className="mb-2"),
                 dcc.Textarea(
                        id='error-display',
                        disabled=True,
                        readOnly=True
                    )
                 ],
             style={"display": "none"}
             )
             
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
    Output("ws","send",allow_duplicate=True), #sent start signal to backend
    Input("start", "n_clicks"),
    State("state-file", "value"),
    State("options-switches", "value"),
    State("wfman-config-store", "data"),
    prevent_initial_call=True,
)
def start_agent(n_clicks, state_file, option_values, wfman_config):
    if not n_clicks:
        raise PreventUpdate

    option_values = option_values or []
    
    state_file = (state_file or "").strip() or "ckpoint_state.json"
    reload_state = "reload_state" in option_values
    use_agent = "use_agent" in option_values
    use_workflow_manager = "use_workflow_manager" in option_values

    workflow_config = {"state_file": state_file, "reload_state": reload_state, "use_agent" : use_agent, "use_workflow_manager" : use_workflow_manager, "workflow_manager_config" : wfman_config["config"] }

    tabs_children, tabs_value = setupTabs(use_agent, use_workflow_manager)
    
    return {"display": "block"}, tabs_children, tabs_value,  {"display" : "none" },  json.dumps({'task' : 'start', 'content' : json.dumps(workflow_config)})


make_scroll_callback('wfman-log', app_dash)
make_scroll_callback('wfapi-log', app_dash)
