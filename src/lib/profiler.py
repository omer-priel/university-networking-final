# Profiler for chrome://tracing

from typing import Callable
import calendar
import time
import threading
import traceback
import os
import os.path
from io import TextIOWrapper

# config
PROFILE_PATH = "profiles/profile.json"

# globals
isFirstEvent = True

profileStream: TextIOWrapper = ...  # type: ignore[assignment]

def use_profiler(entryPoint: Callable[[], None]):
    global profileStream

    # remove the last profile.json and create the parent directory if needed
    if os.path.isfile(PROFILE_PATH):
        os.remove(PROFILE_PATH)
    elif not os.path.isdir(os.path.dirname(PROFILE_PATH)):
        os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)

    # create the profile file
    profileStream = open(PROFILE_PATH, "w")
    profileStream.write('{"displayTimeUnit":"ms","otherData": {},"traceEvents":[')

    # call the program
    try:
        entryPoint()
    except BaseException:
        traceback.print_exc()
    finally:
        # close the profile file
        profileStream.write(']}')
        profileStream.close()

def profiler_add_event(name: str):
    global isFirstEvent

    if (isFirstEvent):
        isFirstEvent = False
    else:
        profileStream.write(',')

    name = name.replace('"', "'")
    ts = calendar.timegm(time.gmtime())
    tid = threading.current_thread().native_id
    profileStream.write('{"name": {}, "cat": "Event", "ph": "X", "dur": 100, "ts": {}, "pid": 0, "tid": {} }'.format(name, ts, tid))

def profiler_add_scope(name: str, startTs: int, endTs: int):
    global isFirstEvent

    if (isFirstEvent):
        isFirstEvent = False
    else:
        profileStream.write(',')

    name = name.replace('"', "'")
    tid = threading.current_thread().native_id
    profileStream.write('{"name": {}, "cat": "Scope", "ph": "X", "dur": {}, "ts": {}, "pid": 0, "tid": {} }'.format(name, endTs - startTs, startTs, tid))

def profiler_scope(function: Callable, scopeName: str | None = None):
    def wrapper(*args,**kwargs):

        startTs = calendar.timegm(time.gmtime())
        ret = function(*args,**kwargs)
        endTs = calendar.timegm(time.gmtime())

        if not scopeName:
            scopeName = function.__name__

        profiler_add_scope(scopeName, startTs, endTs)

        return ret

    return wrapper
