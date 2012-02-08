# -*- coding: utf-8 -*-
from core import Filter

class Test4(Filter):
    def filter(self, data):
        print data.get("from"),"->" , self.name
        return data