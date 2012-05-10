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
        ''' キューを空っぽにする '''
        while not self.empty():
            self.pickup()
    
    def empty(self):
        ''' キューが空かどうかを返す '''
        return self.queue.empty()
    
    def sleep(self):
        ''' イベントを眠らせる '''
        self.event.wait()

class BaseThread(Thread):
    ''' master, logger, input, output(filter)の基底クラス.
        master, logger, inputのoutput_carriersに, 配送先のCarrierオブジェクトを格納して引数に渡す.
    '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, logger=None, output_carriers={}):
        super(BaseThread, self).__init__(group, target, name, args, kwargs, verbose)
        # kwargsをインスタンスにセットする
        if isinstance(kwargs, dict):
            for k,v in kwargs.items():
                if not k in ("name", "master", "logger", "output_carriers"): # 予約語
                    setattr(self, k, v)
        self.daemon = True
        self.master = master
        self.logger = logger
        self.output_carriers = output_carriers
        self.carrier = Carrier(name)
        self.stopevent = Event()
        self.history = []
        self.init()
        self.output_names = set(self.output_carriers.keys())
    
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
    
    def send(self, data, target=[], exclude=[]):
        ''' これでデータを投げる '''
        packet = {"data":data, "from":self.name}
        # target, excludeの成形
        if isinstance(target, str):
            target = [target]
        if isinstance(exclude, str):
            exclude = [exclude]
        # setで集合演算. targetを優先する.
        if target:
            output_names = self.output_names & set(target)
        else:
            output_names = self.output_names - set(exclude)
        
        for name in output_names:
            self.output_carriers[name].handover(copy.deepcopy(packet))
    
    def sendable(self, message):
        ''' 送信可能かどうかをチェックする '''
        if message in self.history:
            return False
        self.history.append(message)
        if len(self.history) > 20:
            self.history.pop(0)
        return True

class Input(BaseThread):
    ''' ネットやファイルシステムなどBoxnyaの外界から定期的にデータを取ってきて, filter, outputに渡すスレッド '''
    def fetch(self):
        ''' データを取ってくる処理をここに '''
        #self.send(data, target, exclude)
    
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
        #self.send(data, target, exclude)
    
    def throw(self, packet):
        self.filter(packet)

class Logger(BaseThread):
    ''' ログ出力するためのスレッド. '''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, settings=None):
        super(Logger, self).__init__(group, target, "logger", args, kwargs, verbose)
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
        logger = self.loggers.get(packet["from"])
        if logger:
            logger.log(level, packet["text"])
            # エラー以上のログならば, settings.LOG_OUTにログテキストを渡す
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
            self.call_master(sys.exc_info(), "error") #TODO: Loggerの再起動処理

class Master(BaseThread):
    ''' 全てのモジュールを管理するスレッド. モジュールのstart, stopなどはこのスレッドが行う. '''
    def __init__(self, settings, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(Master, self).__init__(group, target, "system", args, kwargs, verbose)
        self.modules = {} # 全てのモジュールのインスタンスを保持
        self.settings = {}
        self.output_carriers = {}
        
        self._set_settings(settings)
        # ロガーの起動
        if self.logging:
            self.logger = Logger(master=self, settings=self.log_settings)
            self.logger.start()
        self.log("Boxnya system started.")
        self._load_modules()
        
        #outputモジュールをインスタンス化
        for name, module in self.output_modules.items():
            instance = module(name=name, kwargs=self.settings.get(name), master=self, logger=self.logger)
            self.modules[name] = instance
            self.output_carriers[name] = instance.carrier
        
        # ロガーのエラー出力先outputをセット
        if self.logging:
            log_outputs = self.log_settings["LOG_OUT"]
            self.logger.output_carriers = dict([(name, carrier) for name, carrier in self.output_carriers.items() 
                                                                if name.split(".")[0] in log_outputs])
            self.logger.output_names = set(log_outputs)
        
        #フィルターに出力先を渡してインスタンス化
        for name, module in self.filter_modules.items():
            outputs = dict([(output_name, carrier) for output_name, carrier in self.output_carriers.items()
                                    if output_name.split(".")[0] in self.input_to_output.get(name.split(".")[0])])
            
            instance = module(name=name, kwargs=self.settings.get(name),
                              master=self, logger=self.logger, output_carriers=outputs)
            self.modules[name] = instance
            self.output_carriers[name] = instance.carrier
        
        #入力モジュールに出力先のメッセージを渡してインスタンス化
        for name, module in self.input_modules.items():
            outputs = dict([(output_name, carrier) for output_name, carrier in self.output_carriers.items()
                                    if output_name.split(".")[0] in self.input_to_output.get(name.split(".")[0])])
            
            instance = module(name=name, kwargs=self.settings.get(name),
                                                master=self, logger=self.logger, output_carriers=outputs)
            self.modules[name] = instance

    def _make_module_dict(self, dirname):
        ''' ディレクトリ名を引数にとって, ディレクトリ内のモジュール名と同名のクラスを全て読み込む. '''
        names = __import__(dirname, fromlist=(dirname)).__all__
        names.remove('__init__')
        for name in names:
            __import__('%s.%s' % (dirname, name), fromlist=(name))
        modules = [(sys.modules.get('%s.%s' % (dirname,name)), name) for name in names]
        module_dict = {}
        for module, name in modules:
            if self.enable_modules == [] or name in self.enable_modules: #enable_modulesが空なら常にTrue
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
        self.settings.update(settings["MODULE_SETTINGS"])
        for name, dic in self.settings.items():
            if "include" in dic:
                for mod_name in dic["include"]:
                    self.settings[name][mod_name] = self.settings[mod_name]
    
    def _load_modules(self):
        self.input_modules = self._make_module_dict('lib.inputs')
        self.output_modules = self._make_module_dict('lib.outputs')
        self.filter_modules = self._make_module_dict('lib.filters')
        if self.input_modules == {} or  self.output_modules == {}:
            self.log("no INPUT or OUTPUT module.", "ERROR")
            self.log("Boxnya system terminate.")
            sys.exit("Error : no INPUT or OUTPUT module.")
        
        for input, outputs in self.input_to_output.items(): 
            # INOUTで, inputに対応するoutputが[]のときは, 読み込まれたoutput全てを設定
            if outputs == [] and input in self.input_modules:
                self.input_to_output[input] = self.output_modules.keys() + self.filter_modules.keys()
            elif outputs == [] and input in self.filter_modules:
                self.input_to_output[input] = self.output_modules.keys()

        # settingsにモジュールを多重化するように書いてあれば, そのモジュールをforkしておく
        for name, confs in self.settings.items():
            if isinstance(confs, list):
                for i,conf in enumerate(confs):
                    if i==0: #0番目のモジュールはそのまま
                        self.settings[name] = conf
                    else:
                        new_name = "%s.%d" % (name, i)
                        self.settings[new_name] = conf
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
        for instance in self.modules.values():
            instance.start()
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
        log_text = "Exception has occured in %s : %s %s" % (
                            exception["from"],
                            str(traceback.format_tb(exception["data"][2])),
                            str(exception["data"][1])
                    )
        self.log(log_text, level="ERROR")
        self._start_module(exception["from"])
    
    def join(self, timeout=None, errmsg=""):
        for name in self.modules.values():
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
        outputs = dict([(output_name, carrier) for output_name, carrier in self.output_carriers.items()
                            if output_name.split(".")[0] in self.input_to_output.get(name.split(".")[0],[])])
        if name in self.input_modules:
            instance = self.input_modules[name](name=name, kwargs=self.settings.get(name),
                                master=self, logger=self.logger, output_carriers=outputs)
            instance.start()
            self.modules[name] = instance
        elif name in self.filter_modules:
            instance = self.filter_modules[name](name=name, kwargs=self.settings.get(name),
                                master=self, logger=self.logger, output_carriers=outputs)
            instance.carrier = self.output_carriers[name]
            instance.carrier.clear()
            instance.start()
            self.modules[name] = instance
        elif name in self.output_modules:
            instance = self.output_modules[name](name=name, kwargs=self.settings.get(name),
                                            master=self, logger=self.logger)
            instance.carrier = self.output_carriers[name]
            instance.carrier.clear()
            instance.start()
            self.modules[name] = instance
    
    def _stop_module(self, name):
        if name in self.modules:
            instance = self.modules[name]
            instance.carrier.wake()
            instance.stopevent.set()
            instance.join(1)
            if not instance.is_alive():
                self.modules.pop(name)
                return True
            return False