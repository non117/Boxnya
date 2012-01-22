# -*- coding: utf-8 -*-
from master import Input
from datetime import datetime
import time

class Test(Input):
    def fetch(self):
        if int(datetime.today().strftime("%S")) % 10 == 0:
            self.throw("input->output")
            time.sleep(5)
            raise IndexError