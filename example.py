#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sys import argv
from os.path import join
from time import sleep

from nsmclient import NSMClient, CAP_MESSAGE, CAP_PROGRESS, CAP_SWITCH


class MyAppNSMClient(NSMClient):
    @property
    def app_name(self):
        return "MyApp"

    @property
    def capabilities(self):
        return (CAP_PROGRESS, CAP_MESSAGE, CAP_SWITCH)

    def open_session(self, session_path, client_id):
        print("open session", session_path, client_id)
        # status, filename_or_msg
        return True, join(session_path, "myapp.dat")

    def save_session(self, session_path):
        print("save session", session_path)
        # status, filename_or_msg
        return True, join(session_path, "myapp.dat")

    def session_quit(self, session_path):
        self.send_message("Preparing to quit. Wait for progress to finish.")
        # Fake quit process
        self.update_progress(0.1)
        sleep(0.5)
        self.update_progress(0.5)
        sleep(0.5)
        self.update_progress(0.9)
        self.update_progress(1.0)


if __name__ == '__main__':
    client = MyAppNSMClient(init=False)
    # executable name reported to NSM can be set via first command line arg
    client.init(executable=argv[1] if len(argv) > 1 else None)

    while True:
        sleep(1)
