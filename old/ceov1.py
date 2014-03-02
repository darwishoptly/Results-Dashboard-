import xlsxwriter
import requests
from bs4 import BeautifulSoup
from pprint import pprint 
import VariationNames
import NormDist
import ExpDist
# r = requests.get("https://www.optimizely.com/edit?experiment_id=401420652", cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})

optimizely_session = "d4f8f5c1b8694f58334f5881e27292a7d0122c4e"
GAE_Auth_Cookie = "AJKiYcEWHki1HFOEwqPR6ueSsuxTGv9Ix5UNRgTKaVkFkTNbWAzUxsoCh6pYGfSUnj1LmgbM4Svqwi_4eZnBhulGPLBCEBYmBFk3_OFsgRcE2DYYY93bh2EAjWb8gbKoW6atLT5_lfBiu8GIb4zAvNjV6I7nwXFv5MGT0VcNOyD0BjI_59CpOO101MQCuOfT_YeMIe5d8mzwswV8xRitRvlVWYd63etSiPMw19yk3Asz4_OXbVaJ_gnR5FP0KUbjEKtYqNl9riiclye_bKtSAHN2GhecUO_inbRpuQ_wea75ARWHQ3v31jyFg3c6kiPSFUkW3G4VIykPWGA4-VwCBNYEkLQZmGpTzewF9mEcfa3C1E0yvpZqdxq07yndTOMvnRuPACSaKMmseIdV9ExxuDMICr65Jbc5yTTQzSi6lwbLwHoKhUyM47eA_kpVTdD66cP077epnDDxyqnIYsOimZwy46zd6GKKAryuE4zwHY0ellzrc4yh1G_Ao1xMldPALWkLDAXiDGZ6nAguo-cv0LzXh0R-6GawDTM3D_AuYnEHvMCK0XO8MutkR_T_KIz4_RY5zkaLc-Ve_c-P015bnUEeb_BX1Az_6FtiaRNKSSVnecZQfIbr2othP5ssSnysH9JSSJWd4VMf-wHMX9mgKTNFzW3O5pilVQ"
account_id = 285656357

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


# variation_names = VariationNames.data['variations']


workbook = xlsxwriter.Workbook("Dashboard6.xlsx");
worksheet = workbook.add_worksheet()


row = 1

title = workbook.add_format({'bold':1, 'bottom':1, 'valign': 'vcenter', 'bg_color': '#d5d5d5', "top" : 1})
title.set_text_wrap()

visitors = workbook.add_format({'bold':1, 'bottom':1, 'valign': 'vcenter', 'bg_color': '#d5d5d5', 'align': 'center', "top" : 1})
visitors.set_text_wrap()

header_center = workbook.add_format({'bold':1, 'bottom':1, 'valign': 'vcenter', 'align': 'center', 'bg_color': '#d5d5d5' , "top" : 1})
header_center.set_align('center')
header_center.set_text_wrap()
header_center.set_italic()

experiment_id_format = workbook.add_format({'bottom':1, "top": 1, 'valign': 'vcenter', 'bg_color': '#d5d5d5'})
experiment_id_format.set_italic()
experiment_id_format.set_align("center")
experiment_id_format.set_text_wrap()

center = workbook.add_format()
center.set_align("center")

goal_format = workbook.add_format({'bottom':1})
goal_format.set_text_wrap()
goal_format.set_align('center')
goal_format.set_align('vcenter')

variation_title = workbook.add_format()
variation_title.set_align('left')
variation_title.set_align('vcenter')

title_row = workbook.add_format({'bold':1, 'bottom':1, 'top':1})

improvement_row = workbook.add_format({'bold':1, 'bottom':6, 'bg_color': '#d5d5d5', 'num_format': '0.0%'})
rev_per_visitor_improvement_row_format = workbook.add_format({'bold':1, 'bottom':6, 'bg_color': '#d5d5d5', 'num_format': '0.00'})

##  / VISITOR FORMAT
conversion_rate_format = workbook.add_format({'num_format': '0.0%'})
revenue_visitor_format = workbook.add_format({'num_format': '0.00'})
boolean_format = workbook.add_format({'bold':1, 'bottom':6, 'bg_color': '#d5d5d5'})

def maxGoals():
	maximum = 0
	for exp_id in goals:
		if len(goals[exp_id]["goals"].keys()) > maximum:
			maximum = len(goals[exp_id]["goals"].keys()) 
	return maximum

max_goals = maxGoals() + 5 # +  4 for headers, 1 for visitors gives space. clean up wording later. 

print "Maximum Goals Set"


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
	p = NormDist.pVal(baseline["visitors"], 
										baseline["conversions"], 
										baseline["sum_of_squares"], 
										variation["visitors"],
										variation["conversions"],
										variation["sum_of_squares"])
	if str(p) == "nan":
		return "-"
	# return p if (baseline["conversions"] / baseline["visitors"] > variation["conversions"] / variation["visitors"]) else 1.0 - p
	return p

