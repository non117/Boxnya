# -*- coding: utf-8 -*-
import email.parser
import imaplib
import sys
import time
from email.header import decode_header

from lib.core import Input

class Gmail(Input):
    def init(self):
        self.prev_count = sys.maxint
        self.gmail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        self.gmail.login(self.username, self.password)
    
    def cleanup(self):
        self.gmail.logout()
    
    def fetch(self):
        time.sleep(60)
        _, n =  self.gmail.select()
        delta = int(n[0]) - self.prev_count #前回より増えた件数
        self.prev_count = int(n[0]) #更新しておく
        
        for i in reversed(range(delta)):
            _, msg = self.gmail.fetch(eval("%s-%d"%(n[0],i)), '(BODY.PEEK[HEADER])')
            p = email.parser.FeedParser()
            p.feed(msg[0][1])
            header = p.close()
            from_ = header.get("from").split(" ")[0]
            subject = decode_header(header.get("subject")) #TODO: 文字化け修正
            subject = subject[0][0].decode(subject[0][1]) if subject[0][1] else subject[0][0]
            
            message = "mail from %s : %s" % (from_, subject)
            self.send(message)