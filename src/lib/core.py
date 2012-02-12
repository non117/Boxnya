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
    
    def handover(self, packet):
        ''' データをキューに入れる. 配送先のイベントを起こす '''
        self.queue.put_nowait(packet)
        self.event.set()
        self.event.clear()
    
    def pickup(self):
        ''' 配達したデータを受け取ってもらう '''
        return self.queue.get_nowait()
    
    def wake(self):
        ''' イベントを起こす '''
        self.event.set()
    
    def clear(self):
        while not self.empty():
            self.pickup()
    
    def empty(self):
        return self.queue.empty()
    
    def sleep(self):
        ''' イベントを眠らせる '''
        self.event.wait()

class BaseThread(Thread):
    ''' master, logger, input, output(filter)の基底クラス.
        master, logger, inputのoutput_carriersに, 配送先のCarrierオブジェクトを格納して引数に渡す.
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, logger=None, output_carriers=[]):
        super(BaseThread, self).__init__(group, target, name, args, kwargs, verbose)
        if isinstance(kwargs, dict): # kwargsをselfにセット
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
    
    def join(self, timeout=None):
        self.cleanup()
        super(BaseThread, self).join(timeout)
    
    def call_master(self, data, type):
        ''' masterにデータを投げる. typeはエラー, モジュールの停止要請など '''
        packet = {"data":data, "from":self.name, "type":type}
        self.master.carrier.handover(packet)
    
    def log(self, text, level='INFO'):
        ''' 自分のモジュールに関するログを書く '''
        packet = {"text":text, "from":self.name, "level":level.upper()}
        self.logger.carrier.handover(packet)
    
    def send(self, data, target_names=[]):
        ''' これでデータを投げる '''
        packet = {"data":data, "from":self.name}
        for name, carrier in self.output_carriers.items():
            if not target_names or name in target_names:# target_namesが空ならば常にTrue
                carrier.handover(copy.deepcopy(packet))

class Input(BaseThread):
    ''' ネットやシステムログなどBoxnyaの外界から定期的にデータを取ってきて, filter, outputに渡すスレッド '''
    def fetch(self):
        ''' データを取ってくる処理をここに '''
        #self.send(data, target_names)
    
    def run(self):
        try:
            while not self.stopevent.is_set():
                self.fetch()
        except Exception:
            self.call_master(sys.exc_info(), "error")

class Output(BaseThread):
    ''' inputから受け取ったデータをBoxnyaの外界に投げるスレッド '''
    def throw(self, packet):
        ''' 受け取ったデータの最終処理 '''
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
    ''' 複数の入力をまとめてフィルター処理するのに使うスレッド.
        inputからデータを受け取り, outputに渡す
    '''
    def filter(self, packet):
        ''' フィルター処理をここに書く '''
        #return data
    
    def throw(self, packet):
        data = self.filter(packet)
        if data:
            self.send(data)

class Logger(BaseThread):
    ''' ログを取るためのスレッド. Outputみたいな役割をもつ '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, settings=None):
        super(Logger, self).__init__(group, target, name, args, kwargs, verbose)
        self.master = master
        self.logger = self
        self.log_dir = settings["LOG_DIR"]
        self.loggers = {}
        # システムログを作る
        self.loggers[self.master.name] = self._logger_fuctory(self.master.name)
        # settings.LOG_MODにあるモジュールのロガーを作る
        for name in settings["LOG_MOD"]:
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
        if level >= logging.ERROR:# エラー以上のログならば, settings.LOG_OUTにログテキストを渡す
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
    ''' 全てのモジュールを管理するスレッド. モジュールのstart, stopなどはこのスレッドが行う. '''
    def __init__(self, settings, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(Master, self).__init__(group, target, "system", args, kwargs, verbose)
        self.active_number = 0 # system,logger以外で生きてるスレッドの個数
        self._set_settings(settings)
        
        if self.logging: # ロガーの起動
            self.logger = Logger(master=self, settings=self.log_settings)
            self.logger.start()
        self.log("Boxnya system started.")
        
        self._load_modules()
        self.running_outputs, self.running_inputs, self.running_filters = {},{},{}
        self.filter_carriers, self.carrier_lists, self.output_carriers = {},{},{}
        
        for name, module in self.output_modules.items(): #outputモジュールをインスタンス化
            instance = module(name=name, kwargs=self.output_settings.get(name), master=self, logger=self.logger)
            self.running_outputs[name] = instance
            self.output_carriers[name] = instance.carrier
        
        if self.logging:# ロガーのエラー出力先outputをセット
            log_outputs = self.log_settings["LOG_OUT"]
            self.logger.output_carriers = dict([(name, carrier) for name, carrier in self.output_carriers.items() 
                                           if name.split(".")[0] in log_outputs])
        
        for name, module in self.filter_modules.items(): #フィルターに出力先を渡してインスタンス化
            outputs = [carrier for output_name, carrier in self.output_carriers.items()
                               if output_name.split(".")[0] in self.input_to_output.get(name)]
            
            self.carrier_lists[name] = outputs
            instance = module(name=name, kwargs=self.filter_settings.get(name),
                        master=self, logger=self.logger, output_carriers=outputs)
            self.running_filters[name] = instance
            self.filter_carriers[name] = instance.carrier
        
        for name, module in self.input_modules.items(): #入力モジュールに出力先のメッセージを渡してインスタンス化
            outputs = [carrier for output_name, carrier in self.output_carriers.items() + self.filter_carriers.items()
                               if output_name.split(".")[0] in self.input_to_output.get(name.split(".")[0])]
            
            self.carrier_lists[name] = outputs
            self.running_inputs[name] = module(name=name, kwargs=self.input_settings.get(name),
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
    
    def _set_settings(self, settings):
        self.logging = settings["LOGGING"]
        self.log_settings = settings["LOG_SETTINGS"]
        self.enable_modules = settings["ENABLE_MODULES"]
        self.input_to_output = settings["INOUT"]
        self.input_settings = settings["INPUT_SETTINGS"]
        self.output_settings = settings["OUTPUT_SETTINGS"]
        self.filter_settings = settings["FILTER_SETTINGS"]
        
    def _load_modules(self):
        self.input_modules = self._make_module_dict('lib.inputs')
        self.output_modules = self._make_module_dict('lib.outputs')
        self.filter_modules = self._make_module_dict('lib.filters')
        if not self.input_modules or not self.output_modules:
            self.log("no INPUT or OUTPUT module.", "ERROR")
            self.log("Boxnya system terminate.")
            sys.exit("Error : no INPUT or OUTPUT module.")
        for input, outputs in self.input_to_output.items(): 
            # INOUTで, inputに対応するoutputが[]のときは, 読み込まれたoutput全てを設定
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
                    if i==0: #0番目のモジュールはそのまま
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
        for instance in self.running_outputs.values() + self.running_inputs.values() + self.running_filters.values():
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
                elif packet["type"] == "log":
                    if isinstance(packet["data"], str):
                        self.log(packet["data"])
    
    def _error_handle(self, exception):
        log_text = "Exception has occured in %s : %s %s" %(exception["from"],
                    str(traceback.format_tb(exception["data"][2])), str(exception["data"][1]))
        self.log(log_text, level="ERROR")
        self._start_module(exception["from"])
    
    def join(self, timeout=None, errmsg=""):
        for name in self.running_inputs.keys() + self.running_filters.keys() + self.running_outputs.keys():
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
            self.running_inputs[name] = instance
            self.active_number += 1
        elif name in self.filter_modules:
            instance = self.filter_modules[name](name=name, kwargs=self.filter_settings.get(name),
                                master=self, logger=self.logger, output_carriers=self.carrier_lists[name])
            instance.carrier = self.filter_carriers[name]
            instance.carrier.clear()
            instance.start()
            self.running_filters[name] = instance
            self.active_number += 1
        elif name in self.output_modules:
            instance = self.output_modules[name](name=name, kwargs=self.output_settings.get(name),
                                            master=self, logger=self.logger)
            instance.carrier = self.output_carriers[name]
            instance.carrier.clear()
            instance.start()
            self.running_outputs[name] = instance
            self.active_number += 1
    
    def _stop_module(self, name):
        if name in self.running_inputs:
            instance = self.running_inputs[name]
            instance.stopevent.set()
            instance.join(0.1)
            if not instance.is_alive():
                self.running_inputs.pop(name)
                self.active_number -= 1
        elif name in self.running_filters:
            instance = self.running_filters[name]
            instance.carrier.wake()
            instance.stopevent.set()
            instance.join(0.1)
            if not instance.is_alive():
                self.running_filters.pop(name)
                self.active_number -= 1
        elif name in self.running_outputs:
            instance = self.running_outputs[name]
            instance.carrier.wake()
            instance.stopevent.set()
            instance.join(0.1)
            if not instance.is_alive():
                self.running_outputs.pop(name)
                self.active_number -= 1