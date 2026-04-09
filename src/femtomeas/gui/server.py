from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi import WebSocket, WebSocketDisconnect

import io
import time
import asyncio
import websockets
import json

app = FastAPI()

main_loop = None
@app.on_event("startup")
async def capture_loop():
   global main_loop
   main_loop = asyncio.get_running_loop()

agent_print_queue = asyncio.Queue()

def agentPrint(*args, **kwargs):
    buf = io.StringIO()
    print(*args, *kwargs, file=buf)
    msg = buf.getvalue()
    
    asyncio.run_coroutine_threadsafe(agent_print_queue.put(msg), main_loop).result()
    time.sleep(0.3) #allows successive calls to print to all render correctly

agent_recv_user_queue = asyncio.Queue()
    
def agentQuery(query):
    asyncio.run_coroutine_threadsafe(agent_print_queue.put(query), main_loop).result()
    return asyncio.run_coroutine_threadsafe(agent_recv_user_queue.get(), main_loop).result().strip()

wfman_log_queue = asyncio.Queue()

def workflowManagerLogGUI(*args, **kwargs):
    buf = io.StringIO()
    print(*args, *kwargs, file=buf)
    msg = buf.getvalue()

    asyncio.run_coroutine_threadsafe(wfman_log_queue.put(msg), main_loop).result()
    time.sleep(0.3) #allows successive calls to print to all render correctly

wfapi_log_queue = asyncio.Queue()

def workflowAPIlogGUI(*args, **kwargs):
    buf = io.StringIO()
    print(*args, *kwargs, file=buf)
    msg = buf.getvalue()

    asyncio.run_coroutine_threadsafe(wfapi_log_queue.put(msg), main_loop).result()
    time.sleep(0.3) #allows successive calls to print to all render correctly


    
server_workflow = None

def setServerWorkflow(workflow):
    global server_workflow
    server_workflow = workflow

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    assert server_workflow != None
    
    await websocket.accept()
    global agent_print_queue, agent_recv_user_queue, wfman_log_queue, wfapi_log_queue
    agent_print_queue = asyncio.Queue() #reset
    agent_recv_user_queue = asyncio.Queue()
    wfman_log_queue = asyncio.Queue()
    wfapi_log_queue = asyncio.Queue()
    
    #Task that sends agent output to the frontend
    async def agent_print_sender():
        while True:
            msg = await agent_print_queue.get()
            await websocket.send_json({"task": "agent_output", "content": msg})

    #Task that sends worflow manager log output to frontend
    async def wfman_log_sender():
        while True:
            msg = await wfman_log_queue.get()
            await websocket.send_json({"task": "wfman_log", "content": msg})

    #Task that sends worflow API log output to frontend
    async def wfapi_log_sender():
        while True:
            msg = await wfapi_log_queue.get()
            await websocket.send_json({"task": "wfapi_log", "content": msg})

            
    start_event = asyncio.Event()

    #Arguments to agent start
    workflow_config = None
   
    #Task that receives input from the frontend and redirects as appropriate            
    async def receiver():
        while True:
            msg = await websocket.receive_json()
            if msg['task'] == 'user_response':
               await agent_recv_user_queue.put(msg['content'])
            elif msg['task'] == 'start':
               nonlocal workflow_config
               workflow_config = json.loads(msg['content'])
               start_event.set()
               
    try:
        agent_print_task = asyncio.create_task(agent_print_sender())
        wfman_log_task = asyncio.create_task(wfman_log_sender())
        wfapi_log_task = asyncio.create_task(wfapi_log_sender())
        receiver_task = asyncio.create_task(receiver())

        await start_event.wait()
        await main_loop.run_in_executor(None, server_workflow, workflow_config)
        
        agent_print_task.cancel()
        wfman_log_task.cancel()
        wfapi_log_task.cancel()
        receiver_task.cancel()
        
        while True:
            await asyncio.sleep(3600)
        

    except WebSocketDisconnect:
        print("Client disconnected")
