import sys
import threading
import Queue

class thread1(threading.Thread):
	def __init__(self, bucket):
		threading.Thread.__init__(self)
		self.bucket = bucket
	def run(self):
		for i in range(10):
			print "hoge"
		l = [1,2,3,4,5]
		try:
			print l[6]
		except IndexError:
			self.bucket.put((sys.exc_info(), self.name))
			

class thread2(threading.Thread):
	def __init__(self, bucket):
		threading.Thread.__init__(self)
		self.bucket = bucket
	def run(self):
		for i in range(10):
			print "1111"

if __name__ == "__main__":
	bucket = Queue.Queue()
	dic = {thread1.__name__:thread1,thread2.__name__:thread2}
	obj_list = [c(bucket=bucket) for c in dic.values()]
	for o in obj_list:
		o.start()
	while True:
		try:
			exc = bucket.get(block=False)
		except Queue.Empty:
			pass
		else:
			exc_type, exc_obj, exc_trace = exc[0]
			name = exc[1]
			print exc_type, exc_obj
			print name
			for o in obj_list:
				o.join()
			quit()
