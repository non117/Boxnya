# -*- coding: utf-8 -*-
from core import Output

class Test2(Output):
    def send(self, data):
        print data.get("from"),"->",self.name