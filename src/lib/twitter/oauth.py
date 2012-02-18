# -*- coding: utf-8 -*-
import hashlib
import hmac
import random
import time
import urllib, urllib2
import urlparse

class OAuth():
    def __init__(self, ckey, csecret, atoken="", atokensecret=""):
        self.ckey = ckey
        self.csecret = csecret
        self.atoken = atoken
        self.atokensecret = atokensecret
    
    def make_signature(self, params, url, method, secret=""):
        ''' シグネチャを計算する '''
        pstr = "&".join(["%s=%s" % kv for kv in sorted(params.items())])
        msg = "%s&%s&%s" % (method, urllib.quote(url, ""), urllib.quote(pstr, ""))
        h = hmac.new("%s&%s" % (self.csecret, secret), msg, hashlib.sha1)
        return h.digest().encode("base64").strip()

    def init_params(self, extra_params={}):
        params = {
            "oauth_consumer_key":self.ckey,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_nonce": str(random.getrandbits(64)),
            "oauth_version": "1.0"
            }
        params.update(extra_params)
        return params
    
    def base(self, url, method, extra_params={}, extra_header={}, extra_data=None):
        ''' OAuthのリクエストを作る '''
        params = self.init_params(extra_params)
        params["oauth_token"] = self.atoken
        params["oauth_signature"] = self.make_signature(params, url, method, self.atokensecret)
        for key in extra_params.keys():
            del params[key]
        
        if method == "GET":
            url = "%s?%s" % (url, urllib.urlencode(extra_params))
        request = urllib2.Request(url)
        
        if method == "POST":
            request.add_data("&".join(['%s=%s' % kv for kv in extra_params.items()]))
        if extra_data and extra_header:
            request.add_data(extra_data)
        
        oauth_header = "OAuth %s" % (", ".join(['%s="%s"' % (key, urllib.quote(val)) for key, val in params.items()]))
        request.add_header("Authorization", oauth_header)
        for k,v in extra_header.items():
            request.add_header(k, v)
        return request

    def oauth_initializer(self, request_url, auth_url ,accesstoken_url):
        # Get Token
        print "---* Getting a request token:"
        params = self.init_params()
        params["oauth_signature"] = self.make_signature(params, request_url, "GET")
        request = urllib2.Request("%s?%s" % (request_url, urllib.urlencode(params)))
        ret = urlparse.parse_qs(urllib2.urlopen(request).read())
        token = ret["oauth_token"][0]
        token_secret = ret["oauth_token_secret"][0]
        # Get PIN
        print "---* Please access to following URL, and authorize Boxnya.\n"
        print "%s?%s=%s\n" % (auth_url, "oauth_token", token)
        print "---* Next, please input a 7 digit PIN that is given by twitter.com."
        print "->"
        pin = raw_input()
        print "---* Getting an access token:",
        # Get Access Token
        params = self.init_params({"oauth_verifier":int(pin), "oauth_token":token})
        params["oauth_signature"] = self.make_signature(params, accesstoken_url, "GET", token_secret)
        request = urllib2.Request("%s?%s" % (accesstoken_url, urllib.urlencode(params)))
        fin = urlparse.parse_qs(urllib2.urlopen(request).read())
        print "\n---> Authorized."
        return {"atokensecret":fin["oauth_token_secret"][0], "atoken":fin["oauth_token"][0]}