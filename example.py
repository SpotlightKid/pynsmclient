#!/usr/bin/env python3
"""
Author: Nils Gey ich@nilsgey.de http://www.nilsgey.de  April 2013.

Non Session Manager Author:

Jonathan Moore Liles <male@tuxfamily.org> http://non.tuxfamily.org/nsm/

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


Quick Guide
-----------

How to get Non Session Manager support in your Python application.

0. You can try to start this client via the NSM server right now. Which will
   not work: I have planted undefined Python variable names in this file.
   Replace them all, make the program runnable at all, and you have entered all
   strictly necessary information.

1. Not so Quick behavior guidelines. These are non-negotiable.

   http://non.tuxfamily.org/nsm/API.html

   If you can't  implement them easily consider implementing a special session
   mode.

2. Below you'll find one dictionary with general information about your program
   and two blocks of functions. One is mandatory, the other is optional. See
   the comments to learn more about what your functions must accept and return.

3. Change the ``app_name`` string in the ``nsmclient.init()`` call below.

   This string is very important and used by NSM to generate your save file
   names. If you change the ``app_name`` NSM will think this is a different
   program. So set it to your real program name and don't worry about multiple
   instances.

Calling the ``nsmclient.init()`` function returns two objects. The first is an
instance of the ``NSMClient`` class. You only need this if you want to send
messages from your client to the NSM server. The functions, which can be be
executed directly by your program are::

    # Report percentage during load, save and other heavy operations
    client.updateProgress(value from 0.1 to 1.0)
    # Inform NSM of the save status. Are there unsaved changes?
    client.setDirty(True or False)
    client.sendError(errorCode or String, message string)

Secondly, more importantly, is the event loop processor, which checks for new
messages and queues outgoing ones. See the bottom of this example client.

"""

# You need pyliblo for Python 3 for nsmclient and of course an installed and
# running non-session-manager
import nsmclient

# All capabilities default to False.
# Just change a value to True if your program can do that.
capabilities = {
    "switch": False,        # client is capable of responding to multiple
                            # `open` messages without restarting
    "dirty": False,         # client knows when it has unsaved changes
    "progress": False,      # client can send progress updates during
                            # time-consuming operations
    "message": False,       # client can send textual status updates
    "optional-gui": False,  # client has an optional GUI
}

"""\
``requiredFunctions``
---------------------

All message handler callback functions receive the ``NSMClient`` instance
as the first positional argument.

The ``save`` function must accept one additional argument and ``open`` two:

``session_path``: both the ``open`` and the ``save `` callback receive a path
prefix as the second positional argument. NSM never creates directories or
paths. It is up to you what you do with the path. Append your file extension or
use it as a directory (the directory approach is recommended). You only have to
remember your naming scheme and use it every time. For example it is safe, if
your program is in session mode, to always just use
``"receivedPath/session.yourExtension"`` since it will be a unique path. The
important part is that the filename, once it was created, must never change
again.

``client_id``: ``open`` must accept a ``client_id`` string as the third
positional argument. JACK ports may not be created until after ``open`` was
called and must be prefixed with the received ``client_id``. Since ``open`` can
reload other states (switching clients) this is done after ``open``, and not
through the nsm welcome message.

Open and Save must return two values::

    return bool, string

Bool is ``True`` or ``False``, depending on whether the open function succeeded
or not.

If ``True``: string is just the file name WITHOUT the path. It will be extended
by nsmclient and a ``"/path/foo.save successful"``, save or open, message will
be given out.

If ``False``: string is a message  which will be used to inform nsm and the
user what exactly went wrong (file unreadable, wrong format etc.). Please
include all needed information including the full filepath.

Important: Do not register any JACK clients and ports before a file was opened.
After ``open`` was called, the ``state.client_id`` attribute will be set on the
``NSMClient`` instance. This must be used as the prefix for your JACK clients
(client, not ports). This also enables your application to be used with
multiple instances.

Don't ask the user for confirmation or do anything that pauses the save
process.

"""

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


"""\
Optional functions
------------------

All message handler callback functions receive the ``NSMClient`` instance
as the first positional argument.

Leave the dict-value as None to ignore a function.

``quit`` should be a function that cleans up. Do whatever you must do. Shutdown
your JACK engine, send a final message to a webserver or whatever makes your
program special. The program will exit anyway, even if you don't implement this
extra quit hook. Do NOT warn for unsaved changes etc. Quit means quit. No
questions asked.

``show_gui`` and ``hide_gui`` will be ignored if you did not set
``"optional-gui"`` to True in the capabilities dict. If you have an optional
GUI this enables the session manager to tell your program to show and hide your
GUI. Obviously in this case a hidden GUI should not stop the program. If you
have, for example, a synthesizer with midi in, it should still react and
produce sound.

``session_loaded``: The intent is to signal to clients which may have some
interdependence (say, peer to peer OSC connections) that the session is fully
loaded and all their peers are available.

Do not use it to auto-connect JACK connections. You do not need to implement
auto-conncect from within a session! JACK connections are stored in a seperate
NSM client which belongs to the session.

"""

optionalFunctions = {
    # Accept one argument (client). Return value is ignored.
    "quit": None,
    # Accept one argument (client). Return True or False.
    "show_gui": None,
    # Accept one argument (client). Return True or False.
    "hide_gui": None,
    # Accept one argument (client). Return value is ignored.
    "session_loaded": None,
}

client = nsmclient.init(
    app_name=YourApplicationName,
    capabilities=capabilities,
    requiredFunctions=requiredFunctions,
    optionalFunctions=optionalFunctions
)

"""\
Client message functions
------------------------

Functions for your program to send information to the NSM server::

    # Report percentage during load, save and other heavy operations:
    client.update_progress(value from 0.1 to 1.0)

    # Inform NSM of the save status. Are there unsaved changes?
    client.set_dirty(True or False)

    # For a list of error codes: http://non.tuxfamily.org/nsm/API.html#n:1.2.5.
    client.send_error(message[, code=errorCode or String][, path=String])


Event loop
----------

The ``NSMCLient`` handles OSC messages in the background via a
``liblo.ServerThread``. Your client just needs to stay alive by entering some
kind of loop. When your client receives a SIGTERM signal from the NSM server,
the quit callback is called, the OSC server thread is stopped and then the
client exits.

"""

import time

while True:
    time.sleep(1)
