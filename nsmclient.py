# -*- coding: utf-8 -*-
"""A Python client library for the Non Session Management protocol.

Author: Nils Gey ich@nilsgey.de http://www.nilsgey.de  April 2013.

Heavily modified by: Christopher Arndt <chris@chrisarndt.de>

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

Usage:

Import this file from your python application with::

    import nsmclient

and then call ``nsmclient.init()`` with the right parameters.

See the file ``example.py`` in the source distribution for a detailed example
with extensive comments.

"""

import inspect
import logging
import os
import sys
import time

from os.path import abspath, basename, dirname, join
from signal import signal, SIGTERM

# You need pyliblo for Python 3 for nsmclient and of course an installed and
# running non-session-manager
import liblo


API_VERSION_MAJOR = 1
API_VERSION_MINOR = 2

MSG_ANNOUNCE = "/nsm/server/announce"
MSG_OPEN = "/nsm/client/open"
MSG_SAVE = "/nsm/client/save"
MSG_REPLY = "/reply"
MSG_ERROR = "/error"
MSG_PROGRESS = "/nsm/client/progress"
MSG_SESSION_LOADED = "/nsm/client/session_is_loaded"
MSG_SHOW_GUI = "/nsm/client/show_optional_gui"
MSG_HIDE_GUI = "/nsm/client/hide_optional_gui"
MSG_GUI_SHOWN = "/nsm/client/gui_is_shown"
MSG_GUI_HIDDEN = "/nsm/client/gui_is_hidden"
MSG_DIRTY = "/nsm/client/is_dirty"
MSG_CLEAN = "/nsm/client/is_clean"
MSG_MESSAGE = "/nsm/client/message"
MSG_LABEL = "/nsm/client/label"
MSG_OPENED = '/nsm/server/open'
MSG_SAVED = '/nsm/server/save'

ERROR_CODES = {
    "ERR_GENERAL": -1,
    "ERR_INCOMPATIBLE_API": -2,
    "ERR_BLACKLISTED": -3,
    "ERR_LAUNCH_FAILED": -4,
    "ERR_NO_SUCH_FILE": -5,
    "ERR_NO_SESSION_OPEN": -6,
    "ERR_UNSAVED_CHANGES": -7,
    "ERR_NOT_NOW": -8,
    "ERR_BAD_PROJECT": -9,
    "ERR_CREATE_FAILED": -10
}

log = logging.getLogger(__name__)


class ClientState(object):
    def __init__(self, env):
        # NSM reported the session is loaded
        self.session_loaded = False
        # NSM_URL environment variable
        self.nsm_url = env
        # set by NSMClient.handle_welcome()
        self.welcome_msg = None
        self.nsm_name = None
        # You can test it with "capability in self.server_capabilities"
        self.server_capabilities = set()
        # set by init()
        # You can test it with "capability in self.client_capabilities"
        self.client_capabilities = set()
        # set by NSMClient.handle_open()
        self.path_prefix = None
        self.session_name = None
        self.client_id = None
        # Everything is clean and shiny in the beginning.
        self.dirty = False


