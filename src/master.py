# -*- coding: utf-8 -*-
import sys
from Queue import Queue
from threading import Event

from thread import Module, Message

class Logger(Module):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None,
                  verbose=None, master=None, settings=None):
        super(self, Module).__init__(self, group, target, name, args, kwargs, verbose)
        self.master = master
        self.settings = settings
        self.message = Message(Queue(),Event())
    def _write_log(self, data):
        pass
    def run(self):
        while True:
            self.message.wait()
            if not self.message.empty():
                data = self.message.get()
                self._write_log(data)
            else:
                self.message.wait()

class Master(Module):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(self, Master).__init__(self, group, target, name, args, kwargs, verbose)
        self.message = Message(Queue(),Event())
        self._load_settings()
        self._load_modules()
        self.logger = Logger(settings=self.log_settings)
        for mod_name, output in self.output_modules.items(): #出力モジュールをインスタンス化
            self.output_modules[mod_name] = output(kwargs=None, master=self.message, logger=self.logger.message)
        for mod_name, input in self.input_modules.items(): #入力モジュールに出力先のメッセージを渡してインスタンス化
            output_list = [out_obj.message for out_name, out_obj in self.output_modules.items() 
                           if out_name in self.input_to_output[mod_name]]
            self.input_modules[mod_name] = input(kwargs=None, master=self.message, logger=self.logger.message, outputs=output_list)
    def _make_module_dict(self, dirname):
        ''' ディレクトリ名を引数にとって, ディレクトリ内のモジュール名と同名のクラスを全て読み込む. '''
        name_list = __import__(dirname).__all__
        name_list.remove('__init__')
        for name in name_list:
            __import__('.'.join((dirname,name)))
        return dict(zip(name_list,[getattr(sys.modules.get('.'.join((dirname,name))), name) for name in name_list]))
    def _load_settings(self):
        self.log_settings = None
        self.input_to_output = {}
    def _load_modules(self):
        self.input_modules = self._make_module_dict('input')
        self.output_modules = self._make_module_dict('output')
    def _start_modules(self):
        for obj in self.output_modules.items():
            obj.start()
        for obj in self.input_modules.items():
            obj.start()
    def _stop_modules(self):
        for obj in self.output_modules.items():
            obj.join()
        for obj in self.input_modules.items():
            obj.join()
    def _error_handle(self, data):
        pass
    def run(self):
        self._start_modules()
        while True:
            self.message.wait()
            if not self.message.empty():
                data = self.message.get()
                self._error_handle(data)
            else:
                self.message.wait()