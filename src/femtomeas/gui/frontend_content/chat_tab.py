import time
import dash
from dash import callback, html, Input, Output, State, dcc
from dash_chat import ChatComponent
import dash_extensions as de
from dash.exceptions import PreventUpdate
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import json

def getChatTabContent():
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
    return chat_tab

@callback( Output("chat-component", "messages", allow_duplicate=True),
           Input("ws", "message"),
           State("chat-component", "messages"),
           prevent_initial_call=True
          )
def receiveAgentResponse(server_message, messages):
    if server_message and (j := json.loads(server_message['data']))['task'] == 'agent_output':
        agent_message = j['content']        
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
    print("CHAT COMPONENT DETECTED USER RESPONSE", new_message['content'])
    
    return messages + [ new_message ], json.dumps({ "task" : "user_response", "content" : new_message['content'], "nonce": time.time_ns()  })  #use a timestamp to ensure each message is unique. This prevents the stupid socket library from dropping responses with the same content
