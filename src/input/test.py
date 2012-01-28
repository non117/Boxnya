# -*- coding: utf-8 -*-
from core import Input
from datetime import datetime
import time

class Test(Input):
    def fetch(self):
        if int(datetime.today().strftime("%S")) % 5 == 0:
            self.throw("message")
            self.log(self.name)
            time.sleep(1)