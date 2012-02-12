# -*- coding: utf-8 -*-
from lib.core import Output
from lib.twitter.api import Api

class FavBot(Output):
    def init(self):
        if isinstance(self.twitter, dict):
            self.twitter = [self.twitter]
        apilist = [Api(twi["atoken"],twi["atokensecret"]) for twi in self.twitter]
        self.apis = {}
        self.protected = []
        for a in apilist:
            user = a.usertimeline(count=1)[0]["user"]
            name = user["screen_name"]
            protected = bool(user["protected"])
            if protected:
                self.protected.append(name)
            self.apis[name] = a
    
    def throw(self, packet):
        if isinstance(packet["data"],unicode):
            return None
        if packet["data"]["type"] == "protected":
            for name, a in self.apis.items():
                if not name in self.protected:
                    a.favorite(int(packet["data"]["id"]))