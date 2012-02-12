# -*- coding: utf-8 -*-
import datetime
import urllib, urllib2
import json
import mimetypes
from lib.twitter.oauth import OAuth

class Api():
    def __init__(self,  atoken="", atokensecret="", ckey="iZqQjmzya6I6uDMzwbTsQ", 
                 csecret="CuzuwHUBbmbPuyYzIagCLSfSbXhiyNL7JAusmAexsY"):
        self.oauth = OAuth(ckey, csecret, atoken, atokensecret)
        self.jsonparser = JsonParser()
        self.site = "https://api.twitter.com/"
    
    def initializer(self):
        request_url = "http://twitter.com/oauth/request_token"
        auth_url = "https://twitter.com/oauth/authorize"
        accesstoken_url = "http://twitter.com/oauth/access_token"
        return self.oauth.oauth_initializer(request_url, auth_url, accesstoken_url)
    
    def exc(self, url, method, params={}, extra_header={}, extra_data=None):
        for key, val in params.items():
            if isinstance(val, unicode): val = val.encode("utf-8")
            params[key] = urllib.quote(str(val), "")
        
        request = self.oauth.base(url, method, params, extra_header, extra_data)
        try:
            response = urllib2.urlopen(request).read()
            return self.jsonparser.parse(response)
        except urllib2.URLError:
            return False

    def timeline(self):
        url = self.site + "1/statuses/home_timeline.json"
        return self.exc(url,"GET")

    def usertimeline(self, count=20):
        url = self.site + "1/statuses/user_timeline.json"
        return self.exc(url, "GET", {"count":count})

    def update(self, status):
        url = self.site + "1/statuses/update.json"
        return self.exc(url,"POST", {"status":status})
    
    def favorite(self, status_id):
        url = self.site + "1/favorites/create/%s.json" % str(status_id)
        return self.exc(url, "POST", {"id":str(status_id)})
    
    def upload_icon(self, filename):
        url = self.site + "1/account/update_profile_image.json"
        filetype = mimetypes.guess_type(filename)[0]
        BOUNDARY = 'B0xNyA'
        body = []
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="image"; filename="%s"' % filename)
        body.append('Content-Type: %s' % filetype)
        body.append('')
        with open(filename, 'rb') as f:
            body.append(f.read())
        body.append('--%s--' % BOUNDARY)
        body.append('')
        body = '\r\n'.join(body)
        headers = {'Content-Type': 'multipart/form-data; boundary=%s' % BOUNDARY,
                   'Content-Length': len(body)}
        return self.exc(url, "POST", extra_header=headers, extra_data=body)
    
    def userstream(self, func, rawdata=False):
        url = 'https://userstream.twitter.com/2/user.json'
        req = self.oauth.base(url, "GET")
        response = urllib2.urlopen(req)
        response.readline()
        response.readline()
        while True:
            try:
                rawstr = response.readline()
            except urllib2.URLError:
                rawstr = ''
            if rawstr == '':
                response.close()
                response = urllib2.urlopen(self.oauth.base(url, "GET"))
                continue
            else:
                if rawdata:
                    func(rawstr)
                func(self.jsonparser.parse(rawstr))
        
class JsonParser():
    def user(self, data):
        return {"id":data["id"],
                "screen_name":data["screen_name"],
                "name":data["name"],
                "protected":data["protected"],
                "icon":data["profile_image_url"]
                }
    
    def mentions(self, data):
        return [{"id":d["id"], "screen_name":d["screen_name"]} for d in data]
    
    def status(self, data):
        return {"id":data["id"],
                "user":self.user(data["user"]),
                "text":data["text"],
                "mentions": self.mentions(data["entities"]["user_mentions"]) if data.get("entities") else "",
                "urls":data["entities"]["urls"] if data.get("entities") else "",
                "in_reply_to":data["in_reply_to_status_id"],
                "date":data["created_at"]
                }
    
    def retweet(self, data):
        return {"event":"retweet",
                "source":self.user(data["user"]),
                "target":self.status(data["retweeted_status"])["user"],
                "object":self.status(data["retweeted_status"]),
                "date":data["created_at"]
                }
    
    def event(self, data):
        return {"event":data["event"],
                "source":self.user(data["source"]),
                "target":self.user(data["target"]),
                "object":data.get("target_object"),
                "date":data["created_at"]
                }
    
    def favorite(self, data):
        data = self.event(data)
        data["object"] = self.status(data["object"])
        return data
    
    def list(self, data):
        data = self.event(data)
        data["object"] = {"name":data["object"]["full_name"],
                          "description":data["object"]["description"]}
        return data
    
    def follow(self, data):
        data = self.event(data)
        del data["object"]
        return data
    
    def dm(self, data):
        return {"event":"dm",
                "id":data["direct_message"]["id"],
                "source":self.user(data["direct_message"]["sender"]),
                "target":self.user(data["direct_message"]["recipient"]),
                "text":data["direct_message"]["text"],
                "date":data["direct_message"]["created_at"]
                }
    
    def delete(self, data):
        return {"type":data["delete"].keys()[0],
                "user_id":data["delete"].values()[0]["user_id"],
                "id":data["delete"].values()[0]["id"],
                "date":unicode(datetime.datetime.today().strftime("%a %b %d %H:%M:%S +0900 %Y"))
                }
    
    def format(self, obj):
        if obj.get("event"):
            if "favorite" in obj["event"]:
                return self.favorite(obj)
            if "list" in obj["event"]:
                return self.list(obj)
            if "follow" == obj["event"]:
                return self.follow(obj)
        elif obj.get("retweeted_status"):
            return self.retweet(obj)
        elif obj.get("direct_message"):
            return self.dm(obj)
        elif obj.get("delete"):
            return self.delete(obj)
        
        try:
            data = self.status(obj)
            return data
        except KeyError:
            return obj
    
    def parse(self, rawdata):
        try:
            obj = json.loads(rawdata)
        except (KeyError, ValueError):
            print rawdata
            return {}
        if isinstance(obj, dict):
            return self.format(obj)
        if isinstance(obj, list):
            return [self.format(o) for o in obj]
        else:
            return None