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
workbook = xlsxwriter.Workbook("RevenueComparison2.xlsx");
worksheet = workbook.add_worksheet()
row, col = 0, 0


GAE_Auth_Cookie = "AJKiYcFS5VSgLmbNlvVEQpBgQPtKcNNdWAQXBtfP-wqzN6Mz1u0W7CyWTPedZ-3Sfnu462kre_H_4II24sTGff8Pjf_yaEP8lYzLijc64iUiIObE8oLFNMeYQ6eYYWNeWIQcW_1kv9-CasmHbMCPqNks14x07fEQEXxwFIw7D2urmErQVVYP0utwwerSXJGsJoxtriNGMHD67nVcrkYQ8Z8hseOeG4gO_1XIvnaWVXU7ODEyBaDj4mJdqwr9Y9tBOKjsEkZO0uho2g4dzL18GVbq5QllWSKlxmRxnJi6LMNQhjQXIXsMcv4V7GWhDpSlBsergKKU2zTxsgzoBswVoiEZXjKBTDkUXZsF2T8-5gdOrON_jKrdM1sdRqZ7cu7Bkwb9PIh69AyyRroHdJQ016f2leYzsZaiqTCcZvCQq0qD4HxEg8eVpBIoYMMgoxeYa7WxXTpk4Sh5JocVbHvvxENhR2qLGo9y6PNL19ab0YEoNc0zQwf1XRTCdQg4WFonverRrpWGH-6rJwTbD7AgLKKtnfz9Ql00YcVP0a3YzgpdTMvW4Tc-hWo8_Py42akiYSwwkrqkTqdsTpjyl0AWFs3t7Oy1wNjWYDZjH42TWMLHz6bf3Ayo3BUIIpIcw53422W_YdmiI09r1an8ptKgOuZNBw34-_slbA"



for (account_id, email) in array:
	# f043f0ea284c3304fdace69b122fc599d0583957
	account_id = 285656357
	r = requests.get("https://www.optimizely.com/admin/impersonate?email=ben.cole@mec.ca", cookies={"SACSID" : GAE_Auth_Cookie}) 
	optimizely_session = r.cookies['optimizely_session']
	

	account_token_request = requests.get("https://www.optimizely.com/admin/account_token?account_id=%s" % str(account_id), cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie}) 
	account_token = account_token_request.json()["token"]

	if account_token == None:
		print "ACCOUNT TOKEN ERROR"

	# Get Experiment ID's and Descriptions: https://www.optimizely.com/api/experiments.json?project_ids=82719230&status=Archived

	exp_descriptions = {} ## {experiment_id: description, ...}
	# for status in ["Paused%2CRunning", "Not+Started"]:
	for status in ["Paused%2CRunning", "Not+Started"]:
		experiment_ids_request = requests.get("https://www.optimizely.com/api/experiments.json?project_ids=%s&status=%s" % (str(account_id), status), 
												cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie}
											) 
		exp_descriptions = dict(exp_descriptions.items() + {str(exp_data["id"]) : {"description" : exp_data["description"],  "status" : exp_data["status"] } for exp_data in experiment_ids_request.json()["experiments"]}.items())

	print "Experiment Descriptions Created"

	# Visitors per Variation / Experiment {exp_id : { total visitors : x, variation : { v_id : x } } }
	count_visitors_request = requests.get("https://api.optimizely.com/v1/visitors/%s?experiment_ids=%s&token=%s" % (str(account_id) ,",".join(exp_descriptions.keys()), account_token), 
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
		r = requests.get("https://www.optimizely.com/results", params={"experiment_id":str(exp_id)}, cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})
		soup = BeautifulSoup(r.text)
		link = soup.find("a", {"class":"admin"})['href']
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

	## Finish building the hash 
	# {exp_id: "goals" { goal_id :  { "name" : goal_name , variation_id: "conversions": value, type: "type", "sum_of_squares" : SS_val_if_rev_goal} , goal_id : goal_name } } 

	for exp_id in exp_descriptions.keys():
		r = requests.get("https://api.optimizely.com/v1/results/%s" % (exp_id), params={"debug":"false", "bucket_count" : "1", "token":token_hash[exp_id]}, cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})
		data_arr = r.json()["data"]
		for data in data_arr:
			if data["type"] == "event_goal" or data["type"] == "revenue_goal":
				goals[exp_id]["goals"][str(data["goal_ids"][0])][data["variation_id"]] = {}
				goals[exp_id]["goals"][str(data["goal_ids"][0])][data["variation_id"]]["conversions"] = data["values"][0]
				goals[exp_id]["goals"][str(data["goal_ids"][0])][data["variation_id"]]["type"] = data["type"]				

	for exp_id in exp_descriptions.keys():
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
		if ( float(baseline["conversions"]) / float(baseline["visitors"]) > float(variation["conversions"]) / float(variation["visitors"]) ):
			p = ExpDist.expDist(baseline["visitors"], 
											baseline["conversions"], 
											variation["visitors"],
											variation["conversions"])
		else:
			p = ExpDist.expDist(variation["visitors"], 
											variation["conversions"], 
											baseline["visitors"],
											baseline["conversions"])
		if str(p) == "nan":
			return "-"
		# return p if (baseline["conversions"] / baseline["visitors"] > variation["conversions"] / variation["visitors"]) else 1.0 - p
		return p

	# worksheet.write(0,0,"test")
	# workbook.close()
	for exp_id in exp_descriptions.keys():
	# exp_id = '296378765'
		try: 
			visitor_count[exp_id]
		except:
			print ("ERROR:", exp_id, var_id)
			continue
		var_ids  = visitor_count[exp_id]['variation'].keys()
		baseline_variation_id = filter(lambda var_id: var_id == exp_descriptions[exp_id]["baseline_id"] , visitor_count[exp_id]['variation'].keys())
		baseline_variation_id = baseline_variation_id[0] if len(baseline_variation_id) > 0 else var_ids[0]
		for var_id in var_ids:
			if baseline_variation_id == var_id:
				continue
			goal_id = filter(lambda goal_id:  goals[exp_id]["goals"][goal_id]["name"] == "Total Revenue" ,goals[exp_id]["goals"].keys())
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
				writeRange(worksheet, row, col, [exp_id, var_id, ctb_normal, ctb_exponential], True)
			row+=1
			col=0


workbook.close()

