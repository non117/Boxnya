# -*- coding: utf-8 -*-
import hashlib
import urllib, urllib2

from lib.core import Output

class imkayac(Output):
    def throw(self, packet):
        message = packet["data"]
        url = "http://im.kayac.com/api/post/%s" % self.username
        if isinstance(message, unicode):
            message = message.encode("utf-8")
        else:
            message = str(message)
        
        # 連続送信チェック
        if not self.sendable(message):
            return None
        
        params = {"message":message}
        if self.password:
            params["password"] = self.password
        if self.sig:
            params["sig"] = hashlib.sha1("%s%s" % (message, self.sig)).hexdigest()
        
        request = urllib2.Request(url, data=urllib.urlencode(params))
        try:
            response = urllib2.urlopen(request).read()
        except urllib2.HTTPError, e:
            return e.code
        return "posted" in response