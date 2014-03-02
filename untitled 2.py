import time
q = JoinableQueue()
args = (q,)
def work(args):
	args.get()
	time.sleep(10)

p = Process(target=work, args=args)