class NSMClient(object):
    def __init__(self, state, quit_on_error=False):
        # A shortcut to the client state
        self.state = state
        self.quit_on_error = quit_on_error

        # Functions to implement
        # Required functions
        self.open_cb = self.unimplemented_cb
        self.save_cb = self.unimplemented_cb

        # Optional functions
        self.quit_cb = self.unimplemented_cb
        self.show_gui_cb = self.unimplemented_cb
        self.hide_gui_cb = self.unimplemented_cb
        self.session_loaded_cb = self.unimplemented_cb

        # NSM sends SIGTERM to tell the program to quit,
        # so we install a handler method for this signal
        signal(SIGTERM, self._signal_handler)

        # Create an OSC server instance
        self.osc_server = osc_server = liblo.ServerThread()

        # Add functions to our osc server that receives from NSM.
        # NSM Welcome Message
        osc_server.add_method(MSG_REPLY, None, self.handle_reply)
        # NSM Error messages
        osc_server.add_method(MSG_ERROR, None, self.handle_error)
        osc_server.add_method(MSG_OPEN, None, self.handle_open)
        osc_server.add_method(MSG_SAVE, None, self.handle_save)
        osc_server.add_method(MSG_SESSION_LOADED, None,
                              self.handle_session_loaded)
        osc_server.add_method(MSG_SHOW_GUI, None,
                              self.handle_show_gui)
        osc_server.add_method(MSG_HIDE_GUI, None,
                              self.handle_hide_gui)

        # register a fallback for unhandled messages
        osc_server.add_method(None, None, self.handle_unknown)

        # And start the server thread
        osc_server.start()

    def _signal_handler(self, signal, frame):
        self.close()

    def announce(self, app_name, executable, pid):
        """Send announcement to server that client wants to be part of session.
        """
        caps = ":".join([''] + list(self.state.client_capabilities) + [''])
        self.send(MSG_ANNOUNCE, app_name, caps, executable,
                  API_VERSION_MAJOR, API_VERSION_MINOR, pid)

    def close(self):
        """Call the quit callback and then quit the program.

        The quit callback function does not need to perform the program exit
        itself. It should just shutdown audio engines etc.

        Even if the callback function does nothing, the client process will
        still quit.

        """
        # This can go wrong if the quit callback function tries to
        # shutdown things which have not been initialized yet.
        # For example the JACK engine which is by definition started
        # AFTER nsm-open
        log.debug("Client shutdown.")
        self.quit_cb(self)
        self.osc_server.stop()
        sys.exit()
        log.debug("I'm a zombie.")

    # OSC message handler functions
    def handle_open(self, path, args, types):
        """Handle open message received from NSM server.

        /nsm/client/open s:instance_specific_path_to_project s:session_name s:client_id

        A response is REQUIRED as soon as the open operation has been
        completed. Ongoing progress may be indicated by sending messages to
        /nsm/client/progress.

        """
        log.debug("open message received: %s %r", path, args)
        state = self.state
        state.path_prefix, state.session_name, state.client_id = args
        # Call the open callback function
        res, filename_or_msg = self.open_cb(self, state.path_prefix,
                                            state.client_id)

        if res:
            state_file = join(state.path_prefix, filename_or_msg)
            self.send(MSG_REPLY, MSG_OPEN,
                      "'{}' successfully opened".format(state_file))
        else:
            # TODO: send real errors with error codes
            msg = "Not loaded. Error: {}".format(filename_or_msg)
            log.error(msg)
            self.send_error(msg, path=MSG_OPEN)

            if self.quit_on_error:
                self.close()

    def handle_error(self, path, args, types):
        """Handle error message received from NSM server.

        /error "/nsm/server/announce" i:error_code s:error_message

        -1 ERR_GENERAL           General Error
        -2 ERR_INCOMPATIBLE_API  Incompatible API version
        -3 ERR_BLACKLISTED       Client has been blacklisted.

        """
        _, errcode, msg = args

        if errcode == -2:  # ERR_INCOMPATIBLE_API
            msg = "Incompatible API. Client shuts down itself."
            log.error(msg)
            self.send_error(msg, -2)
        elif errcode == -3:  # ERR_BLACKLISTED
            msg = "Client black listed. Client shuts down itself."
            log.error(msg)
            self.send_error(msg, -3)
        else:
            # TODO
            log.error("Client has received error %s but does not know how "
                      "to handle it yet: %s", errcode, msg)

        if self.quit_on_error:
            self.close()

    def handle_save(self, path, args, types):
        """Handle save message received from NSM server.

        /nsm/client/save

        This message will only be delivered after a previous open message, and
        may be sent any number of times within the course of a session
        (including zero, if the user aborts the session).

        args is empty, types is empty.

        """
        log.debug("save message received: %s %r", path, args)
        # Call the save callback function
        res, filename_or_msg = self.save_cb(self, self.state.path_prefix)

        if res:
            state_file = join(self.state.path_prefix, filename_or_msg)
            self.send(MSG_REPLY, MSG_SAVE,
                      "'{}' successfully saved.".format(state_file))
            self.set_dirty(False, internal=True)
        else:
            # TODO: send real errors with error codes
            msg = "Not saved. Error: {}".format(filename_or_msg)
            log.error(msg)
            self.send_error(msg, path=MSG_SAVE)

            if self.quit_on_error:
                self.close()

    def handle_session_loaded(self):
        """Handle session_is_loaded received from NSM server.

        /nsm/client/session_is_loaded

        """
        self.session_loaded_cb(self)

    def handle_reply(self, path, args, types):
        """Handle /reply messages received from NSM server.

        Dispatches knon reply messages to specific handler methods.

        """
        log.debug("reply message received: %r", args)
        if not args:
            return

        if args[0] == MSG_ANNOUNCE:
            self.handle_welcome(*args[1:])
        elif args[0] == MSG_OPENED:
            log.info("Session loaded.")
        elif args[0] == MSG_SAVED:
            log.info("Session saved.")
        else:
            log.warning("Unknown /reply message: %r", args)

    def handle_unknown(self, path, args, types, src):
        """Handle unknown OSC message."""
        log.warning("Received unknown OSC message '%s' from '%s'",
                    path, src.get_url())

        for a, t in zip(args, types):
            log.debug("argument of type '%s': %r", t, a)

    def handle_welcome(self, welcome_msg, nsm_name, capabilities):
        """Handle welcome message received from NSM server.

        /reply "/nsm/server/announce" s:message s:name_of_session_manager s:capabilities

        Receiving this message means we are now part of a session.

        """
        self.state.welcome_msg = welcome_msg
        self.state.nsm_name = nsm_name
        self.state.server_capabilities = set(capabilities.strip(':').split(':'))

    # GUI
    def handle_show_gui(self, *args):
        """Handle show_optional_gui message received from NSM server.

        Only execute callback if the server has the capabilities to handle
        optional GUIs. If not ignore command.

        """
        if "optional-gui" in self.state.server_capabilities:
            if self.show_gui_cb(self):
                self.send(MSG_GUI_SHOWN)
        else:
            log.warning("%s message received but server capabilities do not "
                        "include 'optional-gui'.", MSG_SHOW_GUI)

    def handle_hide_gui(self, *args):
        """Handle hide_optional_gui message received from NSM server.

        Only execute callback if the server has the capabilities to handle
        optional GUIs. If not ignore command.

        """
        if "optional-gui" in self.state.server_capabilities:
            if self.hide_gui_cb(self):
                self.send(MSG_GUI_HIDDEN)
        else:
            log.warning("%s message received but server capabilities do not "
                        "include 'optional-gui'.", MSG_HIDE_GUI)

    def unimplemented_cb(self, *args, **kwargs):
        """Handle any messages for which no callback function has been set."""
        log.debug("Fallback implementation called with %r, %r", args, kwargs)
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        log.debug('Called by: %s', calframe[1][3])
        return True, "Fine"

    def send(self, *args, **kwargs):
        """Send an OSC mesage to the NSM server.

        Uses the NSM_URL read from the process environment at initialization
        as the destination and the OSC server attached to this instance as
        the source.

        """
        log.debug("Sending OSC to '%s': %r %r",
                   self.state.nsm_url, args, kwargs)
        self.osc_server.send(self.state.nsm_url, *args, **kwargs)

    def send_error(self, msg, code=-1, path=MSG_ANNOUNCE):
        """Send an error reply message to the NSM server."""
        # make sure we send a number.
        code = ERROR_CODES.get(code, code)
        self.send(MSG_ERROR, path, code, msg)

    def send_message(self, message, priority=0):
        """Send a status message to the NSM server.

        /nsm/client/message i:priority s:message

        Clients may send miscellaneous status updates to the server for
        possible display to the user. This may simply be chatter that is
        normally written to the console. priority should be a number from 0 to
        3, 3 being the most important. Clients which have this capability
        should include :message: in their announce capability string.

        """
        if "message" in self.state.client_capabilities:
            self.send(MSG_MESSAGE, int(priority), str(message))
        else:
            log.warning("The client tried to send a status message but was "
                        "not initialized with the 'message' capability. "
                        "The message was not sent. Get rid of this warning by "
                        "setting the 'message' capability flag to True or "
                        "remove the message update from the code")

    def set_dirty(self, dirty, internal=False):
        """Report state change to NSM server.

        /nsm/client/is_dirty
        /nsm/client/is_clean

        Some clients may be able to inform the server when they have
        unsaved changes pending. Such clients may optionally send
        is_dirty and is_clean messages. Clients which have this
        capability should include :dirty: in their announce
        capability string.

        """
        if "dirty" in self.state.client_capabilities:
            if dirty and not self.state.dirty:
                self.state.dirty = True
                self.send(MSG_DIRTY)
            elif not dirty and self.state.dirty:
                self.state.dirty = False
                self.send(MSG_CLEAN)

        elif not internal:
            log.warning("The client tried to send a dirty/clean update, "
                        "but was not initialized with the 'dirty' capability. "
                        "The message was not sent. "
                        "Get rid of this warning by setting the 'dirty' "
                        "capability flag to True or remove the dirty update "
                        "from the code.")

    def set_label(self, label):
        """Set the client label in the NSM GUI."""
        self.send(MSG_LABEL, str(label))

    def update_progress(self, progress):
        """Report progress update to NSM server.

        /nsm/client/progress f:progress

        progress must be a float between 0 and 1.0.

        For potentially time-consuming operations, such as save and open,
        progress updates may be reported to the NSM server throughout the
        duration of the operation, by sending a floating point value between
        0.0 and 1.0. The value 1.0 indicates completion. The server will not
        send a response to these messages, but will relay the information to
        the user.

        """
        if "progress" in self.state.client_capabilities:
            self.send(MSG_PROGRESS, float(progress))
        else:
            log.warning("The client tried to send a progress update but was "
                        "not initialized with the 'progress' capability. "
                        "The message was not sent. Get rid of this warning by "
                        "setting the 'progress' capability flag or remove the "
                        "progress update from the code.")


