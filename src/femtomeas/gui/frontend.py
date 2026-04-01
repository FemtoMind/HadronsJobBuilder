import time
import dash
from dash import callback, html, Input, Output, State, dcc
from dash_chat import ChatComponent
import dash_extensions as de
from dash.exceptions import PreventUpdate

app_dash = dash.Dash(__name__) #mount on / instead

app_dash.layout = html.Div([
    ChatComponent(
        id="chat-component",
        messages=[],
    ),
    de.WebSocket(url="ws://localhost:8050/ws", id="ws")
])

@callback( Output("chat-component", "messages", allow_duplicate=True),
           Input("ws", "message"),
           State("chat-component", "messages"),
           prevent_initial_call=True
          )
def receiveAgentResponse(agent_message, messages):
    if agent_message:
        print("RECEIVED AGENT RESPONSE", agent_message)
        return messages + [ { "role" : "assistant", "content" : agent_message['data'] } ]
    raise PreventUpdate


@callback(
    [ Output("chat-component", "messages"), Output("ws","send",allow_duplicate=True) ],
    Input("chat-component", "new_message"),
    State("chat-component", "messages"),
    prevent_initial_call=True,
)
def handleUserInput(new_message, messages):
    print("USER MESSAGE",new_message)    
    return messages + [ new_message ], new_message['content']
