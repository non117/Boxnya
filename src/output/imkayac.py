# -*- coding: utf-8 -*-
import hashlib
import urllib, urllib2

from core import Output

class imkayac(Output):
    def send(self, message):
        url = "http://im.kayac.com/api/post/%s" % self.username
        if isinstance(message, unicode):
            message = message.encode("utf-8")
        else:
            message = str(message)
        params = {"message":message}
        if self.password:
            params["password"] = self.password
        if self.sig:
            params["sig"] = hashlib.sha1("%s%s" % (message, self.sig)).hexdigest()
        request = urllib2.Request(url, data=urllib.urlencode(params))
        response = urllib2.urlopen(request).read()
        return "posted" in response