import time
import dash
from dash import callback, html, Input, Output, State, dcc
import dash_extensions as de
from dash.exceptions import PreventUpdate
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import json

def getUserInputPopupLayout():
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(id="user_input_popup_title", children="Header")),
            dbc.ModalBody(id="user_input_popup_body",
                          children = [
                              html.Div(
                                  id="user_input_popup_question",
                                  className="question-box",
                              ),
                              dcc.Input(
                                  id="user_input_popup_response",
                                  type="text",
                                  placeholder="Enter response here...",
                              )
                          ]),
            dbc.ModalFooter(
                dbc.Button("Send", id="user_input_popup_send", className="ms-auto", n_clicks=0)
            ),
        ],
        id="user_input_popup",
        is_open=False,
        size="lg"
    )


@callback( Output("user_input_popup", "is_open", allow_duplicate=True),
           Output("user_input_popup_title", "children"),
           Output("user_input_popup_question", "children"),
           Input("ws", "message"),
           prevent_initial_call=True
          )
def userInputPopup(server_message):
    if server_message and (j := json.loads(server_message['data']) )['task'] == 'user_input_popup':
        data = json.loads(j['content'])
        return True, data['title'], data['query']
    raise PreventUpdate


@callback( Output("ws","send",allow_duplicate=True),
           Output("user_input_popup", "is_open"),
           Output("user_input_popup_response", "value"),
           Input("user_input_popup_send", "n_clicks"),
           State("user_input_popup_response", "value"),
           prevent_initial_call=True
           )
def sendUserInputPopupResponse(n_clicks, response):
    if n_clicks and n_clicks > 0:
        return json.dumps({ "task" : "user_input_popup_response", "content" : response, "nonce": time.time_ns()  }), False, "Enter response here..."
    raise PreventUpdate




