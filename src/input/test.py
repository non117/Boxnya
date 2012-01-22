# -*- coding: utf-8 -*-
from master import Input
from datetime import datetime
import time

class Test(Input):
    def loop(self):
        if int(datetime.today().strftime("%S")) % 10 == 0:
            self.throw("input->output")
            print "10sec"
            time.sleep(5)