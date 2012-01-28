# -*- coding: utf-8 -*-
import copy
import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler
from Queue import Queue
from threading import Event, Thread

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
    def clear(self):
        while not self.empty():
            self.get()
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
        if isinstance(kwargs, dict):
            for k,v in kwargs.items():
                if not k in ("name", "master", "logger", "outputs"):
                    setattr(self, k, v)
        self.daemon = True
        self.master = master
        self.logger = logger
        self.outputs = outputs
        self.message = Message()
        self.stopevent = Event()
    def _call_master(self, data):
        mes = {"data":data, "from":self.name}
        self.master.message.push(mes)
    def log(self, text, level='INFO'):
        mes = {"text":text, "from":self.name, "level":level.upper()}
        if self.logger:
            self.logger.message.push(mes)
    def throw(self, text, icon=None):
        ''' 普通はこれでメッセージを投げる '''
        mes = {"text":text, "from":self.name, "icon":icon}
        for output in self.outputs:
            output.push(mes)

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
                while not self.message.empty():
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
        self.dir = settings["dir"]
        self.mod = settings["mod"]
        self.loggers = {}
        self.loggers["system"] = self._logger_fuctory("system")
        for name in self.mod:
            self.loggers[name] = self._logger_fuctory(name)
    def _logger_fuctory(self, name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(os.path.join(self.dir, "%s.log" % name), maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%b %d %H:%M:%S %Y")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    def _write(self, data):
        level = getattr(logging, data["level"], logging.INFO)
        self.loggers[data["from"]].log(level, data["text"])
        if level >= logging.ERROR:
            self.throw(data["text"])
    def run(self):
        try:
            while not self.stopevent.is_set():
                self.message.wait()
                while not self.message.empty():
                    data = self.message.get()
                    self._write(data)
        except Exception:
            self._call_master(sys.exc_info())

class Master(Module):
    def __init__(self, settings, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(Master, self).__init__(group, target, "system", args, kwargs, verbose)
        self._load_settings(settings)
        if self.logging: # ロガーの起動
            self.logger = Logger(master=self, settings=self.log_settings)
            self.logger.start()
        self.log("Boxnya system started.")
        self._load_modules()
        self.output_instances, self.input_instances = {},{}
        self.outputs, self.output_messages = {}, {}
        
        for mod_name, output in self.output_modules.items(): #出力モジュールをインスタンス化
            obj = output(name=mod_name, kwargs=self.output_settings.get(mod_name), master=self, logger=self.logger)
            self.output_instances[mod_name] = obj
            self.output_messages[mod_name] = obj.message
        
        if self.logging:# ロガーのエラー出力先
            log_outputs = settings.LOG_OUT or self.output_modules.keys()
            self.logger.outputs = [mes for name, mes in self.output_messages.items() if name.split(".")[0] in log_outputs]
        
        for mod_name, input in self.input_modules.items(): #入力モジュールに出力先のメッセージを渡してインスタンス化
            output_list = [mes for name, mes in self.output_messages.items() 
                           if name.split(".")[0] in self.input_to_output.get(mod_name.split(".")[0])]
            self.outputs[mod_name] = output_list
            self.input_instances[mod_name] = input(name=mod_name, kwargs=self.input_settings.get(mod_name),
                                                    master=self, logger=self.logger, outputs=output_list)
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
    def _load_settings(self, settings):
        self.logging = getattr(settings, "LOGGING", False)
        if self.logging:
            if not getattr(settings, "LOG_DIR", ""):
                logpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),"log")
            else:
                logpath = settings.LOG_DIR
            if not os.path.exists(logpath):
                try:
                    os.makedirs(logpath)
                except os.error:
                    sys.exit("Error : Cannot make log directory.")
            self.log_settings = {"dir":logpath, "mod":getattr(settings, "LOG_MOD", [])}
        if not getattr(settings, "INOUT", {}):
            print "nothing inout"
        self.input_to_output = settings.INOUT
        self.input_settings = getattr(settings, "INPUT_SETTINGS", {})
        self.output_settings = getattr(settings, "OUTPUT_SETTINGS", {})
    def _load_modules(self):
        self.input_modules = self._make_module_dict('input')
        self.output_modules = self._make_module_dict('output')
        if not self.input_modules or not self.output_modules:
            self.log("no INPUT or OUTPUT module.", "ERROR")
            self.log("Boxnya system terminate.")
            sys.exit("Error : no INPUT or OUTPUT module.")
        for key, io in self.input_to_output.items(): # Outputsが空の場合の処理
            if not io:
                self.input_to_output[key] = self.output_modules.keys()
        if self.input_settings:
            self._bear_modules(self.input_settings)
        if self.output_settings:
            self._bear_modules(self.output_settings)
    def _bear_modules(self, configs):
        ''' settingsにモジュールを多重化するように書いてあれば, そのモジュールをforkしておく. '''
        for name, confs in configs.items():
            if isinstance(confs, list):
                for i,c in enumerate(confs):
                    if i==0:
                        configs[name] = c
                    else:
                        new_name = "%s.%d" % (name, i)
                        configs[new_name] = c
                        self._fork(new_name)
    def _fork(self, name):
        '''' モジュールをforkする. forkされた新しいモジュールの名前は, "hoge.1","hoge.2"になる. '''
        original_name = name.split(".")[0]
        if original_name in self.input_modules:
            mod = self.input_modules[original_name]
            mod = copy.deepcopy(mod)
            self.input_modules[name] = mod
        elif original_name in self.output_modules:
            mod = self.output_modules[original_name]
            mod = copy.deepcopy(mod)
            self.output_modules[name] = mod
    def run(self):
        for obj in self.output_instances.values() + self.input_instances.values():
            obj.start()
        self.log("Boxnya module run.")
        while not self.stopevent.is_set():
            self.message.wait()
            while not self.message.empty():
                data = self.message.get()
                self._error_handle(data)
    def _error_handle(self, exc):
        log_text = "Exception has occured in %s : %s %s" %(exc["from"],
                                                           str(traceback.format_tb(exc["data"][2])),
                                                           str(exc["data"][1]))
        self.log(log_text, level="ERROR")
        self.start_module(exc["from"])
    def join(self, timeout=None, errmsg=""):
        for obj in self.output_instances.values():
            obj.message.notify()
            obj.stopevent.set()
            obj.join(0.5)
            continue
        for obj in self.input_instances.values():
            obj.stopevent.set()
            obj.join(0.5)
            continue
        self.log("Boxnya module terminated.")
        self.log("Boxnya system terminate.")
        self.logger.message.notify()
        self.logger.stopevent.set()
        self.logger.join()
        self.message.notify()
        self.stopevent.set()
        super(Master, self).join(timeout)
    def start_module(self, name):
        if name in self.input_modules:
            obj = self.input_modules[name](name=name, kwargs=self.input_settings.get(name),
                                master=self, logger=self.logger, outputs=self.outputs[name])
            obj.start()
            self.input_instances[name] = obj
        elif name in self.output_modules:
            obj = self.output_modules[name](name=name, kwargs=self.output_settings.get(name),
                                            master=self, logger=self.logger)
            obj.message = self.output_messages[name]
            obj.message.clear()
            obj.start()
            self.output_instances[name] = obj
    def stop_module(self, name):
        if name in self.input_instances:
            obj = self.input_instances[name]
            obj.stopevent.set()
            obj.join(10)
            if not obj.is_alive():
                self.input_instances.pop(name)
        elif name in self.output_instances:
            obj = self.output_instances[name]
            obj.message.notify()
            obj.stopevent.set()
            obj.join(10)
            if not obj.is_alive():
                self.output_instances.pop(name)