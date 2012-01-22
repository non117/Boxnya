# -*- coding: utf-8 -*-
from master import Output

class Test2(Output):
    def send(self, data):
        print data, "received"