for exp_id in exp_descriptions.keys():
# for exp_id in ['523462609']:
	print "ADDING: Experiment ID: ", exp_id
	try: 
		visitor_count[exp_id]
	except:
		print "ERROR:", exp_id, var_id
		row += 2
		continue
	worksheet.write(row, 0, "Experiment ID: " + str(exp_id), experiment_id_format)
	worksheet.merge_range(row, 1, row, 3, exp_descriptions[exp_id]['description'], title) 
	worksheet.write(row, 4, "Total Visitors: %s" % visitor_count[exp_id]['total_visitors'], visitors)
	worksheet.merge_range(row, 5, row, max_goals, "------------Conversions------------", header_center) 
	worksheet.merge_range(row, max_goals + 2, row, max_goals + (max_goals - 5) + 1, "------------ Conversions / Visitor ------------", header_center) 
	worksheet.merge_range(row, max_goals + (max_goals - 5) + 3, row, max_goals + 2*(max_goals - 5) + 3, "------------ Chance to Beat Baseline ------------", header_center) 
	# worksheet.set_row(row, None, title_row)
	row += 1 
	## Hash to be used for calculating improvement
	## {goal_id: [1,2,3], }
	conversions = {}
	## Set up Goal Headers 
	col = max_goals
	goal_ids = goals[exp_id]["goals"]
	for goal_id in goal_ids:
		conversions[goal_id] = {"max" : 0}
		worksheet.write(row, col, goals[exp_id]["goals"][goal_id]["name"], goal_format) ## For Conversions
		worksheet.write(row, col + len(goal_ids) + 1, goals[exp_id]["goals"][goal_id]["name"], goal_format) ## For Conversion Rates
		worksheet.write(row, col + max_goals-5 + 1 + len(goal_ids) + 1, goals[exp_id]["goals"][goal_id]["name"], goal_format)
		col -= 1
	## Visitor and Variation Headers
	worksheet.write(row, 4, "Visitors" , goal_format) 
	col = 0
	worksheet.write(row, col, "Variations" , variation_title)
	row, col = row + 1, 0
	## Variation rows 
	for var_id in visitor_count[exp_id]['variation'].keys():
		variation_visitors = visitor_count[exp_id]['variation'][var_id]
		try:
			worksheet.write(row, col, variation_names[var_id])
		except:
			continue
		col = max_goals 
		for goal_id in goal_ids: 
			variation_conversions = goals[exp_id]["goals"][goal_id][var_id]["conversions"]
			if var_id != exp_descriptions[exp_id]["baseline_id"] and conversions[goal_id]["max"] < float(variation_conversions):
				conversions[goal_id]["max"] += float(variation_conversions)
				conversions[goal_id]["max_var_id"] = var_id
			else:
				conversions[goal_id]["original"] = float(variation_conversions)
				conversions[goal_id]["original_var_id"] = var_id
			worksheet.write(row, col, variation_conversions)
			format = revenue_visitor_format if goals[exp_id]["goals"][goal_id]["name"] == "Total Revenue" else conversion_rate_format
			worksheet.write(row, col + len(goal_ids) + 1, float(variation_conversions) / float(variation_visitors), format) 
			worksheet.write(row, col + max_goals-5 + 1 + len(goal_ids) + 1, CTBNormal(exp_id, var_id, goal_id), conversion_rate_format) 
			col -=1 
		## Visitor Count	
		worksheet.write(row, 4, variation_visitors)
		row, col = row + 1, 0	
	## Improvement Row
	worksheet.write(row, col, "Greatest Change from Original")
	col = max_goals
	goal_ids = goals[exp_id]["goals"]
	worksheet.set_row(row, None, improvement_row) ## must come before revenue format set
	for goal_id in goal_ids:
		try:
			worksheet.write(row, col, conversions[goal_id]["max"] / conversions[goal_id]["original"] -1, improvement_row)
			original_conv = conversions[goal_id]["original"] / visitor_count[exp_id]['variation'][conversions[goal_id]["original_var_id"]] 
			max_conv = conversions[goal_id]["max"] / visitor_count[exp_id]['variation'][conversions[goal_id]["max_var_id"]] 
			format = rev_per_visitor_improvement_row_format if goals[exp_id]["goals"][goal_id]["name"] == "Total Revenue" else improvement_row
			worksheet.write(row, col + len(goal_ids) + 1, (max_conv / original_conv) - 1, format)
			worksheet.write(row, col + max_goals-5 + 1 + len(goal_ids) + 1, CTBNormal(exp_id, conversions[goal_id]["max_var_id"], goal_id) > .95, boolean_format) 
		except:
			print "division error"
		col -= 1 
	print "ADD SUCCESSFUL"
	row += 2



worksheet.set_column('A:B', 14)
worksheet.set_column('C:LL', 15) # should make this depend on max goals 
worksheet.set_column(max_goals + max_goals-5 + 2, max_goals + max_goals-5 + 2, 4)
worksheet.set_column(max_goals + 1, max_goals + 1, 4)

worksheet.hide_gridlines()

workbook.close()
