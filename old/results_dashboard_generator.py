import xlsxwriter
import requests
from bs4 import BeautifulSoup
from pprint import pprint 
import VariationNames

# r = requests.get("https://www.optimizely.com/edit?experiment_id=401420652", cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})

optimizely_session = "dcbaa08c4ad8733945505d4818ff369bad58292d"
GAE_Auth_Cookie = "AJKiYcH8CXdUJ2Mm2DSlZEzEKFYApcT67uBd3QzAmejaRB_CxRVowPI1N2vSYEg5stFA0yguAFsRGMwMQEhAOG5iojPaPdE4z0mFgDahdevPjwhnOWwq4qBcQG-MypoPb4uxp8Y7szx4k95ZZaAaIwB5Skln-KIvqPnYyacobnCHs_4ujqRUXqBqERYp2On8qqz6ncWKmCZ8ni69GxIOXyNNr7PDQX4wRzQdyLCZslM3mP05lJbC-1x0Gy-SG7WC6OUhvwp7BBrNkpXLEI7YmYdu7yARn1C7j1s2tM7spnpE2ntGea_veQdhyCELMTVDJF-5fvdDvdJV-hxaIFj6JD5CSJYnoMLqITRw9VwnP7-ZHBVmAqPpxpcwj4Hz5ID0Wi3axFWyXc8alnnIGBQ85R666PL1BZ4v6x8MPiJf2ezR17mFrRY2CiQqc6zI3VeqGw4J5e4oauiRLb-w96fylU-6fyZhFs4rHq0lNMth_8m0wpPhPfzFedsKajr9kFCTWkTV5vX_IvpZ_JbkV6YDkM_QrONEHvQfluC1m3wpXh2i3DEP94JKdEdR1uCbiMyfa12-0cghA9-Ka5gSdTHvyLdqxYtP6YDWPgKaU5A_LIlAqn-QQxTqFLHo2yWioX-nNoPZ4UhpgA9JUGIDD_bl_nNnF5PMLWyBSQ"
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


workbook = xlsxwriter.Workbook("Dashboard4.xlsx");
worksheet = workbook.add_worksheet()


row = 1

title = workbook.add_format({'bold':1, 'bottom':2})
title.set_font_size(14)

visitors = workbook.add_format({'bold':1, 'bottom':2})
visitors.set_align('center')

center = workbook.add_format()
center.set_align("center")

goal_format = workbook.add_format({'bottom':1})
goal_format.set_text_wrap()
goal_format.set_align('center')
goal_format.set_align('vcenter')

variation_title = workbook.add_format()
variation_title.set_align('left')
variation_title.set_align('vcenter')

title_row = workbook.add_format({'bold':1, 'bottom':2})

improvement_row = workbook.add_format({'bold':1, 'bottom':6, 'bg_color': '#d5d5d5', 'num_format': '0.0%'})
rev_per_visitor_improvement_row_format = workbook.add_format({'bold':1, 'bottom':6, 'bg_color': '#d5d5d5', 'num_format': '0.00'})

conversion_rate_format = workbook.add_format({'num_format': '0.0%'})
revenue_visitor_format = workbook.add_format({'num_format': '0.00'})

def maxGoals():
	maximum = 0
	for exp_id in goals:
		if len(goals[exp_id]["goals"].keys()) > maximum:
			maximum = len(goals[exp_id]["goals"].keys()) 
	return maximum

max_goals = maxGoals() + 2 # + 2 gives space. clean up wording later. 

print "Maximum Goals Set"

# for exp_id in exp_descriptions:
for exp_id in ['321795914']:
	print "ADDING: Experiment ID: ", exp_id
	try: 
		visitor_count[exp_id]
	except:
		print "ERROR:", exp_id, var_id
		row += 2
		continue
	worksheet.write(row, 0, exp_descriptions[exp_id]['description'], title) 
	worksheet.write(row, max_goals - 1, "Total Visitors" , visitors)
	worksheet.write(row, max_goals, visitor_count[exp_id]['total_visitors'], visitors)
	worksheet.set_row(row, None, title_row)
	row += 1 
	worksheet.write(row, 0, "Experiment ID: ")
	worksheet.write(row, 1, str(exp_id), center)
	worksheet.write(row, max_goals, "Date - Date")
	row += 2
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
		col -= 1
	## Visitor and Variation Headers
	worksheet.write(row, col, "Visitors" , goal_format) 
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
			if variation_names[var_id] != "Original" and conversions[goal_id]["max"] < float(variation_conversions):
				conversions[goal_id]["max"] += float(variation_conversions)
				conversions[goal_id]["max_var_id"] = var_id
			else:
				conversions[goal_id]["original"] = float(variation_conversions)
				conversions[goal_id]["original_var_id"] = var_id
			worksheet.write(row, col, variation_conversions)
			format = revenue_visitor_format if goals[exp_id]["goals"][goal_id]["name"] == "Total Revenue" else conversion_rate_format
			worksheet.write(row, col + len(goal_ids) + 1, float(variation_conversions) / float(variation_visitors), format) 
			col -=1 
		## Visitor Count	
		worksheet.write(row, col, variation_visitors)
		row, col = row + 1, 0
	## Improvement Row
	worksheet.write(row, col, "Greatest Change from Original")
	col = max_goals
	goal_ids = goals[exp_id]["goals"]
	for goal_id in goal_ids:
		try:
			worksheet.write(row, col, conversions[goal_id]["max"] / conversions[goal_id]["original"] -1)
			original_conv = conversions[goal_id]["original"] / visitor_count[exp_id]['variation'][conversions[goal_id]["original_var_id"]] 
			max_conv = conversions[goal_id]["max"] / visitor_count[exp_id]['variation'][conversions[goal_id]["max_var_id"]] 
			format = rev_per_visitor_improvement_row_format if variation_names[conversions[goal_id]["max_var_id"]] == "Total Revenue" else improvement_row
			worksheet.write(row, col + len(goal_ids) + 1, max_conv - original_conv, format)
		except:
			print "division error"
		col -= 1 
	print "ADD SUCCESSFUL"
	worksheet.set_row(row, None, improvement_row)
	row += 2

worksheet.set_column('A:B', 10)
worksheet.set_column('C:LL', 15) # should make this depend on max goals 
worksheet.hide_gridlines()

workbook.close()

## add visitors 
## add conversions and conversion rate, allow hide and unhide  
## must figure out how to identify the original variation
## sort by visitors or lyft? 
## add archived experiments 
## summary stats: # experiments, avg visitors / exp, number goals reach stat significance 


