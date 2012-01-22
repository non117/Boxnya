# -*- coding: utf-8 -*-
import sys
import time
from Queue import Queue
from threading import Event, Thread

class Message(object):
    ''' Moduleオブジェクト間のデータ受け渡しとイベント通知を行う '''
    def __init__(self):
        self.queue = Queue()
        self.event = Event()
    def push(self, data):
        self.queue.put_nowait(data)
        self.event.set()
        self.event.clear()
    def get(self):
        return self.queue.get_nowait()
    def notify(self):
        self.event.set()
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
        data = {"text":text, "from":self.name, "icon":icon}
        for output in self.outputs:
            output.push(data)

class Input(Module):
    def run(self):
        while not self.stopevent.isSet():
            try:
                self.fetch()
            except:
                self._call_master(sys.exc_info())
    def fetch(self):
        ''' このメソッドをオーバーライドしてください '''
        pass

class Output(Module):
    def run(self):
        while not self.stopevent.isSet():
            self.message.wait()
            if not self.message.empty():
                data = self.message.get() #TODO sleep処理. 正規表現で制御コードを受け取ってメッセージを送出しないように
                self.send(data)
    def send(self, data):
        ''' このメソッドをオーバーライドしてください '''
        pass

class Logger(Module):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, settings=None):
        super(Logger, self).__init__(group, target, name, args, kwargs, verbose)
        self.master = master
        self.settings = settings
        self.message = Message()
    def _write_log(self, data):
        pass
    def run(self):
        while not self.stopevent.isSet():
            self.message.wait()
            if not self.message.empty():
                data = self.message.get()
                self._write_log(data)

class Master(Module):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(Master, self).__init__(group, target, name, args, kwargs, verbose)
        self.message = Message()
        self._load_settings()
        self._load_modules()
        self.logger = Logger(settings=self.log_settings)
        for mod_name, output in self.output_modules.items(): #出力モジュールをインスタンス化
            self.output_modules[mod_name] = output(name=mod_name, kwargs=None, master=self.message, 
                                                   logger=self.logger.message)
        for mod_name, input in self.input_modules.items(): #入力モジュールに出力先のメッセージを渡してインスタンス化
            output_list = [out_obj.message for out_name, out_obj in self.output_modules.items() 
                           if out_name in self.input_to_output.get(mod_name)]
            self.input_modules[mod_name] = input(name=mod_name, kwargs=None, master=self.message, 
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
        self.log_settings = None
        self.input_to_output = {"test":["test2", "test3"],} #TODO: あとでかく
        self.output_to_input = {}
    def _load_modules(self):
        self.input_modules = self._make_module_dict('input')
        self.output_modules = self._make_module_dict('output')
        if not self.input_modules or not self.output_modules:
            print "empty" #TODO: log
            quit()
    def _start_modules(self):
        self.logger.start()
        for obj in self.output_modules.values():
            obj.start()
        for obj in self.input_modules.values():
            obj.start()
    def _stop_modules(self):
        for obj in self.output_modules.values():
            obj.message.notify()
            obj.stopevent.set()
            obj.join(0.5)
            continue
        for obj in self.input_modules.values():
            obj.stopevent.set()
            obj.join(0.5)
            continue
    def _error_handle(self, data):
        print data
    def run(self):
        self._start_modules()
        while not self.stopevent.isSet():
            self.message.wait()
            if not self.message.empty():
                data = self.message.get()
                self._error_handle(data)
    def join(self, timeout=None):
        self._stop_modules()
        self.logger.message.notify()
        self.logger.stopevent.set()
        self.logger.join()
        self.message.notify()
        self.stopevent.set()
        super(Master, self).join(timeout)