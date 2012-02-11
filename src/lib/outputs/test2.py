# -*- coding: utf-8 -*-
from lib.core import Output

class Test2(Output):
    def throw(self, packet):
        print packet.get("from"),"->",self.name
        print packet