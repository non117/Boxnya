#coding:utf-8
import urllib, urllib2
import signal
from time import sleep

class Api():
    def __init__(self, oauth_instance):
        self.oauth = oauth_instance
        self.connection_timeout = 10
        self.timeout = 90
        self.waitsec_start = 30 # should be between 20 and 40
        self.waitsec_max = 270  # source be between 240 and 300
    
    def getStream(self):
        url ='https://userstream.twitter.com/2/user.json'
        req = self.oauth.generate_request(url)
    
        def handler(signum, frame):
            raise urllib2.URLError(None)
    
        waitsec = 0
        waitpower = 1
        while True:
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(self.connection_timeout)
                strm = urllib2.urlopen(req, None, self.timeout)
                signal.signal(signal.SIGALRM, signal.SIG_DFL)
                signal.alarm(0)
                return strm
            except urllib2.HTTPError, e:
                if e.code == 420: waitpower = 2
            except urllib2.URLError:
                pass
            signal.alarm(0)
            print "---> Connection failure: retry after %d sec " % (waitsec * waitpower)
            sleep(waitsec * waitpower)
            if waitsec == 0:
                waitsec = self.waitsec_start
            elif waitsec * 2 > self.waitsec_max:
                waitsec = self.waitsec_max
            else:
                waitsec = waitsec * 2
            waitpower = 1