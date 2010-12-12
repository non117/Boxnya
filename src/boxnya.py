#!/usr/bin/python
#-*- encoding:utf-8 -*-

atoken =""
atoken_secret = ""
ckey = "ZctjpCsuug2VtjfEuceg"
csecret = "pO9WL26Ia9rXyjNavXrit1iclCt1G2J1nRA4jZ6LGc"

screen_name = ""
im_id = ""
im_pswd = ""
im_sig = ""
reg_exp = ""

import time, random
import urllib, urllib2
import hmac, hashlib
import cgi
import simplejson
import re
import hashlib
import yaml
import datetime
from time import sleep , time ,strftime,localtime

try:
    f = open("oauth.yaml","r")
    oauth_dict = yaml.load(f)
    atoken = oauth_dict["atoken"]
    atoken_secret = oauth_dict["atoken_secret"]
    f.close()
except IOError:
    print "### Permit Boxnya to access your twitter account.\t###\n"

try:
    f = open("settings.yaml","r")
    settings = yaml.load(f)
    screen_name = settings["screen_name"]
    reg_exp = settings["reg_exp"]
    im_id = settings["im_id"]
    im_pswd = settings["im_pswd"]
    im_sig = settings["im_sig"]
    f.close()

except IOError:
    print "### No settings.yaml.\t###\n"

class IMKayac:
    def __init__(self,id,password=None,sig=None):
        self.id = id
        self.password = password
        self.sig = sig

    def notify(self,msg):
        if isinstance(msg, unicode): msg = msg.encode('utf-8')
        path = 'http://im.kayac.com/api/post/%s' % self.id
        params = { 'message':msg, }
        if self.password:
            params['password'] = self.password
        if self.sig:
            params['sig'] = hashlib.sha1(msg+self.sig).hexdigest()
        urllib2.build_opener().open(path, urllib.urlencode(params))

def make_signature(params, url, method, csecret, secret = ""):
    # Generate Signature Base String
    plist = []
    for i in sorted(params):
        plist.append("%s=%s" % (i, params[i]))

    pstr = "&".join(plist)
    msg = "%s&%s&%s" % (method, urllib.quote(url, ""),
                        urllib.quote(pstr, ""))

    # Calculate Signature
    h = hmac.new("%s&%s" % (csecret, secret), msg, hashlib.sha1)
    sig = h.digest().encode("base64").strip()

    return sig

def CheckSettings():
    if not screen_name:
        print "### Please set the screen name.\t###"
    if not reg_exp:
        print "### Please set the keyword.\t###"
    if not im_id:
        print "### Please set the im.kayac id.\t###"
    if not screen_name or not reg_exp or not im_id:
        quit()

def init_params():
    p = {
        "oauth_consumer_key": ckey,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time())),
        "oauth_nonce": str(random.getrandbits(64)),
        "oauth_version": "1.0"
        }

    return p

reqt_url = 'http://twitter.com/oauth/request_token'
auth_url = 'http://twitter.com/oauth/authorize'
acct_url = 'http://twitter.com/oauth/access_token'

if not atoken and not atoken_secret:
    # Request Parameters
    params = init_params()

    # Generate Signature
    sig = make_signature(params, reqt_url, "GET", csecret)
    params["oauth_signature"] = sig

    # Get Token
    req = urllib2.Request("%s?%s" % (reqt_url, urllib.urlencode(params)))
    resp = urllib2.urlopen(req)

    # Parse Token Parameters
    ret = cgi.parse_qs(resp.read())
    token = ret["oauth_token"][0]
    token_secret = ret["oauth_token_secret"][0]

    # Get PIN
    print "* Please access to this URL, and allow."
    print "%s?%s=%s" % (auth_url, "oauth_token", token)
    print "\n* After that, will display 7 digit PIN, input here."
    print "PIN ->",
    pin = raw_input()
    pin = int(pin)

    print "Get access token:",

    # Generate Access Token Request
    params = init_params()
    params["oauth_verifier"] = pin
    params["oauth_token"] = token

    sig = make_signature(params, acct_url, "GET", csecret, token_secret)
    params["oauth_signature"] = sig

    # Get Access Token
    req = urllib2.Request("%s?%s" % (acct_url, urllib.urlencode(params)))
    resp = urllib2.urlopen(req)

    print "\t[OK]\n"

    # Parse Access Token
    fin = cgi.parse_qs(resp.read())
    atoken = fin["oauth_token"][0]
    atoken_secret = fin["oauth_token_secret"][0]

    oauth_dict = {"atoken":atoken, "atoken_secret":atoken_secret}
    f = open("oauth.yaml","w")
    yaml.dump(oauth_dict,f,default_flow_style=False)
    f.close()

    print "* Done."

def oauth_header(params):
    plist = []
    for p in params:
        plist.append('%s="%s"' % (p, urllib.quote(params[p])))

    return "OAuth %s" % (", ".join(plist))

def getStream():
    url ='https://userstream.twitter.com/2/user.json'
    params = init_params()
    params["oauth_token"] = atoken

    sig = make_signature(params, url, "GET", csecret, atoken_secret)
    params["oauth_signature"] = sig

    req = urllib2.Request(url)
    req.add_header("Authorization", oauth_header(params))
    return urllib2.urlopen(req)

def output(text,im):
    im.notify(text)
    time = datetime.datetime.today()
    print "---> ( " + str(time)[:22] + " ) " + text

def main():
    CheckSettings()
    im = IMKayac(im_id, im_pswd, im_sig)
    pattern = re.compile(reg_exp + "|@%s" % screen_name)
    stream = getStream()
    stream.readline()
    stream.readline()
    while True:
        recv = stream.readline()
        try:
            json = simplejson.loads(recv)
            if json.get("event") == "favorite" and json.get("target")["screen_name"] == screen_name:
                text = u"★ "+ json["source"]["screen_name"] + " Favorited: " + json["target_object"]["text"]
                output(text,im)
            elif pattern.search(json.get("text","")):
                text = json["user"]["screen_name"] + ": " + json["text"]
                output(text,im)
        except simplejson.JSONDecodeError:
            pass

if __name__ == "__main__":
    print "---> Boxnya service start"
    try:
        main()
    except KeyboardInterrupt:
        print "\n---> see you !"
