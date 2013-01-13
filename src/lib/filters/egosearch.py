# -*- coding: utf-8 -*-
import re

from lib.core import Filter

class EgoSearch(Filter):
    def init(self):
        try:
            self.regexp = self.regexp.decode("utf-8")
        except UnicodeDecodeError:
            self.regexp = ""
        self.pattern = re.compile(self.regexp)
        
        if isinstance(self.screen_name, str):
            self.screen_name = [self.screen_name]
        
        self.retweet = True
        self.fav = True
        self.dm = True
        self.list = True
        self.follow = True
        self.reply = True
        self.egosearch = True
        
        if "retweet" in self.disable:
            self.retweet = False
        if "fav" in self.disable:
            self.fav = False
        if "dm" in self.disable:
            self.dm = False
        if "list" in self.disable:
            self.list = False
        if "follow" in self.disable:
            self.follow = False
        if "reply" in self.disable:
            self.reply = False
        if "egosearch" in self.disable:
            self.egosearch = False
        
        # オプション設定の読み込み
        self.favsync_sources = getattr(self, "favsync_sources", [])
        if isinstance(self.favsync_sources, str):
            self.favsync_sources = [self.favsync_sources]
        self.favtero = getattr(self, "favtero", False)
        self.filterRT = getattr(self, "filterRT", False)
    
    def isUnofficialRT(self, text):
        if not self.filterRT:
            return False
        regexp = r".*[RQ]T:?\s?@?[a-zA-Z0-9_].*"
        # searchがヒットしなければNoneが帰る
        result = re.search(regexp, text)
        return result
    
    def filter(self, packet):
        data = packet["data"]
        if not isinstance(data, dict):
            return None

        if self.reply and data.get("mentions") and [user for user in self.screen_name if user in data["mentions"]]:
            mention = {"user":data["user"]["screen_name"],
                       "post":data["text"]}
            if not self.isUnofficialRT(mention["post"]):
                self.send(u"%(user)s: %(post)s" % mention, exclude = ["favbot"])
                
                if self.favtero and "fav" in mention["post"] and mention["user"] in self.screen_name:
                    self.send({"text":mention["post"], "mention":data["mentions"], "type":"favtero"}, target=["favbot"])
        
        elif data.get("event") and data.get("target") and data["target"]["screen_name"] in self.screen_name:
            if self.fav and "favorite" in data["event"]:
                event = {"star":u"☆" if "un" in data["event"] else u"★",
                         "user":data["source"]["screen_name"],
                         "event":data["event"].title(),
                         "post":data["object"]["text"]}
                self.send(u"%(star)s %(user)s %(event)sd: %(post)s" % event, exclude = ["favbot"])
            
            elif self.retweet and "retweet" == data["event"]:
                event = {"user":data["source"]["screen_name"],
                         "post":data["object"]["text"]}
                self.send(u"♺ %(user)s Retweeted: %(post)s" % event, exclude = ["favbot"])
            
            elif self.dm and "dm" == data["event"]:
                event = {"user":data["source"]["screen_name"],
                         "post":data["text"]}
                self.send(u"DM from %(user)s: %(post)s" % event, exclude = ["favbot"])
            
            elif self.follow and "follow" == data["event"]:
                event = {"name":data["source"]["name"],
                         "screen_name":data["source"]["screen_name"]}
                self.send(u"%(name)s (@%(screen_name)s) is now following you" % event, exclude = ["favbot"])
            
            elif self.list and "list" in data["event"]:
                event = {"event":u"◆ Added into" if "add" in data["event"] else u"◇ Removed from",
                         "list":data["object"]["name"]}
                self.send(u"%(event)s %(list)s" % event, exclude = ["favbot"])
        
        elif self.egosearch and self.regexp and self.pattern.search(data.get("text", "")):
            mention = {"user":data["user"]["screen_name"],
                       "post":data["text"]}
            self.send(u"%(user)s: %(post)s" % mention, exclude = ["favbot"])
        
        elif data.get("event") == "favorite" and data["source"]["screen_name"] in self.favsync_sources:
            self.send({"id":data["object"]["id"],"type":"favsync"}, target = ["favbot"])