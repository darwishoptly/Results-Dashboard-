import requests
from bs4 import BeautifulSoup
from pprint import pprint 
import VariationNames
import NormDist
import ExpDist

def getData(optimizely_sessioin, GAE_Auth_Cookie, account_id):
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
