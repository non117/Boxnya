# -*- coding: utf-8 -*-
import re

from lib.core import Filter

class EgoSearch(Filter):
    def init(self):
        try:
            self.regexp = self.regexp.decode("utf-8")
        except UnicodeDecodeError:
            self.regexp = None
        self.pattern = re.compile(self.regexp)
        if isinstance(self.screen_name, str):
            self.screen_name = [self.screen_name]
        self.users = self.screen_name
        self.history = []
        self.pattern
        #TODO: enable処理
    
    def filter(self, packet):
        data = packet["data"]
        if not isinstance(data, dict):
            return None

        if data.get("mentions") and [user for user in self.users if user in [mention["screen_name"] for mention in data["mentions"]]]:
            mention = {"user":data["user"]["screen_name"],
                       "post":data["text"]}
            return u"%(user)s: %(post)s" % mention
        elif data.get("event") and data["target"]["screen_name"] in self.users:
            if "favorite" in data["event"]:
                event = {"star":u"☆" if "un" in data["event"] else u"★",
                         "user":data["source"]["screen_name"],
                         "event":data["event"].title(),
                         "post":data["object"]["text"]}
                return u"%(star)s %(user)s %(event)sd: %(post)s" % event
            elif "retweet" == data["event"]:
                event = {"user":data["source"]["screen_name"],
                         "post":data["object"]["text"]}
                return u"%(user)s Retweeted: %(post)s" % event
            elif "dm" == data["event"]:
                event = {"user":data["source"]["screen_name"],
                         "post":data["text"]}
                return u"DM from %(user)s: %(post)s" % event
            elif "follow" == data["event"]:
                event = {"name":data["source"]["name"],
                         "screen_name":data["source"]["screen_name"]}
                return u"%(name)s (@%(screen_name)s) is now following you" % event
            elif "list" in data["event"]:
                event = {"event":u"◆ Added into" if "add" in data["event"] else u"◇ Removed from",
                         "list":data["object"]["name"]}
                return u"%(event) %(list)s" % event
        elif self.regexp and self.pattern.search(data.get("text", "")):
            mention = {"user":data["user"]["screen_name"],
                       "post":data["text"]}
            return u"%(user)s: %(post)s" % mention
        return None