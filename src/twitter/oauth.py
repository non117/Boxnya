#coding:utf-8
from time import time
import urllib, urllib2
import hmac, hashlib
import cgi
import random

class Oauth():
    def __init__(self, ckey, csecret="", atoken="", atoken_secret=""):
        self.ckey = ckey
        self.csecret = csecret
        self.atoken = atoken
        self.atoken_secret = atoken_secret
        self.reqt_url = 'http://twitter.com/oauth/request_token'
        self.auth_url = 'http://twitter.com/oauth/authorize'
        self.acct_url = 'http://twitter.com/oauth/access_token'
    
    def init_params(self):
        p = {
            "oauth_consumer_key": self.ckey,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time())),
            "oauth_nonce": str(random.getrandbits(64)),
            "oauth_version": "1.0"
            }
        return p
    
    def make_signature(self, params, url, method, csecret, secret=""):
        # Generate Signature Base String
        plist = ["%s=%s" % (i, params[i]) for i in sorted(params)]
        pstr = "&".join(plist)
        msg = "%s&%s&%s" % (method, urllib.quote(url, ""), urllib.quote(pstr, ""))
        # Calculate Signature
        h = hmac.new("%s&%s" % (csecret, secret), msg, hashlib.sha1)
        sig = h.digest().encode("base64").strip()
        return sig
    
    def request(self, url, params):
        try:
            req = urllib2.Request("%s?%s" % (url, urllib.urlencode(params)))
            resp = urllib2.urlopen(req)
            print "    [OK]"
            return resp
        except (urllib2.HTTPError,urllib2.URLError):
            print "    [failed]"
            print "---! Please retry authorization."
            quit()
    
    def oauth_initializer(self):
        # Get Token
        params = self.init_params()
        sig = self.make_signature(params, self.reqt_url, "GET", self.csecret)
        params["oauth_signature"] = sig
        print "---* Getting a request token:"
        resp = self.request(self.reqt_url, params)
        ret = cgi.parse_qs(resp.read())
        token = ret["oauth_token"][0]
        token_secret = ret["oauth_token_secret"][0]

        # Get PIN
        print "---* Please access to following URL, and authorize Boxnya."
        print "[ %s?%s=%s ]" % (self.auth_url, "oauth_token", token)
        print "---* Next, please input a 7 digit PIN that is given by twitter.com."
        print "->"
        pin = raw_input()
        print "---* Getting an access token:",

        # Get Access Token
        params = self.init_params()
        params["oauth_verifier"] = int(pin)
        params["oauth_token"] = token
        sig = self.make_signature(params, self.acct_url, "GET", self.csecret, token_secret)
        params["oauth_signature"] = sig
        resp = self.request(self.acct_url, params)
        fin = cgi.parse_qs(resp.read())
        self.atoken = fin["oauth_token"][0]
        self.atoken_secret = fin["oauth_token_secret"][0]
        print "---> Done Boxnya authorizing\n"
        return {"access_token":self.atoken, "access_token_secret":self.atoken_secret}
    
    def oauth_header(self, params):
        plist = ['%s="%s"' % (p, urllib.quote(params[p])) for p in params]
        return "OAuth %s" % (", ".join(plist))
    
    def generate_request(self, url):
        params = self.init_params()
        params["oauth_token"] = self.atoken
        sig = self.make_signature(params, url, "GET", self.csecret, self.atoken_secret)
        params["oauth_signature"] = sig
        
        req = urllib2.Request(url)
        req.add_header("Authorization", self.oauth_header(params))
        return req