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
        self.event.set()
    def get(self):
        return self.queue.get_nowait()
    def empty(self):
        return self.queue.empty()
    def wait(self):
        self.event.wait()

class Module(Thread):
    ''' master, logger, input, outputの基底クラス
        master, logger引数にはそれぞれのMessageオブジェクトが渡される
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, logger=None, outputs=[]):
        super(self, Module).__init__(self, group, target, name, args, kwargs, verbose)
        self.master = master
        self.logger = logger
        self.outputs = outputs
        self.message = Message(Queue(),Event())
    def _call_master(self, text):
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
                self._call_master(sys.exc_info())
    def loop(self):
        ''' このメソッドをオーバーライドしてください '''
        pass

class Output(Module):
    def run(self):
        while True:
            self.message.wait()
            if not self.message.empty():
                data = self.message.get()
                self.send(data)
            else:
                self.message.wait()
    def send(self, data):
        ''' このメソッドをオーバーライドしてください '''
        pass