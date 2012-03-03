# -*- coding: utf-8 -*-
import datetime
import json
import gzip
import mimetypes
import urllib, urllib2
from lib.twitter.oauth import OAuth
from StringIO import StringIO

class Api():
    def __init__(self,  atoken="", atokensecret="", ckey="ZctjpCsuug2VtjfEuceg", 
                 csecret="pO9WL26Ia9rXyjNavXrit1iclCt1G2J1nRA4jZ6LGc"):
        self.oauth = OAuth(ckey, csecret, atoken, atokensecret)
        self.site = "http://api.twitter.com/"
    
    def initializer(self):
        ''' アクセストークン, シークレットを作る '''
        request_url = "http://twitter.com/oauth/request_token"
        auth_url = "https://twitter.com/oauth/authorize"
        accesstoken_url = "http://twitter.com/oauth/access_token"
        return self.oauth.oauth_initializer(request_url, auth_url, accesstoken_url)
    
    def execute(self, url, method, params={}, extra_header={}, extra_data=None):
        ''' twitterのリクエスト処理の実行 '''
        # パラメータを成形して辞書に
        for key, val in params.items():
            if isinstance(val, unicode): val = val.encode("utf-8")
            params[key] = urllib.quote(str(val), "")
        # gzip圧縮されたレスポンスを受け取る
        extra_header.update({"Accept-Encoding": "deflate, gzip"})
        request = self.oauth.base(url, method, params, extra_header, extra_data)
        try:
            response = urllib2.urlopen(request)
            if response.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
                data = f.read()
            else:
                data = response.read()
            return parse(data)
        except urllib2.URLError:
            return False

    def timeline(self):
        url = self.site + "1/statuses/home_timeline.json"
        return self.execute(url,"GET")

    def user_timeline(self, count=20, screen_name=""):
        url = self.site + "1/statuses/user_timeline.json"
        return self.execute(url, "GET", {"count":count, "screen_name":screen_name})

    def update(self, status):
        url = self.site + "1/statuses/update.json"
        return self.execute(url,"POST", {"status":status})
    
    def favorite(self, status_id):
        url = self.site + "1/favorites/create/%s.json" % str(status_id)
        return self.execute(url, "POST", {"id":str(status_id)})
    
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
        return self.execute(url, "POST", extra_header=headers, extra_data=body)
    
    def userstream(self, callback_func, rawdata=False):
        
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
                    callback_func(rawstr)
                callback_func(parse(rawstr))
        
def user(data):
    return {"id":data["id"],
            "screen_name":data["screen_name"],
            "name":data["name"],
            "protected":data["protected"],
            "icon":data["profile_image_url"]
            }

def mentions(data):
    if data.get("entities"):
        return [d["screen_name"] for d in data["entities"]["user_mentions"]]
    else:
        return []

def status(data):
    return {"id":data["id"],
            "user":user(data["user"]),
            "text":data["text"],
            "mentions": mentions(data),
            "urls":data["entities"]["urls"] if data.get("entities") else "",
            "in_reply_to":data["in_reply_to_status_id"],
            "date":data["created_at"]
            }

def retweet(data):
    return {"event":"retweet",
            "source":user(data["user"]),
            "target":status(data["retweeted_status"])["user"],
            "object":status(data["retweeted_status"]),
            "date":data["created_at"]
            }

def event(data):
    return {"event":data["event"],
            "source":user(data["source"]),
            "target":user(data["target"]),
            "object":data.get("target_object"),
            "date":data["created_at"]
            }

def favorite(data):
    data = event(data)
    data["object"] = status(data["object"])
    return data

def lists(data):
    data = event(data)
    data["object"] = {"name":data["object"]["full_name"],
                      "description":data["object"]["description"]}
    return data

def follow(data):
    data = event(data)
    del data["object"]
    return data

def dm(data):
    return {"event":"dm",
            "id":data["direct_message"]["id"],
            "source":user(data["direct_message"]["sender"]),
            "target":user(data["direct_message"]["recipient"]),
            "text":data["direct_message"]["text"],
            "date":data["direct_message"]["created_at"]
            }

def delete(data):
    return {"type":data["delete"].keys()[0],
            "user_id":data["delete"].values()[0]["user_id"],
            "id":data["delete"].values()[0]["id"],
            "date":unicode(datetime.datetime.today().strftime("%a %b %d %H:%M:%S +0900 %Y"))
            }

def format(obj):
    if obj.get("event"):
        if "favorite" in obj["event"]:
            return favorite(obj)
        if "list" in obj["event"]:
            return lists(obj)
        if "follow" == obj["event"]:
            return follow(obj)
    elif obj.get("retweeted_status"):
        return retweet(obj)
    elif obj.get("direct_message"):
        return dm(obj)
    elif obj.get("delete"):
        return delete(obj)
    
    try:
        data = status(obj)
        return data
    except KeyError:
        return obj

def parse(rawdata):
    try:
        obj = json.loads(rawdata)
    except (KeyError, ValueError):
        return {}
    if isinstance(obj, dict):
        return format(obj)
    if isinstance(obj, list):
        return [format(o) for o in obj]
    else:
        return None