def init(app_name, capabilities, requiredFunctions, optionalFunctions,
         startsWithGui=True, executable=None):
    """Create an NSMClient instance and announce it to the NSM server.

    Also sets the message handler callback functions from the provided
    lookup dictionaries.

    app_name = "Super Client"

    You must not change the app_name after your software is released and used
    in people's sessions. The NSM server provides a path for the session files
    to your application and bases this on the app_name. Changing the app_name
    would be like telling NSM we are a different program now.

    Returns the created NSMClient instance.

    """
    state = ClientState(os.getenv("NSM_URL"))

    if not state.nsm_url:
        raise RuntimeError("Non-Session-Manager environment variable $NSM_URL "
                           "not found. This program must be run via a Non "
                           "Session manager.")
        sys.exit(1)

    caps = {key for key, value in capabilities.items() if value}
    state.client_capabilities = caps
    client = NSMClient(state)

    for identifier, function in requiredFunctions.items():
        setattr(client, identifier + '_cb', function)

    for identifier, function in optionalFunctions.items():
        if function:
            setattr(client, identifier + '_cb', function)

    # Finally tell NSM we are ready and start the main loop
    # __main__.__file__ stands for the executable name

    # XXX: Funky!
    import __main__

    if not executable:
        if dirname(__main__.__file__) in os.environ["PATH"].split(os.pathsep):
            executable = basename(__main__.__file__)
        else:
            executable = abspath(__main__.__file__)

    client.announce(app_name, executable, os.getpid())

    # Wait for the welcome message.
    s = time.time()
    while not state.welcome_msg:
        time.sleep(.1)
        if time.time() - s > 5:
            raise RuntimeError("No response from NSM server.")

    # If the optional-gui capability is not present then clients with
    # optional GUIs MUST always keep them visible
    if "optional-gui" in state.client_capabilities:
        if "optional-gui" in state.server_capabilities:
            if startsWithGui:
                client.show_gui_cb(client)
                client.send(MSG_GUI_SHOWN)
            else:
                client.hide_gui_cb(client)
                client.send(MSG_GUI_HIDDEN)
        else:
            # Call show_gui_cb once.
            # All other OSC messages from client will be ignored.
            client.show_gui_cb(client)
            client.send(MSG_GUI_SHOWN)

    # loop and dispatch messages every 100ms
    return client
