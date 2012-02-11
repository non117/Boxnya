# -*- coding: utf-8 -*-
import copy
import logging
import os
import re
import sys
import traceback
from logging.handlers import RotatingFileHandler
from Queue import Queue
from threading import Event, Thread

class Carrier(object):
    ''' スレッド間のデータ受け渡しとイベント通知を行う '''
    def __init__(self, name):
        self.name = name
        self.queue = Queue()
        self.event = Event()
    
    def handover(self, data):
        self.queue.put_nowait(data)
        self.event.set()
        self.event.clear()
    
    def pickup(self):
        return self.queue.get_nowait()
    
    def wake(self):
        self.event.set()
    
    def clear(self):
        while not self.empty():
            self.pickup()
    
    def empty(self):
        return self.queue.empty()
    def sleep(self):
        self.event.wait()

class BaseThread(Thread):
    ''' master, logger, input, outputの基底クラス
        master, logger引数にはそれぞれのCarrierオブジェクトが渡される
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, logger=None, output_carriers=[]):
        super(BaseThread, self).__init__(group, target, name, args, kwargs, verbose)
        if isinstance(kwargs, dict):
            for k,v in kwargs.items():
                if not k in ("name", "master", "logger", "output_carriers"):
                    setattr(self, k, v)
        self.daemon = True
        self.master = master
        self.logger = logger
        self.output_carriers = dict([(o.name, o) for o in output_carriers])
        self.carrier = Carrier(name)
        self.stopevent = Event()
        self.init()
    
    def init(self):
        ''' 初期処理をここに書く '''
        pass
    
    def cleanup(self):
        ''' 終了時の処理をここに書く '''
        pass
    
    def join(self, timeout=None, errmsg=""):
        self.cleanup()
        super(BaseThread, self).join(timeout)
    
    def call_master(self, data, type):
        packet = {"data":data, "from":self.name, "type":type}
        self.master.carrier.handover(packet)
    
    def log(self, text, level='INFO'):
        packet = {"text":text, "from":self.name, "level":level.upper()}
        self.logger.carrier.handover(packet)
    
    def send(self, data, target_names=[]):
        ''' これでメッセージを投げる '''
        packet = {"data":data, "from":self.name}
        for name, carrier in self.output_carriers.items():
            if not target_names or name in target_names:# target_namesが空ならば常にTrue
                carrier.handover(copy.deepcopy(packet))

class Input(BaseThread):
    def fetch(self):
        ''' このメソッドをオーバーライドする '''
        #self.send(data, target_names)
    
    def run(self):
        try:
            while not self.stopevent.is_set():
                self.fetch()
        except Exception:
            self.call_master(sys.exc_info(), "error")

class Output(BaseThread):
    def throw(self, packet):
        ''' このメソッドをオーバーライドする '''
        pass
    
    def run(self):
        try:
            while not self.stopevent.is_set():
                self.carrier.sleep()
                while not self.carrier.empty():
                    packet = self.carrier.pickup()
                    self.throw(packet)
        except Exception:
            self.call_master(sys.exc_info(), "error")
            
class Filter(Output):
    def filter(self, packet):
        ''' フィルター処理をここに書く '''
        #return data
    
    def throw(self, packet):
        data = self.filter(packet)
        self.send(data)

class Logger(BaseThread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, settings=None):
        super(Logger, self).__init__(group, target, name, args, kwargs, verbose)
        self.master = master
        self.logger = self
        self.log_dir = settings["log_dir"]
        self.loggers = {}
        self.loggers[self.master.name] = self._logger_fuctory(self.master.name)
        for name in settings["log_mod"]:
            self.loggers[name] = self._logger_fuctory(name)
    
    def _logger_fuctory(self, name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(os.path.join(self.log_dir, "%s.log" % name), maxBytes=1000000, backupCount=5)
        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(message)s", datefmt="%b %d %H:%M:%S %Y")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def _write(self, packet):
        level = getattr(logging, packet["level"], logging.INFO)
        self.loggers[packet["from"]].log(level, packet["text"])
        if level >= logging.ERROR:
            self.send(packet["text"])
    
    def run(self):
        try:
            while not self.stopevent.is_set():
                self.carrier.sleep()
                while not self.carrier.empty():
                    packet = self.carrier.pickup()
                    self._write(packet)
        except Exception:
            self.call_master(sys.exc_info(), "error")

class Master(BaseThread):
    def __init__(self, settings, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(Master, self).__init__(group, target, "system", args, kwargs, verbose)
        self.active_number = 0
        self._load_settings(settings)
        if self.logging: # ロガーの起動
            self.logger = Logger(master=self, settings=self.log_settings)
            self.logger.start()
        self.log("Boxnya system started.")
        
        self._load_modules()
        self.output_instances, self.input_instances, self.filter_instances = {},{},{}
        self.filter_carriers, self.carrier_lists, self.output_carriers = {},{},{}
        for name, module in self.output_modules.items(): #出力モジュールをインスタンス化
            instance = module(name=name, kwargs=self.output_settings.get(name), master=self, logger=self.logger)
            self.output_instances[name] = instance
            self.output_carriers[name] = instance.carrier
        if self.logging:# ロガーのエラー出力先
            log_outputs = getattr(settings ,"LOG_OUT")
            self.logger.output_carriers = dict([(name, carrier) for name, carrier in self.output_carriers.items() 
                                           if name.split(".")[0] in log_outputs])
        
        for name, module in self.filter_modules.items(): #フィルターに出力先を渡してインスタンス化
            outputs = [carrier for output_name, carrier in self.output_carriers.items()
                               if output_name.split(".")[0] in self.input_to_output.get(name)]
            
            self.carrier_lists[name] = outputs
            instance = module(name=name, kwargs=self.filter_settings.get(name),
                        master=self, logger=self.logger, output_carriers=outputs)
            self.filter_instances[name] = instance
            self.filter_carriers[name] = instance.carrier
        
        for name, module in self.input_modules.items(): #入力モジュールに出力先のメッセージを渡してインスタンス化
            outputs = [carrier for output_name, carrier in self.output_carriers.items() + self.filter_carriers.items()
                               if output_name.split(".")[0] in self.input_to_output.get(name.split(".")[0])]
            
            self.carrier_lists[name] = outputs
            self.input_instances[name] = module(name=name, kwargs=self.input_settings.get(name),
                                                master=self, logger=self.logger, output_carriers=outputs)
        
    def _make_module_dict(self, dirname):
        ''' ディレクトリ名を引数にとって, ディレクトリ内のモジュール名と同名のクラスを全て読み込む. '''
        names = __import__(dirname, fromlist=(dirname)).__all__
        names.remove('__init__')
        for name in names:
            __import__('%s.%s' % (dirname, name), fromlist=(name))
        modules = [(sys.modules.get('%s.%s' % (dirname,name)), name) for name in names]
        module_dict = {}
        for module, name in modules:
            if not self.enable_modules or name in self.enable_modules: #enable_modulesが空なら常にTrue
                try:
                    class_name = [obj_name for obj_name in dir(module) if re.match(name, obj_name, re.IGNORECASE)][0]
                    module_dict[name] = getattr(module, class_name)
                except AttributeError:
                    pass
        return module_dict
    
    def _load_settings(self, settings):
        self.logging = getattr(settings, "LOGGING", False)
        if self.logging:
            if not getattr(settings, "LOG_DIR", ""):
                logpath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),"log")
            else:
                logpath = settings.LOG_DIR
            if not os.path.exists(logpath): #フォルダが存在しなければ作る
                try:
                    os.makedirs(logpath)
                except os.error:
                    sys.exit("Error : Cannot make log directory.")
            self.log_settings = {"log_dir":logpath, "log_mod":getattr(settings, "LOG_MOD", [])}
        if not getattr(settings, "INOUT", {}):
            sys.exit("Error : No Input-to-Output matrix.")
        self.enable_modules = getattr(settings, "ENABLE_MODULES", [])
        self.input_to_output = settings.INOUT
        self.input_settings = getattr(settings, "INPUT_SETTINGS", {})
        self.output_settings = getattr(settings, "OUTPUT_SETTINGS", {})
        self.filter_settings = getattr(settings, "FILTER_SETTINGS", {})
        
    def _load_modules(self):
        self.input_modules = self._make_module_dict('lib.inputs')
        self.output_modules = self._make_module_dict('lib.outputs')
        self.filter_modules = self._make_module_dict('lib.filters')
        if not self.input_modules or not self.output_modules:
            self.log("no INPUT or OUTPUT module.", "ERROR")
            self.log("Boxnya system terminate.")
            sys.exit("Error : no INPUT or OUTPUT module.")
        for input, outputs in self.input_to_output.items(): # Outputsが空の場合の処理
            if not outputs and input in self.input_modules:
                self.input_to_output[input] = self.output_modules.keys() + self.filter_modules.keys()
            elif not outputs and input in self.filter_modules:
                self.input_to_output[input] = self.output_modules.keys()
        if self.input_settings:
            self._clone_modules(self.input_settings)
        if self.output_settings:
            self._clone_modules(self.output_settings)
    
    def _clone_modules(self, settings):
        ''' settingsにモジュールを多重化するように書いてあれば, そのモジュールをforkしておく. '''
        for name, confs in settings.items():
            if isinstance(confs, list):
                for i,conf in enumerate(confs):
                    if i==0:
                        settings[name] = conf
                    else:
                        new_name = "%s.%d" % (name, i)
                        settings[new_name] = conf
                        self._fork(new_name)
    
    def _fork(self, name):
        '''' モジュールをforkする. forkされた新しいモジュールの名前は, "hoge.1","hoge.2"になる. '''
        original_name = name.split(".")[0]
        for modules in (self.input_modules, self.filter_modules, self.output_modules):
            if original_name in modules:
                module = modules[original_name]
                module = copy.deepcopy(module)
                modules[name] = module
    
    def run(self):
        for instance in self.output_instances.values() + self.input_instances.values() + self.filter_instances.values():
            instance.start()
            self.active_number += 1
        self.log("Boxnya module run.")
        while not self.stopevent.is_set():
            self.carrier.sleep()
            while not self.carrier.empty():
                packet = self.carrier.pickup()
                if packet["type"] == "error":
                    self._error_handle(packet)
                elif packet["type"] == "start":
                    self._start_module(packet["data"])
                elif packet["type"] == "stop":
                    self._stop_module(packet["data"])
    
    def _error_handle(self, exception):
        log_text = "Exception has occured in %s : %s %s" %(exception["from"],
                    str(traceback.format_tb(exception["data"][2])), str(exception["data"][1]))
        self.log(log_text, level="ERROR")
        self._start_module(exception["from"])
    
    def join(self, timeout=None, errmsg=""):
        for name in self.input_instances.keys() + self.filter_instances.keys() + self.output_instances.keys():
            self._stop_module(name)
        self.log("Boxnya module terminated.")
        self.log("Boxnya system terminate.")
        self.logger.carrier.wake()
        self.logger.stopevent.set()
        self.logger.join()
        self.carrier.wake()
        self.stopevent.set()
        super(Master, self).join(timeout)
    
    def _start_module(self, name):
        if name in self.input_modules:
            instance = self.input_modules[name](name=name, kwargs=self.input_settings.get(name),
                                master=self, logger=self.logger, output_carriers=self.carrier_lists[name])
            instance.start()
            self.input_instances[name] = instance
            self.active_number += 1
        elif name in self.filter_modules:
            instance = self.filter_modules[name](name=name, kwargs=self.filter_settings.get(name),
                                master=self, logger=self.logger, output_carriers=self.carrier_lists[name])
            instance.carrier = self.filter_carriers[name]
            instance.carrier.clear()
            instance.start()
            self.filter_instances[name] = instance
            self.active_number += 1
        elif name in self.output_modules:
            instance = self.output_modules[name](name=name, kwargs=self.output_settings.get(name),
                                            master=self, logger=self.logger)
            instance.carrier = self.output_carriers[name]
            instance.carrier.clear()
            instance.start()
            self.output_instances[name] = instance
            self.active_number += 1
    
    def _stop_module(self, name):
        if name in self.input_instances:
            instance = self.input_instances[name]
            instance.stopevent.set()
            instance.join(0.1)
            if not instance.is_alive():
                self.input_instances.pop(name)
                self.active_number -= 1
        elif name in self.filter_instances:
            instance = self.filter_instances[name]
            instance.carrier.wake()
            instance.stopevent.set()
            instance.join(0.1)
            if not instance.is_alive():
                self.filter_instances.pop(name)
                self.active_number -= 1
        elif name in self.output_instances:
            instance = self.output_instances[name]
            instance.carrier.wake()
            instance.stopevent.set()
            instance.join(0.1)
            if not instance.is_alive():
                self.output_instances.pop(name)
                self.active_number -= 1