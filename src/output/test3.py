# -*- coding: utf-8 -*-
from core import Output

class Test3(Output):
    def send(self, data):
        print data, "received2"