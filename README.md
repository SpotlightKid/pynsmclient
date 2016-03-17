Python Non Session Manager Client
=================================

Version 0.2b - March 2016

This is a heavily reworked fork of *nsmclient* from
https://github.com/nilsgey/pynsmclient.

This fork created by: Christopher Arndt <chris@chrisarndt.de>

Original Author: Nils Gey ich@nilsgey.de http://www.nilsgey.de

Non Session Manager Author:

Jonathan Moore Liles  <male@tuxfamily.org> http://non.tuxfamily.org/nsm/


Overview
--------

*nsmclient* is a Python 3 client library for the [Non Session Management]
protocol and a convenience wrapper around a [liblo]-based [OSC] server and
client, which makes it easy to support NSM in your Python programs. You don't
need any OSC knowledge to use this package.


Usage Instructions
------------------

Copy `nsmclient.py` into your source directory or use

    python setup.py install

to install `nsmclient.py` system-wide. Both variants are equally good. Just
copying it to your own source tree does not require your users to install
nsmclient themselves. Since this is a really small lib, I recommend this
approach.

In your own program:

    import nsmclient

The `nsmclient` module provides `NSMClient`, an abstract base class. You must
sub-class it and implement at least the following methods:

    def MyApp(nsmclient.NSMClient):

        def open_session(self, session-path, client_id):
            """Open/create a sesssion and return status and filename or error."""
            return status, filename_or_msg

        def save_session(self, session_path, client_id):
            """Save current sesssion and return status and filename or error."""
            return status, filename_or_msg

Additionally you should probably implement these read-only property methods:

    @property
    def app_name(self):
        """Return name of application as displayed in NSM GUI."""
        return "MyApp"

    @property
    def capabilities(self):
        """Return sequence of client capabilities."""
        return (nsmclient.CAP_MESSAGE, nsmclient.CAP_PROGRESS, ...)

Then instantiate your class and enter your main event loop.

Please see `example.py` for a minimal and working example.

Additional methods your subclass can provide are:

    def quit(self):
        """Called before program exits."""

    def show_gui(self):
        """Called when NSM tells your program to open its GUI."""

    def hide_gui(self):
        """Called when NSM tells your program to close its GUI."""

    def session_loaded(self):
        """Called when NSM tells your program the entire session was loaded."""

The return value is of these methods is ignored.

Furthermore, there are some methods provided by `NSMClient`, which your
sub-class may want to use:

    # Set program label in NSM GUI
    set_label(name)

    # Report session "dirty" status to NSM
    set_dirty(bool)

    # Send status message to NSM
    send_message(message, priority=0)

    # Report progress of current operation (e.g. open or save) to NSM
    # 0.0 <= value <= 1.0
    update_progress(value)

The important part is that your application follows the NSM rules - see the
[API documentation] on the NSM website.


Dependencies
------------

* [Non Session Manager]
* [liblo] - an OSC library written in C
  (tested with version 0.28)
* [pyliblo] - Python 3 bindings for liblo
  (tested with version 0.10.0)


License
-------

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


[Non Session Manager]: http://non.tuxfamily.org/nsm/
[Non Session Management]: http://non.tuxfamily.org/wiki/Non%20Session%20Manager
[API documentation]: http://non.tuxfamily.org/nsm/API.html
[OSC]: http://opensoundcontrol.org/
[liblo]: http://liblo.sourceforge.net/
[pyliblo]: http://das.nasophon.de/pyliblo/
