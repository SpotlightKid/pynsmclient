#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import sleep
from os.path import join

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
    client.init()

    while True:
        sleep(1)
