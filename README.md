Python Non Session Manager Client
=================================

Version 0.2b - March 2016

This is a heavily reworked fork of *nsmclient* from
https://github.com/nilsgey/pynsmclient.

This fork created by: Christopher Arndt <chris@chrisarndt.de>

Original Author: Nils Gey ich@nilsgey.de http://www.nilsgey.de

Non Session Manager Author:

Jonathan Moore Liles  <male@tuxfamily.org> http://non.tuxfamily.org/nsm/


Purpose
-------

Python nsmclient is a convenience wrapper around liblo and the NSM-protocol to
implement Non Session support easily in your own Python programs. You don't
need any OSC knowledge to use this package.


Instructions
------------

Copy `nsmclient.py` into your source directory or use

    python3 setup.py install

to install `nsmclient.py` system-wide. Both variants are equally good. Just
copying it to your own source tree does not require your users to install
nsmclient themselves. Since this is a really small lib I recommend this
approach.

In your own program:

    import nsmclient

`NSMClient` is an abstract base class. You must sub-classs it and implement at
least the following methods and properties:

    def MyApp(nsmclient.NSMClient):

        def open_session(self, session-path, client_id):
            return status, filename_or_msg

        def save_session(self, session_path, client_id):
            return status, filename_or_msg

Additionally you should probably implement these read-only property methods:

    @property
    def app_name(self):
        return "MyApp"

    @property
    def capabilities(self):
        return (nsmclient.CAP_MESSAGE, nsmclient.CAP_PROGRESS, ...)

Please see `example.py` for a minimal and working example.

The important part is that your application follows the NSM rules (see
example.py documentation and NSM website http://non.tuxfamily.org/nsm/API.html)


Dependencies
------------

* [Non Session Manager](http://non.tuxfamily.org/nsm/)
* [liblo](http://liblo.sourceforge.net/) (tested with version 0.28)
* [pyliblo](http://das.nasophon.de/pyliblo/) - Python 3 bindings for liblo.
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
