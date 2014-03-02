from multiprocessing import Process, Queue

def add_experiment_token(q):
	exp_id = q.get()
	r = requests.get("https://www.optimizely.com/results", params={"experiment_id":str(exp_id)}, cookies={"optimizely_session": self.optimizely_session, "SACSID" : self.GAE_Auth_Cookie})
	soup = BeautifulSoup(r.text)
	try:
		link = soup.find("a", {"class":"admin"})['href']
	except: 
		print "Error Creating Token Hash for Experiment", exp_id
		del(self.exp_descriptions[exp_id])
		continue		
	self.token_hash[exp_id] = link.split("token=")[1]

q = Queue()
for exp_id in exp_descriptions.keys():
	q.put(exp_id)
	
processes = [Process(target=do_work, args=(q,) for exp in exp_descriptions.keys()]
for p in processes:
	p.start()
for p in processes: 
	p.join()