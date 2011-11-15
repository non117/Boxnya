# -*- coding: utf-8 -*-
from threading import Thread as OldThread

class Thread(OldThread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None, master=None, log=None):
        pass

    def gen_message(self):
        pass