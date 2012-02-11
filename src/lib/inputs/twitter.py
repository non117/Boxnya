# -*- coding: utf-8 -*-
from lib.core import Input
from lib.twitter.api import Api

class Twitter(Input):
    def init(self):
        self.api = Api(self.atoken, self.atokensecret)
    
    def fetch(self):
        def hoge(data):
            self.send(data)
        self.api.userstream(hoge)