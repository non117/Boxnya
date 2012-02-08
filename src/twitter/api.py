#coding:utf-8
import urllib, urllib2
from twitter.oauth import OAuth

class Api():
    def __init__(self, ckey, csecret, atoken, atokensecret):
        self.oauth = OAuth(ckey, csecret, atoken, atokensecret)
    
    def userstream(self):
        url = 'https://userstream.twitter.com/2/user.json'
        req = self.oauth.base(url, "GET")
        response = urllib2.urlopen(req)
        response.readline()
        response.readline()
        return response.readline()
    
    def update(self, post):
        url = "https://api.twitter.com/1/statuses/update.json"
        if isinstance(post, unicode): post = post.encode("utf-8")
        else: post = str(post)
        post = urllib.quote(post, "")
        request = self.oauth.base(url, "POST", {"status":post})
        return urllib2.urlopen(request).read()
    
    def timeline(self):
        url = "https://api.twitter.com/1/statuses/home_timeline.json"
        request = self.oauth.base(url, "GET", {"count":"5"})
        return urllib2.urlopen(request).read()