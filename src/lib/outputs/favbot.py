# -*- coding: utf-8 -*-
from lib.core import Output
from lib.twitter.api import Api

class FavBot(Output):
    def init(self):
        if isinstance(self.twitter, dict):
            self.twitter = [self.twitter]
        apilist = [Api(twi["atoken"],twi["atokensecret"]) for twi in self.twitter]
        self.apis = {}
        
        self.favsync_targets = getattr(self, "favsync_targets", [])
        if isinstance(self.favsync_targets, str):
            self.favsync_targets = [self.favsync_targets]
        
        for api in apilist:
            user = api.user_timeline(count=1)[0]["user"]
            name = user["screen_name"]
            self.apis[name] = api
    
    def throw(self, packet):
        if isinstance(packet["data"],unicode):
            return None
        if packet["data"].get("type") == "favsync":
            for name, api in self.apis.items():
                if name in self.favsync_targets:
                    api.favorite(int(packet["data"]["id"]))
        
        elif packet["data"].get("type") == "favtero":
            name = packet["data"]["mention"][0]["screen_name"]
            target_name = packet["data"]["text"].split(" ")[2]
            count = int(packet["data"]["text"].split(" ")[3])
            roop = count/201 + 1
            ids = []
            for i in range(roop):
                n = count - 200*i
                try:
                    temp_id = [post["id"] for post in self.apis[name].user_timeline(count=n, screen_name=target_name)]
                except TypeError:
                    temp_id = []
                ids = ids + temp_id
            for id in ids:
                self.apis[name].favorite(id)