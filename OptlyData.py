import time		
import xlsxwriter
import requests
from bs4 import BeautifulSoup
from pprint import pprint 
import NormDist
import ExpDist
import datetime
from multiprocessing import Process, JoinableQueue, Queue, Manager
from Queue import Empty
import myAdapter


# One instance of the OptlyData class holds all experiment information for a single segment id, value pair, for a given project. If no segment ID,Value pair is defined, then its for all experiments for an entire project. 

class client:
	def __init__(self, GAEAuthCookie, project_id, account_id, options={}): # options - email, optimizely_session, segment_id, segment_value 
		# requests = myAdapter.s
		self.GAE_Auth_Cookie, self.project_id, self.account_id = GAEAuthCookie, project_id, account_id
		if "optimizely_session" in options: 
			self.optimizely_session = options["optimizely_session"]
		else:
			r = requests.get("HTTPS://www.optimizely.com/admin/impersonate?email=%s" % options["email"], cookies={"SACSID" : self.GAE_Auth_Cookie}) 
			self.optimizely_session = r.cookies['optimizely_session']
		self.segment_id = options["segment_id"] if "segment_id" in options else ""
		self.segment_value = options["segment_value"] if "segment_id" in options else ""
		self.segment_request = "&segment_id=%s&segment_value=%s" % ( str(options["segment_id"]) , str(options["segment_value"]) ) if "segment_id" in options else ""
		self.segment_value_maps = options["segment_value_maps"] if "segment_value_maps" in options else None 
		self.token_hash = options["token_hash"] if "token_hash" in options else {}
		self.D = options["D"] if "D" in options else {}
		self.cookies = {"optimizely_session": self.optimizely_session,
			 			"SACSID" : self.GAE_Auth_Cookie}
		self.errors = []
		self.goals = {}
		self.inResultsCall = set()
		if "account_token" in options:
			self.account_token = options["account_token"]
		else:
			self.setAccountToken()
		self.exp_descriptions = options["exp_descriptions"] if "exp_descriptions" in options else {} 
		
		self.months_ago = options["months_ago"] if "months_ago" in options else 3
		
		if options["start"]:
			self.start()
	
	# Fully creates Optly Data Object making all necessary API calls 
	def start(self):

		self.setExperimentDescriptions(self.months_ago)
		if self.exp_descriptions == {}:
			return None
		
		self.setVisitorCount()
		if self.token_hash == {}:
			self.createTokenHash()
		self.makeExperimentsCall() ## sets variation names and original goals	
		## Finish building the hash 
		# {exp_id: "goals" { goal_id :  { "name" : goal_name , variation_id: {"conversions": value, type: "type", "sum_of_squares" : SS_val_if_rev_goal, "conversion_rate" " X, "improvment" : X,  "CTB" : X }}}} 
		self.safelyMakeResultsCall()
		self.makeRevenueCall()
		# D.setGoals()
		self.setResultStatistics()
		self.setGoalNames()
	
	def setAccountToken(self):
		account_token_request = requests.get("HTTPS://www.optimizely.com/admin/account_token?account_id=%s" % str(self.account_id), cookies=self.cookies) 
		self.account_token = account_token_request.json()["token"]
		if self.account_token == None:
			raise "ACCOUNT TOKEN ERROR"
	
	def setExperimentDescriptions(self, months_ago=3):
		# Get Experiment ID's and Descriptions: HTTPSs://www.optimizely.com/api/experiments.json?project_ids=82719230&status=Archived
		# self.exp_descriptions = {} ## {experiment_id: description, ...}
		if self.exp_descriptions == {}:
			for status in ["Paused%2CRunning", "Archived"]:
			# for status in ["Archived"]:				
				experiment_ids_request = requests.get("HTTPS://www.optimizely.com/api/experiments.json?project_ids=%s&status=%s" % (str(self.project_id), status), cookies={"optimizely_session": self.optimizely_session, "SACSID" : self.GAE_Auth_Cookie } ) 
				self.exp_descriptions = dict(self.exp_descriptions.items() + {str(exp_data["id"]) : {"description" : exp_data["description"],  "status" : exp_data["status"] , "last_modified" : exp_data["last_modified"] } for exp_data in experiment_ids_request.json()["experiments"]}.items())
			self.removeOldExperiments(months_ago)
		for exp_id in self.exp_descriptions.keys():
			print "exp_descriptions,", exp_id, self.segment_id, self.segment_value
			if (self.segment_request != "") and (self.segment_id in self.segment_value_maps[exp_id]) and (self.segment_value not in self.segment_value_maps[exp_id][self.segment_id]):
				print "deleting", exp_id
				del self.exp_descriptions[exp_id]
		print "Experiment Descriptions Created: length, ", len(self.exp_descriptions)
	
	def removeOldExperiments(self, months_ago):
		for exp_id in self.exp_descriptions.keys():
			t = self.exp_descriptions[exp_id]['last_modified']
			exp_date = datetime.datetime.strptime(t[0:-1], "%Y-%m-%dT%H:%M:%S")
			ago = datetime.datetime.today() - datetime.timedelta(months_ago*365/12)	
			if (exp_date - ago).days < 0:
				del self.exp_descriptions[exp_id]
	
	def setVisitorCount(self):
		# Visitors per Variation / Experiment {exp_id : { total visitors : x, variation : { v_id : x } } }
		if self.segment_request != "":
			self.visitor_count = {}
			self.safelyMakeResultsCall() ## Can only call this after token hash set 
			print "length exp descriptions", len(self.exp_descriptions.keys())
			self.sumVisitorCount()
		else:
			count_visitors_request = requests.get("HTTPS://api.optimizely.com/v1/visitors/%s?experiment_ids=%s&token=%s" % (str(self.account_id) ,",".join(self.exp_descriptions.keys()), self.account_token), cookies= self.cookies).json()
			self.visitor_count = {str(exp_data["id"]) : {"variation" : exp_data["by_variation"], "total_visitors": exp_data["visitor_count"]} for exp_data in count_visitors_request["experiments"]}
		print "Visitor Count Created", len(self.visitor_count)
	
	def add_experiment_token(self, q, output, extra):
		exp_id = q.get()
		# print "....TOKEN....", exp_id
		r = requests.get("HTTPS://www.optimizely.com/results", params={"experiment_id":str(exp_id)}, cookies={"optimizely_session": self.optimizely_session, "SACSID" : self.GAE_Auth_Cookie})
		soup = BeautifulSoup(r.text)
		try:
			link = soup.find("a", {"class":"admin"})['href']
			output.put((exp_id, link.split("token=")[1]))
		except Exception as E: 
			print "Error Creating Token Hash for Experiment", exp_id, E
			extra.put(exp_id)	
		q.task_done()
				
	
	def createTokenHash(self):
		self.token_hash = {}
		(output, delete) = self.batchProcess(self.exp_descriptions, self.add_experiment_token)
		while True:
			try:
				pair = output.get(block=False)
				self.token_hash[pair[0]] = pair[1]
			except Empty:
				break
		while True:
			try:
				exp_id = delete.get(block=False)
				del self.exp_descriptions[exp_id]
			except Empty:
				break
		print "token hash done", len(self.token_hash)
	
	def setVisitorCountFromResultsApi(self, exp_id, data):
		if exp_id not in self.visitor_count:
			self.visitor_count[exp_id] = {"variation": {}}
		self.visitor_count[exp_id]["variation"][data["variation_id"]] = data["values"][0]
		
	def sumVisitorCount(self):
		for exp_id in self.visitor_count:
			total_visitors = 0
			for var_id in self.visitor_count[exp_id]["variation"]:
				total_visitors += int(self.visitor_count[exp_id]["variation"][var_id])
			self.visitor_count[exp_id]["total_visitors"] = total_visitors
	
	def batchProcess(self, arr_to_enque, work_method, t=False):
		q = JoinableQueue()
		output = JoinableQueue()
		extra = JoinableQueue()
		third = JoinableQueue()
		if t: 
			args = ((q, output, extra, third))
		else:
			args=(q, output, extra)
		for obj in arr_to_enque:
			q.put(obj)
		processes = [Process(target=work_method, args=args, name=str(obj)) for obj in arr_to_enque]
		for p in processes:
			p.start()
		for p in processes: 
			p.join(30)
			if p.is_alive():
				print "ERROR JOINING PROCESS FOR: ", p.name
				[p.terminate() for p in processes if p.is_alive()]
				raise Exception("Goal Conversion Error:", (self.account_id, self.project_id))
		print "end batch process"
		if t:
			return (output, extra, third)
		else:
			return (output, extra)
	
	def add_visitor_call(self, q, output, extra):
		exp_id = q.get()
		# print "results call, recieved", exp_id, "into queue"
		r = requests.get("HTTPS://api.optimizely.com/v1/results/%s" % (exp_id), params={"debug":"false", "bucket_count" : "1", "token": self.token_hash[exp_id], "segment_id" : self.segment_id, "segment_value" : self.segment_value }, cookies={"optimizely_session": self.optimizely_session, "SACSID" : self.GAE_Auth_Cookie}).json()["data"]
		if r!= []:
			for data in r:
				goal_type = data["type"]
				var_id, conversions = data["variation_id"], data["values"][0]
				if goal_type != "event_goal" and goal_type != "revenue_goal":
					goal_id = "" 
					output.put((exp_id, goal_id, var_id, conversions, goal_type))
				else:
					for goal_id in data["goal_ids"]:
						output.put((exp_id, str(goal_id), var_id, conversions, goal_type))
		else:
			print "failure", exp_id
			extra.put(exp_id)
		q.task_done()
	
	def processVisitors(self, output, extra):
		print "processing visitors"
		while True:
			try:
				(exp_id, goal_id, var_id, conversions, goal_type) = output.get_nowait()	
				print "result calls, successfully inserting into goals (exp_id, goal_id, var_id, conversions, goal_type):", exp_id, goal_id, var_id, conversions, goal_type
				self.inResultsCall.add((exp_id, goal_id, var_id, goal_type))
				if self.segment_request != "":
					if exp_id not in self.visitor_count:
						self.visitor_count[exp_id] = {"variation": {}}
					if goal_type != "event_goal" and goal_type != "revenue_goal":
						self.visitor_count[exp_id]["variation"][var_id] = conversions
				if goal_type != "visitor":
					if exp_id not in self.goals:
						self.goals[exp_id] = {"goals": {goal_id : {}}}
						self.goals[exp_id]["goals"][goal_id] = {var_id : { "conversions" : conversions, "type": goal_type }}
					elif goal_id not in self.goals[exp_id]["goals"]:
						self.goals[exp_id]["goals"][goal_id] = {var_id : { "conversions" : conversions, "type": goal_type }}
					else:
						self.goals[exp_id]["goals"][goal_id].update({var_id : { "conversions" : conversions, "type": goal_type }})
					output.task_done()
			except Empty:
				break
		while True:
			try:
				exp_id = extra.get_nowait()	
				print "no results existed for exp2:", exp_id
				del self.exp_descriptions[exp_id]
				extra.task_done()
			except Empty:
				break
	
	def makeResultsCallSlow(self, step=20):
		exp_ids = self.exp_descriptions.keys()
		print "LENGTH USED: ", len(exp_ids), exp_ids
		i = 0
		while True:
			if i + step > len(exp_ids):
				first, last = i, len(exp_ids)
				self.makeResultsCall(exp_ids[first:last])
				break
			else: 
				first, last = i, i+step
			print exp_ids[i:i+step], len(exp_ids[i:i+step]), i
			self.makeResultsCall(exp_ids[first:last])
			i = i + step		

	def makeResultsCall(self, exp_ids=None): ## Token hash must be set first
		print "...... Making Results Call ...... "
		exp_ids = exp_ids or self.exp_descriptions.keys()
		(output, extra) = self.batchProcess(exp_ids, self.add_visitor_call)
		self.processVisitors(output, extra)
		print "Results Call made."
	
	def safelyMakeResultsCall(self):
		try:
			self.makeResultsCall()
		except:		
			try:
				self.makeResultsCallSlow(15)	
			except: 
				try:
					print "trying slower call"
					self.makeResultsCallSlow(5)	
				except:
					print "trying slower call 3"
				
					self.makeResultsCallSlow(3)
		
	def add_experiment_call(self, q, output, extra, third):
		exp_id = q.get()
		req_goals = requests.get("HTTPS://www.optimizely.com/api/experiments/%s.json" % (exp_id), params={"include_results":"false", "token": self.token_hash[exp_id]}, cookies={"optimizely_session": self.optimizely_session, "SACSID" : self.GAE_Auth_Cookie}).json()
		for goal in req_goals["goals"]: 
			output.put((exp_id, str(goal["id"]), goal["name"]))
		for variation in req_goals["variations"]:
			third.put((str(variation["id"]), "_".join(variation["name"])))
		baseline_index = req_goals["display_baseline_index"]
		extra.put((exp_id, req_goals["earliest"], req_goals["latest"], str(req_goals["variations"][baseline_index]["id"])))	
		q.task_done()
	
	def makeExperimentsCall(self):
		print "......... Making Experiments API Call (e_id, g_id, v_id) ..........."
		self.variation_names = {}
		exp_ids = self.exp_descriptions.keys()
		(output, extra, third) = self.batchProcess(exp_ids, self.add_experiment_call, True)
		while True:
			try:
				data = output.get(block=False)
				exp_id, goal_id, goal_name = data[0], data[1], data[2]
				print "Experiments Call: ", exp_id, goal_id, goal_name
				if exp_id not in self.goals:
					self.goals[exp_id] = {"goals": {goal_id : {}}}
					self.goals[exp_id]["goals"][goal_id] = { "name" : goal_name }
				elif goal_id not in self.goals[exp_id]["goals"]:
					self.goals[exp_id]["goals"][goal_id] = { "name" : goal_name }
				else:
					self.goals[exp_id]["goals"][goal_id].update({ "name" : goal_name })	
			except Empty:
				break
		while True:
			try:
				d = extra.get(block=False)
				self.exp_descriptions[d[0]]["earliest"] = d[1]
				self.exp_descriptions[d[0]]["latest"] = d[2]
				self.exp_descriptions[d[0]]["baseline_id"] = d[3]
			except Empty:
				break
		while True: 
			try: 
				d = third.get(block=False)
				self.variation_names[d[0]] = d[1]
			except Empty:
				break
		print "Experiments Call Made", "Length:", len(self.goals)	
	
	def addRevenue(self, q, output, extra):
		"......... Making Revenue API Call (e_id, g_id, v_id) ..........."
		exp_id = q.get()
		r = requests.get("HTTPS://api.optimizely.com/v1/results/%s" % (exp_id), params={"debug":"false", "ss": "true", "bucket_count" : "1", "token": self.token_hash[exp_id], "segment_id" : self.segment_id, "segment_value" : self.segment_value }, cookies={"optimizely_session": self.optimizely_session, "SACSID" : self.GAE_Auth_Cookie})			
		data_arr = r.json()["data"]
		for data in data_arr:
			if data["type"] == "revenue_goal":
				print "..revenue..", exp_id, data["goal_ids"][0], data["variation_id"], int(data["sum_of_squares"])
				output.put( (exp_id, str(data["goal_ids"][0]), data["variation_id"], int(data["sum_of_squares"])) )
		q.task_done()
		
	def makeRevenueCall(self):	
		(output, extra) = self.batchProcess(self.exp_descriptions.keys(), self.addRevenue)
		while True: 
			try: 
				d = output.get(block=False)
				self.goals[d[0]]["goals"][d[1]][d[2]]["sum_of_squares"] = d[3]
			except Empty:
				break
	
	def setGoals(self):
		# Create Goal - Goal Name 
		# {exp_id: "goals" { goal_id : { "name" : goal_name, var_id : {"conversions" : X , "type" : X, "c-rate" : "X", "CTB": X, "improvement" : X } } } }
		# self.goals = {}
		time.sleep(1)
		self.makeExperimentsCall() ## sets variation names and original goals	
		time.sleep(2)	
		## Finish building the hash 
		# {exp_id: "goals" { goal_id :  { "name" : goal_name , variation_id: {"conversions": value, type: "type", "sum_of_squares" : SS_val_if_rev_goal, "conversion_rate" " X, "improvment" : X,  "CTB" : X }}}} 
		self.makeResultsCallSlow(3)	
		time.sleep(2)
		self.makeRevenueCall()
		
		print "Goals Created"
	
	def createGoalCount(self):
	    goal_count = {}
	    for exp_id in self.goals:
	        goal_ids = self.goals[exp_id]['goals'].keys()
	        for goal_id in goal_ids:
	            if goal_id in goal_count:
	                goal_count[goal_id] += 1
	            else:
	                goal_count[goal_id] = 1
	    return sorted(goal_count.items(), key=lambda x: x[1],reverse=True)
		
	def setGoalNames(self):
	    self.goal_names = {}
	    for exp_id in self.goals:
	        goal_ids = self.goals[exp_id]['goals'].keys()	
	        for goal_id in goal_ids:
	            if goal_id not in self.goal_names:
	                self.goal_names[goal_id] = self.goals[exp_id]['goals'][goal_id]["name"]
	    return self.goal_names
	
	def maxGoals(self):
		maximum = 0
		for exp_id in self.goals:
			if len(self.goals[exp_id]["goals"].keys()) > maximum:
				maximum = len(self.goals[exp_id]["goals"].keys()) 
		return maximum
	
	def getVariationInfo(self, exp_id, var_id, goal_id):
		variation = {}
		goal = self.goals[exp_id]["goals"][goal_id][var_id]
		if goal["type"] == "event_goal":
			variation["conversions"] = float(goal["conversions"])
			variation["sum_of_squares"] = float(goal["conversions"])
		else:
			variation["conversions"] = float(goal["conversions"])
			variation["sum_of_squares"] = float(goal["sum_of_squares"])	
		variation["visitors"] = float(self.visitor_count[exp_id]['variation'][var_id])
		return variation
	
	def CTBNormal(self, exp_id, var_id, goal_id):
		try:
			baseline_variation_id = filter(lambda var_id: var_id == self.exp_descriptions[exp_id]["baseline_id"] , self.visitor_count[exp_id]['variation'].keys())[0]
		except:
			return 0.0
		if var_id == baseline_variation_id:
			return 0.0
		baseline = self.getVariationInfo(exp_id, baseline_variation_id, goal_id)
		variation = self.getVariationInfo(exp_id, var_id, goal_id)
		try:
			# p = NormDist.pVal(baseline["visitors"], 
			# 								baseline["conversions"], 
			# 								baseline["sum_of_squares"], 
			# 								variation["visitors"],
			# 								variation["conversions"],
			# 								variation["sum_of_squares"])
			p = ExpDist.expDist(baseline["visitors"], baseline["conversions"], variation["visitors"], variation["conversions"])
		except:
			p = "-"
		if str(p) == "nan":
			return "-"
		# return p if (baseline["conversions"] / baseline["visitors"] > variation["conversions"] / variation["visitors"]) else 1.0 - p
		return p
	
	def CTBExponential(self, exp_id, var_id, goal_id):
		try:
			baseline_variation_id = filter(lambda var_id: var_id == self.exp_descriptions[exp_id]["baseline_id"] , self.visitor_count[exp_id]['variation'].keys())[0]
		except:
			return 0.0
		if var_id == baseline_variation_id:
			return 0.0
		baseline = self.getVariationInfo(exp_id, baseline_variation_id, goal_id)
		variation = self.getVariationInfo(exp_id, var_id, goal_id)
		if variation["visitors"] == 0 or baseline["visitors"] == 0:
			return "-"
                if variation["conversions"] == 0 and baseline["conversions"] == 0:
			return "-"
                if variation["conversions"] == 0:
                        return "0"
                if variation["conversions"] > 0 and baseline["conversions"] == 0:
			return "1"
		p = ExpDist.expDist(baseline["visitors"], 
											baseline["conversions"], 
											variation["visitors"],
											variation["conversions"])
		if str(p) == "nan":
			return "-"
		# return p if (baseline["conversions"] / baseline["visitors"] > variation["conversions"] / variation["visitors"]) else 1.0 - p
		return p		
	
	def getGoalConversions(self, exp_id, var_id, goal_id):
		visitors = self.visitor_count[exp_id]['variation'][var_id]
		print exp_id, goal_id, var_id
		if var_id not in self.goals[exp_id]["goals"][goal_id]:
			# self.errors.append(("STATS", self.account_id, self.project_id, exp_id, var_id))
			print ("VARIATION DELETED", self.account_id, self.project_id, exp_id, var_id)
			conversions, conversion_rate = "-", "-"
		else:
			conversions = self.goals[exp_id]["goals"][goal_id][var_id]["conversions"]
			if visitors > 100:
				conversion_rate = float(conversions) / float(visitors)
			else:
				conversion_rate = "-"
		return (conversions, conversion_rate)
	
	def getGoalValues(self, exp_id, var_id, goal_id, baseline_variation_id):
	    conversions, conversion_rate = self.getGoalConversions(exp_id, var_id, goal_id)
	    if var_id == baseline_variation_id:
	        return (conversions, conversion_rate, "-", "-")
	    else:
	        conversions, conversion_rate = self.getGoalConversions(exp_id, var_id, goal_id)
	        b_conversions, b_conversion_rate = self.getGoalConversions(exp_id, baseline_variation_id, goal_id)
	        improvement = "-" if (b_conversion_rate == 0 or conversion_rate == "-" or b_conversion_rate == "-") else (float(conversion_rate) / float(b_conversion_rate)) - 1
	        CTB = self.CTBExponential(exp_id, var_id, goal_id) if (conversions > 25 and b_conversions > 25) else "-"
	        return (conversions, conversion_rate, improvement, CTB)
	
	def setResultStatistics(self):
		for exp_id in self.exp_descriptions.keys():
			print "......STATS......", exp_id
			if exp_id not in self.visitor_count or exp_id not in self.goals:
				print ("ERROR:", exp_id)
				continue
			goal_ids = self.goals[exp_id]["goals"].keys()
			var_ids = self.visitor_count[exp_id]['variation'].keys()
			baseline_variation_id = filter(lambda var_id: var_id == self.exp_descriptions[exp_id]["baseline_id"] , var_ids)
			baseline_variation_id = baseline_variation_id[0] if len(baseline_variation_id) > 0 else var_ids[0]
			for var_id in var_ids:
				col = 0
				if var_id not in self.variation_names:
					print "..........VARIATION DELETED........ ", var_id	
					## right here is where you made change for improvement key not showing up 
					# for goal_id in goal_ids:
					# 	if var_id in self.goals[exp_id]['goals'][goal_id]:
					# 		del self.goals[exp_id]['goals'][goal_id][var_id]
					continue
				for goal_id in goal_ids:           
					(conversions, conversion_rate, improvement, CTB) = self.getGoalValues(exp_id, var_id, goal_id, baseline_variation_id)
					self.goals[exp_id]["goals"][goal_id][var_id]["conversions"] = conversions
					self.goals[exp_id]["goals"][goal_id][var_id]["conversion_rate"] = conversion_rate
					self.goals[exp_id]["goals"][goal_id][var_id]["improvement"] = improvement
					self.goals[exp_id]["goals"][goal_id][var_id]["CTB"] = CTB
					if var_id == baseline_variation_id: 
						self.goals[exp_id]["goals"][goal_id][var_id]["baseline"] = True
	
	# COULD NOT GET THIS TO WORK	
	def makeResultsCallSafe(self):
		# Had Trouble Getting this to work. Hash
		print "...... Making SAFE Results Call ...... "
		exp_producer = JoinableQueue()
		self.output = JoinableQueue()
		errors = JoinableQueue()
		c_process = Process(target=self.processVisitorsSafe, args=(self.output, errors))
		processes = [Process(target=self.add_visitor_call, args=(exp_producer, self.output, errors)) for exp_id in self.exp_descriptions.keys()]
		for p in processes:
			p.start()
		c_process.start()
		for exp_id in self.exp_descriptions.keys():
			exp_producer.put(exp_id)
		for p in processes: 
			p.join()
		c_process.terminate()
		
	# COULD NOT GET THIS TO WORK
	def processVisitorsSafe(self, output, extra):
		print "processing visitors"
		while True:
			try:
				(exp_id, goal_id, var_id, conversions, goal_type) = output.get(block=True)	
				if self.segment_request != "":
					if exp_id not in self.visitor_count:
						self.visitor_count[exp_id] = {"variation": {}}
					if goal_type != "event_goal" and goal_type != "revenue_goal":
						self.visitor_count[exp_id]["variation"][var_id] = conversions
				if goal_type != "visitor":
					print "result calls, successfully inserting into goals (exp_id, goal_id, var_id, conversions, goal_type):", exp_id, goal_id, var_id, conversions, goal_type
					if exp_id not in self.goals:
						print "inside1"
						self.goals[exp_id] = {"goals": {goal_id : {}}}
						self.goals[exp_id]["goals"][goal_id] = {var_id : { "conversions" : conversions, "type": goal_type }}
					elif goal_id not in self.goals[exp_id]["goals"]:
						print "inside2"
						self.goals[exp_id]["goals"][goal_id] = {var_id : { "conversions" : conversions, "type": goal_type }}
					else:
						print "inside3: ", conversions, goal_type 						
						self.goals[exp_id]["goals"][goal_id].update({var_id : { "conversions" : conversions, "type": goal_type }})
					output.task_done()
			except Empty:
				print "Empty"
		# while True:
		# 	try:
		# 		exp_id = extra.get_nowait()	
		# 		print "no results existed for exp2:", exp_id
		# 		del self.exp_descriptions[exp_id]
		# 		extra.task_done()
		# 	except Empty:
		# 		break