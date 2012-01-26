# -*- coding: utf-8 -*-
import sys
from Queue import Queue
from threading import Event, Thread

import settings

class Message(object):
    ''' Moduleオブジェクト間のデータ受け渡しとイベント通知を行う '''
    def __init__(self):
        self.queue = Queue()
        self.event = Event()
    def push(self, data):# メッセージを突っ込む
        self.queue.put_nowait(data)
        self.event.set()
        self.event.clear()
    def get(self):# メッセージを取り出す
        return self.queue.get_nowait()
    def notify(self): # 起きろ
        self.event.set()
    def empty(self): # 空？
        return self.queue.empty()
    def wait(self): # ブロック
        self.event.wait()

class Module(Thread):
    ''' master, logger, input, outputの基底クラス
        master, logger引数にはそれぞれのMessageオブジェクトが渡される
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, logger=None, outputs=[]):
        super(Module, self).__init__(group, target, name, args, kwargs, verbose)
        self.daemon = True
        self.master = master
        self.logger = logger
        self.outputs = outputs
        self.message = Message()
        self.stopevent = Event()
    def _call_master(self, text):
        data = {"text":text, "from":self.name}
        self.master.push(data)
    def log(self, text, level='info'):
        data = {"text":text, "from":self.name, "level":level}
        self.logger.push(data)
    def throw(self, text, icon=None):
        ''' 普通はこれでメッセージを投げる '''
        data = {"text":text, "from":self.name, "icon":icon}
        for output in self.outputs:
            output.push(data)

class Input(Module):
    def fetch(self):
        ''' このメソッドをオーバーライドしてください '''
        pass
    def run(self):
        ''' これはあまりオーバーライドしてほしくない '''
        try:
            while not self.stopevent.is_set():
                self.fetch()
        except Exception:
            self._call_master(sys.exc_info())

class Output(Module):
    def send(self, data):
        ''' このメソッドをオーバーライドしてください '''
        pass
    def run(self):
        ''' これはあまりオーバーライドしてほしくない '''
        try:
            while not self.stopevent.is_set():
                self.message.wait()
                if not self.message.empty():
                    data = self.message.get()
                    self.send(data)
        except Exception:
            self._call_master(sys.exc_info())

class Logger(Module):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, settings=None):
        super(Logger, self).__init__(group, target, name, args, kwargs, verbose)
        self.master = master
        self.logger = self
        self.settings = settings
    def _write(self, data):
        pass
    def run(self):
        try:
            while not self.stopevent.isSet():
                self.message.wait()
                if not self.message.empty():
                    data = self.message.get()
                    self._write_log(data)
        except Exception:
            self._call_master(sys.exc_info())

class Master(Module):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(Master, self).__init__(group, target, name, args, kwargs, verbose)
        self._load_settings()
        self._load_modules()
        self.logger = Logger(settings=self.log_settings)
        self.output_instances, self.input_instances, self.outputs = {},{}, {}
        self.outputs, self.output_messages = {}, {}
        for mod_name, output in self.output_modules.items(): #出力モジュールをインスタンス化
            obj = output(name=mod_name, kwargs=None, master=self.message, logger=self.logger.message)
            self.output_instances[mod_name] = obj
            self.output_messages[mod_name] = obj.message
        for mod_name, input in self.input_modules.items(): #入力モジュールに出力先のメッセージを渡してインスタンス化
            output_list = [obj for name, obj in self.output_messages.items() if name in self.input_to_output.get(mod_name)]
            self.outputs[mod_name] = output_list
            self.input_instances[mod_name] = input(name=mod_name, kwargs=None, master=self.message, 
                                                 logger=self.logger.message, outputs=output_list)
    def _make_module_dict(self, dirname):
        ''' ディレクトリ名を引数にとって, ディレクトリ内のモジュール名と同名のクラスを全て読み込む. '''
        name_list = __import__(dirname).__all__
        name_list.remove('__init__')
        for name in name_list:
            __import__('%s.%s' % (dirname,name))
        modules = [(sys.modules.get('%s.%s' % (dirname,name)), name) for name in name_list]
        module_dict = {}
        for module, name in modules:
            try:
                module_dict[name] = getattr(module, name.lower().title())
            except AttributeError:
                pass
        return module_dict
    def _load_settings(self):
        self.log_settings = settings.LOGDIR
        self.input_to_output = settings.INOUT
    def _load_modules(self):
        self.input_modules = self._make_module_dict('input')
        self.output_modules = self._make_module_dict('output')
        if not self.input_modules or not self.output_modules:
            print "empty" #TODO: log
            quit()
        for key, io in self.input_to_output.items(): # Outputsが空の場合の処理
            if not io:
                self.input_to_output[key] = self.output_modules.keys()
    def run(self):
        self.logger.start()
        for obj in self.output_instances.values() + self.input_instances.values():
            obj.start()
        while not self.stopevent.isSet():
            self.message.wait()
            if not self.message.empty():
                data = self.message.get()
                self._error_handle(data)
    def _error_handle(self, data):
        print data #TODO: log
        self.start_module("name")
    def join(self, timeout=None):
        for obj in self.output_instances.values():
            obj.message.notify()
            obj.stopevent.set()
            obj.join(0.5)
            continue
        for obj in self.input_instances.values():
            obj.stopevent.set()
            obj.join(0.5)
            continue
        self.logger.message.notify()
        self.logger.stopevent.set()
        self.logger.join()
        self.message.notify()
        self.stopevent.set()
        super(Master, self).join(timeout)
    def start_module(self, name):
        if name in self.input_modules:
            obj = self.input_modules[name](name=name, kwargs=None, master=self.message, 
                                logger=self.logger.message, outputs=self.outputs[name])
            obj.start()
            self.input_instances[name] = obj
        elif name in self.output_modules:
            obj = self.output_modules[name](name=name, kwargs=None, master=self.message, 
                                                            logger=self.logger.message)
            obj.message = self.output_messages[name]
            obj.start()
            self.output_instances[name] = obj
    def stop_module(self, name):
        if name in self.input_instances:
            obj = self.input_instances[name]
        elif name in self.output_instances:
            obj = self.output_instances[name]
            obj.message.notify()
        else:
            return False
        obj.stopevent.set()
        obj.join(10)
        return False if obj.is_alive() else True