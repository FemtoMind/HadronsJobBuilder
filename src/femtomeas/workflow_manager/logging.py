from femtomeas.meas_config_agent.common import cmdlinePrint

#Control over the function used for workflow manager logging
wfman_log_func = cmdlinePrint

def wfmanLog(*args, **kwargs):
    """
    Function employed by the workflow manager to output log information
    Default to cmdline but can be overridden
    """
    wfman_log_func(*args, *kwargs)

#Control over the function used for workflow API logging
api_log_func = cmdlinePrint

def wfapiLog(*args, **kwargs):
    """
    Function employed by the workflow api to output log information
    Default to cmdline but can be overridden
    """
    api_log_func(*args, *kwargs)




