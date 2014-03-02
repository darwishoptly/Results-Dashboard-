import Queue
import threading

class URLThread(threading.Thread):
    def __init__(self, queue):
      threading.Thread.__init__(self)
      self.queue = queue
	  
	  
    def run(self):
      while True:
        #grabs host from queue
        host = self.queue.get()
    
        #grabs urls of hosts and prints first 1024 bytes of page
        url = urllib2.urlopen(host)
        print url.read(1024)
    
        #signals to queue job is done
        self.queue.task_done()