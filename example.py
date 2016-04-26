#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from sys import argv
from time import sleep

from nsmclient import NSMClient, CAP_MESSAGE, CAP_PROGRESS, CAP_SWITCH


log = logging.getLogger("pynsm")


class MyAppNSMClient(NSMClient):
    @property
    def capabilities(self):
        return (CAP_PROGRESS, CAP_MESSAGE, CAP_SWITCH)

    def open_session(self, session_prefix, session_name, client_id):
        print("open session", session_prefix, session_name, client_id)
        return "/myapp.dat"

    def save_session(self, session_path):
        print("save session", session_path)
        return "/myapp.dat"

    def quit(self):
        self.send_message("Preparing to quit. Wait for progress to finish.")
        # Fake quit process
        self.update_progress(0.1)
        sleep(0.5)
        self.update_progress(0.5)
        sleep(0.5)
        self.update_progress(0.9)
        self.update_progress(1.0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # The executable name reported to NSM can be set via first command line arg
    executable = argv[1] if len(argv) > 1 else None

    # If you pass init=False to the constructor, the client delays announcing
    # itself to NSM and becoming part of the session until its init() method is
    # called.
    client = MyAppNSMClient(init=False)
    client.init(executable=executable)

    while True:
        sleep(1)
