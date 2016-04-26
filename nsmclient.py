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


See the file README.md in the source distribution / code repository for
usage instructions.

"""

import abc
import logging
import os
import sys
import time

from enum import Enum
from os.path import abspath, basename, dirname, join
from signal import signal, SIGTERM

# You need pyliblo for Python 3 for nsmclient and of course an installed and
# running non-session-manager
import liblo


log = logging.getLogger(__name__)


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

# client knows when it has unsaved changes
CAP_DIRTY = "dirty"
# client can send textual status updates
CAP_MESSAGE = "message"
# client can send progress updates during time-consuming operations
CAP_PROGRESS = "progress"
# client has an optional GUI
CAP_OPTIONAL_GUI = "optional-gui"
# client is capable of responding to multiple `open` messages without
# restarting
CAP_SWITCH = "switch"


class ErrCode(Enum):
    """NSM protocol error codes."""
    # General error
    GENERAL = -1
    # Incompatible API version
    INCOMPATIBLE_API = -2
    # Client has been blacklisted.
    BLACKLISTED = -3
    # Client could not be launched
    LAUNCH_FAILED = -4
    # The named session does not exist
    NO_SUCH_FILE = -5
    # No session is loaded
    NO_SESSION_OPEN = -6
    # Unsaved changes would be lost
    UNSAVED_CHANGES = -7
    # Operation cannot be completed at this time
    NOT_NOW = -8
    # An existing project file was found to be corrupt
    BAD_PROJECT = -9
    # A new project could not be created
    CREATE_FAILED = -10
    # Session is locked by another process
    SESSION_LOCKED = -11
    # An operation is currently in progress
    OPERATION_PENDING = -12


class ClientState(object):
    """Simple data class to store NSM client state."""

    def __init__(self, url):
        # NSM reported the session is loaded
        # set by NSMClient.session_loaded()
        self.session_loaded = False
        # NSM_URL environment variable
        # set by NSMClient.init()
        self.nsm_url = url
        # set by NSMClient.handle_welcome()
        self.session_joined = False
        self.welcome_msg = None
        self.nsm_name = None
        # Test for a server capability with:
        # capability in self.server_capabilities
        self.server_capabilities = set()
        # set by NSMClient.handle_open()
        self.session_prefix = None
        self.session_path = None
        self.session_name = None
        self.client_id = None
        # Everything is clean and shiny in the beginning.
        self.dirty = False


class NSMClient(abc.ABC):
    """Abstract base class for NSM client implementations."""

    def __init__(self, name=None, init=True, quit_on_error=True, show_gui=True,
                 executable=None, timeout=5):
        """Create an NSMClient instance.

        It ``init`` is ``True`` (the default), announce the client to the NSM
        server immediately and thereby join the NSM session.

        If joining a session fails or the ``open_session`` or ``save_session``
        methods raise an exception, the client program is shut down by calling
        the ``close`` instance method when ``quit_on_error`` is ``True`` (the
        default).

        The remaining keyword arguments are passed to the ``init`` method.

        If the client *and* the server have the CAP_OPTIONAL_GUI capability and
        if the ``show_gui`` argument is ``True`` (the default), the client's
        ``show_gui`` method is called after the NSM session has been joined, or
        the ``hide_gui`` method if it is ``False``.

        If the server does not have the CAP_OPTIONAL_GUI capability, but the
        client does, the ``show_gui`` method is called unconditionally.

        """
        self.name = name
        self.quit_on_error = quit_on_error
        self._show_gui = show_gui

        # NSM sends SIGTERM to tell the program to quit,
        # so we install a handler method for this signal
        signal(SIGTERM, self.handle_sigterm)

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

        if init:
            self.init(executable=executable, timeout=timeout, show_gui=showgui)

    # public API functions

    def init(self, executable=None, timeout=5):
        """Announce the NSM client to the NSM server.

        The client tries to get the OSC URL of the server from the ``NSM_URL``
        environment variable. If it is not set or empty, a ``RuntimeError``
        exception will be raised.

        The ``excutable`` argument sets the name of the executable file of the
        NSM client reported to the NSM server. If it is not passed or false, it
        will be determined automatically. In certain situations, e.g. when
        running the Python client from a shell script via ``exec``, this may
        not result in the correct or desired value being used, so this
        parameter allows to override it.

        ``timeout`` sets the maxiumum time period in seconds, for which the
        client blocks and waits for the server's reply to its announce message.
        If the server does not reply within the timeout, a ``RuntimeError``
        exception is raised.

        """
        nsm_url = os.getenv("NSM_URL")

        if not nsm_url:
            raise RuntimeError(
                "Non-Session-Manager environment variable NSM_URL not set. "
                "This program must be run via a Non Session Manager.")

        # We keep the client state in a separate data object
        self.state = ClientState(nsm_url)

        # XXX: Funky!
        import __main__

        if not executable:
            # Derrive the executable path from __main__.__file__
            filename = __main__.__file__
            if dirname(filename) in os.environ["PATH"].split(os.pathsep):
                executable = basename(filename)
            elif filename :
                executable = abspath(filename)

        # Finally tell NSM we are ready and start the main loop
        self.announce(executable, os.getpid())

        # Wait for the welcome message.
        if timeout:
            s = time.time()
            while not self.state.session_joined:
                time.sleep(.1)
                if time.time() - s > timeout:
                    raise RuntimeError("No response from NSM server within "
                                       "timeout (%s sec.).", timeout)

    def send_message(self, message, priority=0):
        """Send a status message to the NSM server.

        /nsm/client/message i:priority s:message

        Clients may send miscellaneous status updates to the server for
        possible display to the user. This may simply be chatter that is
        normally written to the console. priority should be a number from 0 to
        3, 3 being the most important. Clients which have this capability
        should include :message: in their announce capability string.

        """
        if "message" in self.capabilities:
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

        Some clients may be able to inform the server when they have unsaved
        changes pending. Such clients may optionally send is_dirty and is_clean
        messages. Clients which have this capability should include :dirty: in
        their announce capability string.

        """
        if "dirty" in self.capabilities:
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
        if "progress" in self.capabilities:
            self.send(MSG_PROGRESS, float(progress))
        else:
            log.warning("The client tried to send a progress update but was "
                        "not initialized with the 'progress' capability. "
                        "The message was not sent. Get rid of this warning by "
                        "setting the 'progress' capability flag or remove the "
                        "progress update from the code.")

    # Internal helper methods

    def announce(self, executable, pid):
        """Send announcement to server that client wants to be part of session.
        """
        caps = ":".join([''] + list(self.capabilities) + [''])
        log.debug("Announcing client: name=%s, capabilities=%s, executable=%s"
                  ",pid=%i", self.app_name, caps, executable, pid)
        self.send(MSG_ANNOUNCE, self.app_name, caps, executable,
                  API_VERSION_MAJOR, API_VERSION_MINOR, pid)

    def close(self):
        """Call the quit callback and then quit the program.

        The quit callback function does not need to perform the program exit
        itself. It should just shut down audio engines etc.

        Even if the callback function does nothing, the client process will
        still quit.

        """
        # This can go wrong if the quit callback function tries to
        # shutdown things which have not been initialized yet.
        # For example the JACK engine which is by definition started
        # AFTER nsm-open
        log.debug("Client shutdown.")
        self.quit()
        self.osc_server.stop()
        sys.exit()
        log.debug("I'm a zombie.")


    def send(self, *args, **kwargs):
        """Send an OSC mesage to the NSM server.

        Uses the NSM_URL read from the process environment at initialization
        as the destination and the OSC server attached to this instance as
        the source.

        """
        log.debug("Sending OSC to '%s': %r %r",
                  self.state.nsm_url, args, kwargs)
        self.osc_server.send(self.state.nsm_url, *args, **kwargs)

    def send_error(self, msg, code=ErrCode.GENERAL, path=MSG_ANNOUNCE):
        """Send an error reply message to the NSM server."""
        # make sure we send a number.
        self.send(MSG_ERROR, path, code, msg)

    # OSC message, signal handler and internal callback functions

    def handle_error(self, path, args, types):
        """Handle error message received from NSM server.

        /error "/nsm/server/announce" i:error_code s:error_message

        ErrCode.GENERAL           General Error
        ErrCode.INCOMPATIBLE_API  Incompatible API version
        ErrCode.BLACKLISTED       Client has been blacklisted.

        """
        path, err_code, msg = args
        quit = self.quit_on_error

        if err_code == ErrCode.INCOMPATIBLE_API:
            msg = "Incompatible API."
        elif err_code == ErrCode.BLACKLISTED:
            msg = "Client black listed."
        elif err_code == ErrCode.GENERAL:
            msg = "General error."
        else:
            # XXX: call custom error handler if defined?
            msg = ("Client received error %s but does't know how to handle it:"
                   " %s" % (err_code, msg))

        if path == MSG_ANNOUNCE:
            quit = True
            msg = "Server rejected client announcement: " + msg

        log.error(msg)

        if quit:
            log.debug("Client shuts itself down.")
            self.close()

    def handle_open(self, path, args, types):
        """Handle open message received from NSM server.

        /nsm/client/open s:instance_specific_path_to_project s:session_name
                         s:client_id

        A response is REQUIRED as soon as the open operation has been
        completed. Ongoing progress may be indicated by sending messages to
        /nsm/client/progress.

        """
        log.debug("open message received: %s %r", path, args)
        session_prefix, session_name, client_id = args

        # Call the open callback function
        try:
            session_path = self.open_session(session_prefix, session_name,
                                             client_id)
        except Exception as exc:
            err_code = getattr(exc, 'code', ErrCode.GENERAL)
            msg = "Session not loaded. Error ({}): {}".format(err_code, exc)
            log.error(msg)
            self.send_error(msg, err_code, MSG_OPEN)

            if self.quit_on_error:
                self.close()
        else:
            state = self.state
            state.session_prefix = session_prefix
            state.session_name = session_name
            state.client_id = client_id

            if not session_path.startswith(state.session_prefix):
                session_path = state.session_prefix + session_path

            self.state.session_path = session_path
            self.send(MSG_REPLY, MSG_OPEN,
                      "'{}' successfully opened".format(session_path))

    def handle_reply(self, path, args, types):
        """Handle /reply messages received from NSM server.

        Dispatches known reply messages to specific handler methods.

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
        try:
            self.save_session(self.state.session_path)
        except Exception as exc:
            err_code = getattr(exc, 'code', ErrCode.GENERAL)
            msg = "Not saved. Error ({}): {}".format(err_code, exc)
            log.error(msg)
            self.send_error(msg, err_code, MSG_SAVE)

            if self.quit_on_error:
                self.close()
        else:
            self.send(MSG_REPLY, MSG_SAVE, "'{}' successfully saved."
                      .format(self.state.session_path))
            self.set_dirty(False, internal=True)

    def handle_session_loaded(self):
        """Handle session_is_loaded received from NSM server.

        /nsm/client/session_is_loaded

        """
        self.session_loaded()

    def handle_sigterm(self, signal, frame):
        """Handle system signal SIGTERM by shutting down client orderly."""
        self.close()

    def handle_unknown(self, path, args, types, src):
        """Handle unknown OSC messages."""
        log.warning("Received unknown OSC message '%s' from '%s'",
                    path, src.get_url())

        for a, t in zip(args, types):
            log.debug("argument of type '%s': %r", t, a)

    def handle_welcome(self, welcome_msg, nsm_name, capabilities):
        """Handle welcome message received from NSM server.

        /reply "/nsm/server/announce" s:message s:name_of_session_manager
               s:capabilities

        Receiving this message means we are now part of a session.

        """
        self.state.session_joined = True
        self.state.welcome_msg = welcome_msg
        self.state.nsm_name = nsm_name
        self.state.server_capabilities = set(
            capabilities.strip(':').split(':'))

        # If the optional-gui capability is not present then clients with
        # optional GUIs MUST always keep them visible
        if CAP_OPTIONAL_GUI in self.capabilities:
            if CAP_OPTIONAL_GUI in self.state.server_capabilities:
                if self._show_gui:
                    self.show_gui()
                    self.send(MSG_GUI_SHOWN)
                else:
                    self.hide_gui()
                    self.send(MSG_GUI_HIDDEN)
            else:
                # Call show_gui once.
                # All other OSC messages from client will be ignored.
                self.show_gui()
                self.send(MSG_GUI_SHOWN)

    # GUI

    def handle_hide_gui(self, *args):
        """Handle hide_optional_gui message received from NSM server.

        Only execute callback if the server has the capabilities to handle
        optional GUIs. If not, ignore command.

        """
        if "optional-gui" in self.state.server_capabilities:
            if self.hide_gui():
                self.send(MSG_GUI_HIDDEN)
        else:
            log.warning("%s message received but server capabilities do not "
                        "include 'optional-gui'.", MSG_HIDE_GUI)

    def handle_show_gui(self, *args):
        """Handle show_optional_gui message received from NSM server.

        Only execute callback if the server has the capabilities to handle
        optional GUIs. If not, ignore command.

        """
        if "optional-gui" in self.state.server_capabilities:
            if self.show_gui():
                self.send(MSG_GUI_SHOWN)
        else:
            log.warning("%s message received but server capabilities do not "
                        "include 'optional-gui'.", MSG_SHOW_GUI)

    # Required methods to implement by concrete sub-classes

    # Required methods
    @abc.abstractmethod
    def open_session(self, session_prefix, session_name, client_id):
        """Open/create a session and return session path (or suffix)."""

    @abc.abstractmethod
    def save_session(self, session_path):
        """Save current session using the given session path."""

    # Optional properties, may be overwritten by sub-classes

    @property
    def app_name(self):
        """Return name of application as displayed in NSM GUI.

        May be overwritten by a sub-class but should be treated as a read-only
        attribute.

        You must not change the app_name after your software is released and
        used in people's sessions. The NSM server provides a path (prefix) for
        the session files to your application and bases this on the app_name.
        Changing the app_name would be like telling NSM we are a different
        program now.

        The default implementation returns the name passed to the constructor
        via the ``name`` argument, or, if this is empty or ``None`, the class
        name.

        """
        return self.name or self.__class__.__name__

    @property
    def capabilities(self):
        """Return sequence of client capabilities.

        Capabilities are defined as constants CAP_DIRTY, CAP_MESSAGE,
        CAP_PROGRESS, CAP_OPTIONAL_GUI and CAP_SWITCH.

        """
        return ()

    # Optional methods, may be overwritten by sub-classes

    def hide_gui(self):
        """Called when NSM tells the client to close its GUI."""
        if CAP_OPTIONAL_GUI not in self.capabilities:
            raise RuntimeError(
                "Client does not have 'optional-gui' capability.")

    def quit(self):
        """Called before program exits."""
        pass

    def show_gui(self):
        """Called when NSM tells the client to open its GUI."""
        if CAP_OPTIONAL_GUI not in self.capabilities:
            raise RuntimeError(
                "Client does not have 'optional-gui' capability.")

    def session_loaded(self):
        """Called when NSM tells the client the entire session was loaded."""
        self.state.session_loaded = True
