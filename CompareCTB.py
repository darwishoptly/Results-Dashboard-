import xlsxwriter
import requests
from bs4 import BeautifulSoup
from pprint import pprint 
import VariationNames
import NormDist
import ExpDist
# r = requests.get("https://www.optimizely.com/edit?experiment_id=401420652", cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})

## 1. GAE Cookie (same for everyone)
## (account_id, email) pairs
workbook = xlsxwriter.Workbook("Comparison_Many.xlsx");
worksheet = workbook.add_worksheet()
row, col = 0, 0


authorization = [{"email" : "ben.cole@mec.ca", "project_id" : 186764410, "account_id" : 186764410},
			{"email" : "cdavin@atgstores.com", "project_id" : 285656357, "account_id" : 285656357}] 
				 
GAE_Auth_Cookie = "AJKiYcEbAXewrRJPr1XO0aFPiN7A_em-IhmImV8AXe6iSRtuXGgBf1t7pUrFPC1semcfMpGd3bk4DtvAI6sPZBTYZkdIP8wOZ5b3epIoNfz3QvlHtgNn9Bz3SwjaFyrXmmzmksswlcipqNka-Q0f2AonVxV4L4Co2qbv7APe2r4QgYlwkTGBEtoeTao2829NJhTvkreMevEJD2meOt0lQXCtlOnaPppKCEhoNTVbRzXShVnu1S940Qa_lG4afd4m4Z1N0xZWxtIEQQ0FJSemb_FYTw8y1GXyQNvj6fE2HlFp9gfa53NG9AJtQFUUOAeX2LlsP9JZwX-V47nxaOPdHVIqU8iFin5js2ouFnOd66Z9V14D6WScLgSx8zrtbAXjNuoshuotFPDYn0Rp-UT9et3xc2D8LVwmHQdqEDyYF7JpnJOnDMAEWIONqSEBVvAagNH3pxlHW4iY-OxB4dtNY4Fukgp3IzuK5Urlne4UJ_8jIc3xIr4wg2UZkoH2oF_VxdLFs7UJPZLvDZhfKcldkTDsJ4Ma9vaLah99uSE0mclDZghjVoXgX5Gnc19sNrwYaf8TwE2Da8YTqlXNuqgzmp8cAl9qLopd9VlznHxnLusewdib8M2FnS9FQKEDv2g1uShp0Xg_Uhp9nEJFrqh4SS7vKcGJKfLE8Q"



