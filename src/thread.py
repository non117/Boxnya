# -*- coding: utf-8 -*-
import sys
from Queue import Queue
from threading import Thread, Event

class Message(object):
    ''' Moduleオブジェクト間のデータ受け渡しとイベント通知を行う '''
    def __init__(self, q, event):
        self.queue = q
        self.event = event
    def push(self, data):
        self.queue.put_nowait(data)
        self._wake()
    def _wake(self):
        self.event.set()

class Module(Thread):
    ''' master, logger, input, outputの基底クラス
        master, logger引数にはそれぞれのMessageオブジェクトが渡される
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, message=None, master=None, logger=None, outputs=[]):
        self.message = message
        self.master = master
        self.logger = logger
        self.outputs = outputs
        self.message = Message(Queue(),Event())
        super(self, Module).__init__(self, group, target, name, args, kwargs, verbose)
    def call_master(self, text):
        data = {"text":text, "from":self.name}
        self.master.push(data)
    def log(self, text, level='info'):
        data = {"text":text, "from":self.name, "level":level}
        self.logger.push(data)
    def throw(self, text, icon=None):
        data = {"text":text, "from":self.name, "icon":icon}
        for output in self.outputs:
            output.push(data)

class Input(Module):
    def run(self):
        while True:
            try:
                self.loop()
            except:
                self.call_master(sys.exc_info())
    def loop(self):
        ''' このメソッドをオーバーライドしてください '''
        pass

class Output(Module):
    def catch(self):
        while True:
            self.message.event.wait()
            if not self.message.queue.empty():
                self.send()
            else:
                self.message.event.wait()
    def send(self):
        ''' このメソッドをオーバーライドしてください '''
        pass