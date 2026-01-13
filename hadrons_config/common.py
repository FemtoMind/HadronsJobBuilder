from langchain.tools import tool
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
    AIMessage
)
import json
import io

def storeGetList(key, store):
    l = store.get( ("ns",),key)
    if l == None:
        return []
    ll = l.value
    assert isinstance(ll, list)
    return ll

def storeListAppend(key, value, store):
    ll = storeGetList(key,store)
    ll.append(value)
    store.put(("ns",), key, ll)


use_auto_eval = False    
auto_eval_messages = None
auto_eval_ostrm = None  
auto_eval_model = None
auto_eval_sys = None

def enableAutoEvaluate(model, sys):
    global use_auto_eval
    global auto_eval_model
    global auto_eval_sys
    global auto_eval_messages
    global auto_eval_ostrm
    use_auto_eval = True
    auto_eval_model = model
    auto_eval_sys = sys
    auto_eval_ostrm = io.StringIO()
    auto_eval_messages = []
    
def Print(*args, **kwargs):
    if use_auto_eval == True:
        global auto_eval_ostrm
        print(*args, *kwargs, file=auto_eval_ostrm)
    else:
        print(*args, *kwargs)
        
def Input(query):
    if use_auto_eval == True:
        global auto_eval_ostrm
        global auto_eval_messages
        auto_eval_messages.append(HumanMessage(auto_eval_ostrm.getvalue()))
        auto_eval_ostrm.close()
        auto_eval_ostrm = io.StringIO()

        auto_eval_messages.append(HumanMessage(query))
        print("TO EVAL AGENT:", auto_eval_messages[-2].content,"\n",auto_eval_messages[-1].content)
        
        msg = [ SystemMessage(auto_eval_sys) ] + auto_eval_messages 
        ret = auto_eval_model.invoke(msg).content
        print("EVAL AGENT RESPONSE:", ret)
        return ret
    else:        
        return input(query + " : ").strip()

        
@tool
def getUserInput(query: str) -> str:
    """
    Get a response from the user to a query.
    Args:
       query: The question to pose to the user
    Return:
       Return the user's response
    """    
    return Input(query + " : ")

@tool
def provideInformationToUser(description: str):
    """
    Provide some text information to the user
    """
    Print(description)

def queryYesNo(query: str)->bool:
    result = ""
    while(result not in ["y","n"]):    
        result = Input(query)
    return True if result == "y" else False
        

def callModelWithStructuredOutput(model, sys_prompt : str, other_messages : list[BaseMessage], schema : BaseModel, use_langchain_structured_output_method = True)-> BaseModel:
    """
    Wrapper function for calling an LLM model with structured output
    """
    if use_langchain_structured_output_method:
        messages = [ SystemMessage(sys_prompt) ] + other_messages
        ret = None
        retries=0
        while ret == None:
            if retries > 10:
                raise Exception(f"Obtained a null result from the model. Attempted 10 times. If this happens it might be because the last message is an AIMessage not a HumanMessage. Models seem to implicitly rely on this! Message history: {messages}") 
                
                
            ret = model.with_structured_output(schema, method="function_calling").invoke(messages) #using method=json_schema (default I think) produces garbled output for the oss-120b model for some reason; function_calling seems more reliable
            retries+=1
            
        return ret
        
    else:
        sys_prompt += """
Your output must be in JSON format. Use the following schema:
""" + json.dumps(schema.model_json_schema())
        
        messages = [ SystemMessage(sys_prompt) ] + other_messages
        obj = None
        valid=False
        tries=0
        while(valid == False):
            tries += 1
            if tries == 10:
                break
            
            try:
                response = model.invoke(messages)
                obj = schema.model_validate_json(response.content)
                valid=True
            except Exception as e:
                messages.append(HumanMessage(f"Your previous response did not parse correctly for the following reason: {str(e)}"))

        if valid == False:
            raise Exception("Not able to parse output correctly within 10 tries")

        return obj

def spaceSeparateSeq(seq):
    r = ""
    for i, v in enumerate(seq):
        r = r + str(v) + ("" if i==len(seq)-1 else " ")
    return r
