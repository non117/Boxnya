# -*- coding: utf-8 -*-
import sys
import datetime
import Queue
import settings #TODO: settingsの場所どうするか

class Master(object):
	def __init__(self):
		self.input_dict = self.make_module_dict("input")
		self.output_dict = self.make_module_dict("output")
		self.message_q = Queue.Queue()
		self.error_q = Queue.Queue()
		self.syslog = open(settings.LOG_DIR,"a+")

	def make_module_dict(self,dirname):
		name_list = __import__(dirname).__all__
		name_list.remove('__init__')
		for name in name_list:
			__import__('.'.join((dirname,name)))
			return dict(zip(name_list,[sys.modules.get('.'.join((dirname,name))) for name in name_list]))

	def push_message(self, message):
		self.message_q.put(message, block=False)

	def pop_message(self):
		if self.message_q.queue:
			return self.message_q.get(block=False)

	def write_log(self, text):
		time = datetime.datetime.today().strftime("%b %d %H:%M:%S")
		log = "%s [master] %s\n" % (time, text)
		self.syslog.write(log)

	def _run(self):
		run_dict = {}
		for input_mod_name in self.input_dict.keys():
			input_obj = self.input_dict[input_mod_name](name=input_mod_name, push_method=self.push_message, bucket=self.error_q)
			input_obj.start()
			run_dict.update({input_mod_name:input_obj})
		# TODO: output threadのstart()
		return run_dict

	def start(self):
		self.run_dict = self._run()
		while True:
			if self.message_q.queue:
				pass # TODO: output threadに投げる.
			if self.error_q.queue:
				exc = self.error_q.get(block=False)
				exc_type, exc_obj, exc_trace = exc[0]
				name = exc[1]
				self.write_log("Error has occured in %s. %s" % (name, str(exc_obj)))
				obj = self.input_dict[name](name=name, push_method=self.push_message, bucket=self.error_q)
				obj.start()
		
	def close(self):
		for obj in self.run_dict.values():
			obj.join()
		self.write_log("Boxnya exiting.")
		self.syslog.close()

if __name__ == "__main__":
	pass