for auth in authorization:
	email = auth["email"]
	account_id = auth["project_id"]
	project_id = auth["account_id"]
	print "EMAIL: ", email, "PROJECT_ID ", project_id
	r = requests.get("https://www.optimizely.com/admin/impersonate?email=%s" % email, cookies={"SACSID" : GAE_Auth_Cookie}) 
	optimizely_session = r.cookies['optimizely_session']
	
	
	account_token_request = requests.get("https://www.optimizely.com/admin/account_token?account_id=%s" % str(project_id), cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie}) 
	account_token = account_token_request.json()["token"]
	
	if account_token == None:
		print "ACCOUNT TOKEN ERROR"
	
	# Get Experiment ID's and Descriptions: https://www.optimizely.com/api/experiments.json?project_ids=82719230&status=Archived
	
	exp_descriptions = {} ## {experiment_id: description, ...}
	# for status in ["Paused%2CRunning", "Not+Started"]:
	for status in ["Paused%2CRunning"]:
		experiment_ids_request = requests.get("https://www.optimizely.com/api/experiments.json?project_ids=%s&status=%s" % (str(account_id), status), 
												cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie}
											) 
		exp_descriptions = dict(exp_descriptions.items() + {str(exp_data["id"]) : {"description" : exp_data["description"],  "status" : exp_data["status"] } for exp_data in experiment_ids_request.json()["experiments"]}.items())
	
	print "Experiment Descriptions Created"
	
	# Visitors per Variation / Experiment {exp_id : { total visitors : x, variation : { v_id : x } } }
	count_visitors_request = requests.get("https://api.optimizely.com/v1/visitors/%s?experiment_ids=%s&token=%s" % (str(project_id) ,",".join(exp_descriptions.keys()), account_token), 
										 	cookies= {
										 		"optimizely_session": optimizely_session, 
										 		"SACSID" : GAE_Auth_Cookie
										 		}
										 ).json()
	visitor_count = {str(exp_data["id"]) : {"variation" : exp_data["by_variation"], "total_visitors": exp_data["visitor_count"]} for exp_data in count_visitors_request["experiments"]}
	
	print "Visitor Count Created"
	
	## Get token_hash
	token_hash = {}
	for exp_id in exp_descriptions.keys():
		print "....TOKEN....", exp_id
		r = requests.get("https://www.optimizely.com/results", params={"experiment_id":str(exp_id)}, cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})
		soup = BeautifulSoup(r.text)
		try:
			link = soup.find("a", {"class":"admin"})['href']
		except: 
			print "Not Started"
			del(exp_descriptions[exp_id])
			continue		
		token_hash[exp_id] = link.split("token=")[1]
	
	print "Token Hash Created"
	
	# Use Token Hash to call results api 
	# Get Goal Name and Id https://www.optimizely.com/api/experiments/227872712.json?include_results=false&token=AAKVVowAVXorInY4jd5y3YQOwk6i0GOO
	# Revenue SS https://api.optimizely.com/v1/results/227872712?callback=jQuery172036228616954758763_1384334668164&ss=true&begin=&bucket_count=200&end=&token=AAKVVowAVXorInY4jd5y3YQOwk6i0GOO&_=1384334668559
	# Get Other Goal Conversion Data https://api.optimizely.com/v1/results/227872712?bucket_count=1&end=&token=AAKVVowAVXorInY4jd5y3YQOwk6i0GOO&_=1384334668557
	
	variation_names = {}
	# Create Goal - Goal Name 
	# {exp_id: "goals" { goal_id : { "name" : goal_name } , goal_id : goal_name } } 
	goals = {}
	for exp_id in exp_descriptions.keys():
		print "....VARIATION NAMES....", exp_id
		# Combine line below with loop above, no need to generate a token hash
		## provides goals names and VARIATION NAMES
		goals[exp_id] = {"goals": {}}
		## should rename to experiments request
		req_goals = requests.get("https://www.optimizely.com/api/experiments/%s.json" % (exp_id), params={"include_results":"false", "token":token_hash[exp_id]}, cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})
		goals[exp_id]["goals"] = dict( goals[exp_id]["goals"].items() + { str(goal["id"]) : { "name" : goal["name"] } for goal in req_goals.json()["goals"] }.items())
		baseline_index = req_goals.json()["display_baseline_index"]
		exp_descriptions[exp_id]["baseline_id"] = str(req_goals.json()["variations"][baseline_index]["id"])
		for variation in req_goals.json()["variations"]:
			variation_names[str(variation["id"])] = variation["name"][0]
	
	print "Variation Names created"
	
	## Finish building the hash 
	# {exp_id: "goals" { goal_id :  { "name" : goal_name , variation_id: "conversions": value, type: "type", "sum_of_squares" : SS_val_if_rev_goal} , goal_id : goal_name } } 
	
	for exp_id in exp_descriptions.keys():
		print "....Goals....", exp_id
		r = requests.get("https://api.optimizely.com/v1/results/%s" % (exp_id), params={"debug":"false", "bucket_count" : "1", "token":token_hash[exp_id]}, cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})
		data_arr = r.json()["data"]
		for data in data_arr:
			if data["type"] == "event_goal" or data["type"] == "revenue_goal":
				goals[exp_id]["goals"][str(data["goal_ids"][0])][data["variation_id"]] = {}
				goals[exp_id]["goals"][str(data["goal_ids"][0])][data["variation_id"]]["conversions"] = data["values"][0]
				goals[exp_id]["goals"][str(data["goal_ids"][0])][data["variation_id"]]["type"] = data["type"]				
	
	for exp_id in exp_descriptions.keys():
		print "....Revenue....", exp_id
		r = requests.get("https://api.optimizely.com/v1/results/%s" % (exp_id), params={"debug":"false", "ss": "true", "bucket_count" : "1", "token":token_hash[exp_id]}, cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})			
		data_arr = r.json()["data"]
		for data in data_arr:
			if data["type"] == "revenue_goal":
				goals[exp_id]["goals"][str(data["goal_ids"][0])][data["variation_id"]]["sum_of_squares"] = int(data["sum_of_squares"])
	print "Goals Created"
	
	def writeRange(worksheet, row, start_col, values, update=False, formats = []):
	    global col
	    i = 0 
	    for v in values:
	        if len(formats) > 0:
	            f = formats[i]
	            i+=1
	        else:
	            f = workbook.add_format({});
	        worksheet.write(row, start_col, v, f)
	        start_col += 1
	    if update:
	        col = start_col
	    return
	
	def getVariationInfo(exp_id, var_id, goal_id):
		variation = {}
		goal = goals[exp_id]["goals"][goal_id][var_id]
		if goal["type"] == "event_goal":
			variation["conversions"] = float(goal["conversions"])
			variation["sum_of_squares"] = float(goal["conversions"])
		else:
			variation["conversions"] = float(goal["conversions"])
			variation["sum_of_squares"] = float(goal["sum_of_squares"])	
		variation["visitors"] = float(visitor_count[exp_id]['variation'][var_id])
		return variation
	
	def CTBNormal(exp_id, var_id, goal_id):
		try:
			baseline_variation_id = filter(lambda var_id: var_id == exp_descriptions[exp_id]["baseline_id"] , visitor_count[exp_id]['variation'].keys())[0]
		except:
			return 0.0
		if var_id == baseline_variation_id:
			return 0.0
		baseline = getVariationInfo(exp_id, baseline_variation_id, goal_id)
		variation = getVariationInfo(exp_id, var_id, goal_id)
		try:
			p = NormDist.pVal(baseline["visitors"], 
											baseline["conversions"], 
											baseline["sum_of_squares"], 
											variation["visitors"],
											variation["conversions"],
											variation["sum_of_squares"])
		except:
			p = "-"
		if str(p) == "nan":
			return "-"
		# return p if (baseline["conversions"] / baseline["visitors"] > variation["conversions"] / variation["visitors"]) else 1.0 - p
		return p
	
	def CTBExponential(exp_id, var_id, goal_id):
		try:
			baseline_variation_id = filter(lambda var_id: var_id == exp_descriptions[exp_id]["baseline_id"] , visitor_count[exp_id]['variation'].keys())[0]
		except:
			return 0.0
		if var_id == baseline_variation_id:
			return 0.0
		baseline = getVariationInfo(exp_id, baseline_variation_id, goal_id)
		variation = getVariationInfo(exp_id, var_id, goal_id)
		if variation["visitors"] == 0 or baseline["visitors"] == 0:
			return "-"
		p = ExpDist.expDist(baseline["visitors"], 
											baseline["conversions"], 
											variation["visitors"],
											variation["conversions"])
		if str(p) == "nan":
			return "-"
		# return p if (baseline["conversions"] / baseline["visitors"] > variation["conversions"] / variation["visitors"]) else 1.0 - p
		return p
	
	for exp_id in exp_descriptions.keys():
		print ".....WRITING ID ......", exp_id
		try: 
			visitor_count[exp_id]
		except:
			print ("ERROR:", exp_id, var_id)
			continue
		var_ids  = visitor_count[exp_id]['variation'].keys()
		print "..... VARIATION IDs ......", exp_id, var_ids
		baseline_variation_id = filter(lambda var_id: var_id == exp_descriptions[exp_id]["baseline_id"] , visitor_count[exp_id]['variation'].keys())
		baseline_variation_id = baseline_variation_id[0] if len(baseline_variation_id) > 0 else var_ids[0]
		for var_id in var_ids:
			if baseline_variation_id == var_id or var_id not in variation_names:
				continue
			goal_id = filter(lambda goal_id:  goals[exp_id]["goals"][goal_id]["name"] == "Total Revenue" or goals[exp_id]["goals"][goal_id][var_id]["type"] == "revenue_goal" ,goals[exp_id]["goals"].keys())
			if len(goal_id) > 0:
				goal_id = goal_id[0]
				try:
					goals[exp_id]["goals"][goal_id][var_id]
				except Exception as e:
					print "var id not", var_id, e
					continue
				ctb_normal = CTBNormal(exp_id, var_id, goal_id)
				try:
					ctb_exponential = CTBExponential(exp_id, var_id, goal_id)
				except Exception as e:
					ctb_exponential = str(e)
				print '.... values......', exp_id, var_id, ctb_normal, ctb_exponential
				writeRange(worksheet, row, col, [exp_id, var_id, ctb_normal, ctb_exponential], True)
			else:
				print "NO REVENUE GOAL"
			row+=1
			col=0
	
	print ".....FINISHED......"


workbook.close()

