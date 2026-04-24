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

def getConfigurePageLayout():
    startup_controls = dbc.Container(
        [
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Label("State file", html_for="state-file"),
                        dcc.Store(id="wfman-config-store", storage_type="local"), #persist in browser cache
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
                        dcc.Upload(
                            id="wfman-config-upload",
                            children=dbc.Button(
                                id="wfman-config-upload-button",
                                #children="Choose the workflow manager configuration file (JSON)",
                                color="secondary",
                                className="mt-3",
                            ),
                            multiple=False,
                            style={"display": "inline-block"}
                        ),
                        dbc.Button(
                            "Clear cache",
                            id="clear-cache",
                            color="primary",
                            className="mt-3"
                        ),
                        dbc.Button(
                            "Start",
                            id="start",
                            color="primary",
                            className="mt-3"#,
                            #disabled=True #start disabled because use_workflow_manager is enabled by default and we need to upload a config file to use it
                        )
                    ]
                ),
                className="mb-3",
            ),
        ],
        fluid=True,
        className="py-3",
    )
    return startup_controls
    


@callback(
    Output("wfman-config-store", "clear_data"),
    Input("clear-cache", "n_clicks"), 
    prevent_initial_call=True
    )
def clear_wfman_cfg_cache(n_clicks):
    print("CLEAR CACHE TRIGGER")
    if n_clicks and n_clicks > 0:
        return True
    raise PreventUpdate

@callback(
    Output("wfman-config-store", "data"),
    Input("wfman-config-upload", "filename"),
    State("wfman-config-upload","contents"),
    prevent_initial_call=True)
def upload_wfman_cfg(filename, contents):
    if filename:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string).decode('utf-8')        
        config = parseManagerConfigStr(decoded)        
        return { "origin" : filename, "config" : config.model_dump_json() }
    raise PreventUpdate

@callback(
    Output("wfman-config-upload-button", "children"),
    Input("wfman-config-store", "data")
    )
def set_upload_button_text_to_filename(store_data):
    print("SET UPLOAD TRIGGER")
    if store_data:
        return store_data["origin"]
    else:
        return "Choose the workflow manager configuration file (JSON)"




#If we we have the use-workflow-manager toggle enabled, we cannot start unless the wfman configuration exists
@callback(
Output("start", "disabled"),
Input("options-switches","value"),
Input("wfman-config-store", "data"),
State("options-switches","value"),
State("wfman-config-store", "data"),
)
def disable_start_until_wfman_cfg_upload(option_values_trigger, store_trigger, options_values, store_data):   
    if "use_workflow_manager" in options_values and not store_data:
        return True
    else:
        return False
