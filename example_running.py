#!/usr/bin/env python3

import logging

from os.path import join
from random import randint
from time import sleep

# You need pyliblo for Python 3 for nsmclient and of course an installed and
# running non-session-manager
import nsmclient


# All capabilities default to False.
# Just change a value to True if your program can do that.
capabilities = {
    "switch": False,        # client is capable of responding to multiple
                            # `open` messages without restarting
    "dirty": False,         # client knows when it has unsaved changes
    "progress": True,       # client can send progress updates during
                            # time-consuming operations
    "message": True,        # client can send textual status updates
    "optional-gui": False,  # client has an optional GUI
}


def myLoadFunction(client, session_path, client_id):
    print("myLoadFunction", session_path, client_id)
    """Pretend to load a file."""
    return True, "foo.save"


def mySaveFunction(client, session_path):
    """Pretend to save a file."""
    print("mySaveFunction", session_path)
    if randint(1, 5) == 3:  # 1 in a 5 chance to fail
        return False, "Failed to save '{}' because an RNG went wrong".format(
            join(session_path, "foo.save"))
    else:
        return True, "foo.save"


requiredFunctions = {
    "open": myLoadFunction,
    # Accept two parameters.
    # Return two values: a bool and a status string.
    # Otherwise you'll get a message that does not help at all:
    #
    #    Exception TypeError: "'NoneType' object is not iterable" in
    #    'liblo._callback' ignored"
    "save": mySaveFunction,
    # Accept one parameter.
    # Return two values: a bool and a status string.
    # Otherwise you'll get a message that does not help at all:
    #
    #    Exception TypeError: "'NoneType' object is not iterable" in
    #    'liblo._callback' ignored
}


def quitty(client):
    client.send_message("Preparing to quit. Wait for progress to finish.")
    # Fake quit process
    client.update_progress(0.1)
    sleep(0.5)
    client.update_progress(0.5)
    sleep(0.5)
    client.update_progress(0.9)
    client.update_progress(1.0)
    return True


optionalFunctions = {
    # Accept one argument (client). Return value is ignored.
    "quit": quitty,
    # Accept one argument (client). Return True or False.
    "show_gui": None,
    # Accept one argument (client). Return True or False.
    "hide_gui": None,
    # Accept one argument (client). Return value is ignored.
    "session_loaded": None,
}


logging.basicConfig(level=logging.DEBUG,
                    format="[%(name)s] %(levelname)s: %(message)s")

client = nsmclient.init(
    app_name="PyNSMClient",
    capabilities=capabilities,
    requiredFunctions=requiredFunctions,
    optionalFunctions=optionalFunctions,
    executable="testpynsm"
)

while True:
    sleep(1)
