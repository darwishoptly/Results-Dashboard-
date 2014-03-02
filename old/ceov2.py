import xlsxwriter
import requests
from bs4 import BeautifulSoup
from pprint import pprint 
import NormDist
import ExpDist
# r = requests.get("https://www.optimizely.com/edit?experiment_id=401420652", cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie})

GAE_Auth_Cookie = "AJKiYcGlT-a7VKyCc_ENLr2YY6uAhHscwTVHYPrP4Q53bsBb5XtJ0kqLiIihdQassrfOFl_tvXq_M-o49NpeT0msCRcsdvUuvghoqkStjrpczX52LGGM8d9_LweX9VEk5A8ZlDhNU1ydZIfWmWlvV1F8K-0ejDv_eUGMqiOijn-oTOG4XGPW-wqcEUnssjrkbpK5lIi5Hc7DxED46j6L3j3gIjRoV3Vg_GEtYkYeAxL3HpxyEe38lSu27zoRBA46WGxUoyPUsCn3oVTqVRGCPSfBKoVXfmyJ87qT2DYfoLWFEBXOgK8MQarQExF5Eu4fe_vpT5zDg4uoeKfbr9WTBqJhKD-3ty8Ry81mVCIpzltA4RGebDaIqwhoaXqCofHTcob7t36rE0_0h6hy93bAnOtB-6iXCnvnx6FSiFqC5uTPe0ZPiLKt4o3i_TKLyglPaKTvAk4CauppUvXbewqQn3w5Ci4Mz-cuPnNqWk8tBjxRciEnQsNu5nyFSeTqTqGcfsRFV4KqauaQKlHRb7UsE22RuM2SL5wzN81wJmHsoEXmsCDjgLWa1gJL8G9eIfcwAqM-duK6jn2m2zQSyuWny31x3oVxsQrzv0FuSevqsH5orfEZBlxs4TzR3GsteF8fK465WBm_95RY1YCfacQKOKFX-S3ohLgf8A"
optimizely_session = "ffd31f6a89777361d5cef194e9f7453f9e75efc4"
# email = "optimizely@healthydirections.com"
project_id = 119665466
account_id = 119665466
name = "ResultsExport.xlsx"

# r = requests.get("https://www.optimizely.com/admin/impersonate?email=%s" % email, cookies={"SACSID" : GAE_Auth_Cookie}) 
# optimizely_session = optimizely_session or r.cookies['optimizely_session']


## SACSID Cookie after impersonation

account_token_request = requests.get("https://www.optimizely.com/admin/account_token?account_id=%s" % str(project_id), cookies={"optimizely_session": optimizely_session, "SACSID" : GAE_Auth_Cookie}) 
account_token = account_token_request.json()["token"]

if account_token == None or "Forbidden" in account_token.text:
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
	exp_descriptions[exp_id]["start"] = req_goals.json()["earliest"]
	exp_descriptions[exp_id]["end"] = req_goals.json()["latest"]	
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

def maxGoals():
	maximum = 0
	for exp_id in goals:
		if len(goals[exp_id]["goals"].keys()) > maximum:
			maximum = len(goals[exp_id]["goals"].keys()) 
	return maximum

max_goals = maxGoals() + 5 # +  4 for headers, 1 for visitors gives space. clean up wording later. 

print "Maximum Goals Set"

def createGoalCount():
    goal_count = {}
    for exp_id in goals:
        goal_ids = goals[exp_id]['goals'].keys()
        for goal_id in goal_ids:
            if goal_id in goal_count:
                goal_count[goal_id] += 1
            else:
                goal_count[goal_id] = 1
    return sorted(goal_count.items(), key=lambda x: x[1],reverse=True)

def getGoalNames():
    goal_names = {}
    for exp_id in goals:
        goal_ids = goals[exp_id]['goals'].keys()	
        for goal_id in goal_ids:
            if goal_id not in goal_names:
                goal_names[goal_id] = goals[exp_id]['goals'][goal_id]["name"]
    return goal_names

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

conversions = {}

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

def addSpaceColumn(worksheet, column):
    worksheet.set_column(column, column, 2)
    global col
    col += 1
    return 

def setGoalHeaders(worksheet, row, column, goals):
    global col
    col = column
    for goal in goal_count:            
        goal_id = goal[0]
        if goal_id in goals:
            # merge the length of number of goal fields - 1
            addSpaceColumn(worksheet, col)
            f = combinedFormat(["center", "bottom", "font"])
            worksheet.merge_range(row, col, row, col + 4 - 1, goal_names[goal_id], workbook.add_format(f))
            col+=4
    return 

def getGoalConversions(exp_id, var_id, goal_id):
	visitors = visitor_count[exp_id]['variation'][var_id]
	conversions = goals[exp_id]["goals"][goal_id][var_id]["conversions"]
	if visitors > 0:
		conversion_rate = float(conversions) / float(visitors)
	else:
		conversion_rate = "-"
	return (conversions, conversion_rate)

def getGoalValues(exp_id, var_id, goal_id, baseline_variation_id):
    conversions, conversion_rate = getGoalConversions(exp_id, var_id, goal_id)
    if var_id == baseline_variation_id:
        return (conversions, conversion_rate, "-", "-")
    else:
        conversions, conversion_rate = getGoalConversions(exp_id, var_id, goal_id)
        b_conversions, b_conversion_rate = getGoalConversions(exp_id, baseline_variation_id, goal_id)
        improvement = "-" if (b_conversion_rate == 0 or conversion_rate == "-" or b_conversion_rate == "-") else (float(conversion_rate) / float(b_conversion_rate)) - 1
        CTB = CTBNormal(exp_id, var_id, goal_id)
        return (conversions, conversion_rate, improvement, CTB)
        

workbook = xlsxwriter.Workbook(name);
worksheet = workbook.add_worksheet()


formats = {
    "percent" : {'num_format': '0.0%'}, 
    "decimal" : {'num_format': '0.00'}, 
    'fill_green': {'bg_color': '#E7EFD8'},
    "fill_red" : {"bg_color" : '#F2DCDB'},
    "center": {'align': 'center'},
    "bottom": {'bottom':1},
    "font": {"font_name": "Gill Sans Light"},
    "font_bold": {"font_name": "Gill Sans"},
    "wrap": {"text_wrap": "True"},
    "fill_grey": {'bg_color': '#D9D9D9'}
    }

def combinedFormat(list_formats): # ["percent", "fill_green"]
    combined_format = {}
    for f in list_formats: combined_format.update(formats[f])
    return combined_format

def getGoalFormats(goal_name, improvement):
    if improvement > .05 and improvement != "-": 
        percentage = workbook.add_format(combinedFormat(["percent", "fill_green", "font"]))
        decimal = workbook.add_format(combinedFormat(["decimal", "fill_green", "font"]))
    elif improvement < -.05 and improvement != "-":
        percentage = workbook.add_format(combinedFormat(["percent", "fill_red", "font"]))
        decimal = workbook.add_format(combinedFormat(["decimal", "fill_red", "font"])) 
    else:
        percentage = workbook.add_format(combinedFormat(["percent", "font"]))
        decimal = workbook.add_format(combinedFormat(["decimal", "font"])) 
    if goal_name == "Total Revenue":
        return [decimal, decimal, percentage, percentage]
    else:
        return [decimal, percentage, percentage, percentage]

# percentage = workbook.add_format({'num_format': '0.0%'})
# two_digit_decimal = workbook.add_format({'num_format': '0.00'})

row, col = 0 , 0 

goal_count = createGoalCount()
goal_names = getGoalNames()

## Set up Headers 
headers = ["Variation Name", "Visitors"]
f = workbook.add_format(combinedFormat(["font_bold", "fill_grey"]))
writeRange(worksheet, row, col, headers, True, [f,f])
addSpaceColumn(worksheet, col)
worksheet.set_column(0, 0, 30)
worksheet.set_column(1, 1, 12)
## Set up Goal Headers
fields = ["Conversions", "CNV Rate", "Improvement", "CTB"]
for i in range(0, maxGoals()): 
    col_old = col
    center = workbook.add_format(combinedFormat(["center", "font_bold", "fill_grey"]))
    writeRange(worksheet, row, col, fields, True, [center, center, center, center])
    worksheet.set_column(col_old, col, 12)
    addSpaceColumn(worksheet, col)

row += 2
col = 0

expIDSortedbyVisitorCount = sorted(visitor_count, key=lambda x: visitor_count[x]['total_visitors'], reverse=True)

for exp_id in expIDSortedbyVisitorCount:
# exp_id = '523462609'
    print "ADDING: Experiment ID: ", exp_id
    try: 
    	visitor_count[exp_id]
    except:
    	print ("ERROR:", exp_id, var_id)
        continue
    font = workbook.add_format(formats["font"])
    font_bold = workbook.add_format(combinedFormat(["font_bold", "wrap"]))
    worksheet.write(row, 0, exp_descriptions[exp_id]['description'] + " (" + str(exp_id) + ")", font_bold) 
    col+=2
    goal_ids = goals[exp_id]["goals"].keys()
    setGoalHeaders(worksheet, row, col, goal_ids)   
    row += 1
    # sort variations with baseline first 
    var_ids  = visitor_count[exp_id]['variation'].keys()
    baseline_variation_id = filter(lambda var_id: var_id == exp_descriptions[exp_id]["baseline_id"] , var_ids)    
    baseline_variation_id = baseline_variation_id[0] if len(baseline_variation_id) > 0 else var_ids[0]
    var_ids.remove(baseline_variation_id)
    var_ids.insert(0, baseline_variation_id)
    # Add Variation Names 
    for var_id in var_ids:
        col = 0
        if var_id not in variation_names:
            print "..........VARIATION DELETED........ ", var_id
            continue
        writeRange(worksheet, row, col, [variation_names[var_id], visitor_count[exp_id]['variation'][var_id]], True, [font, font])
        for goal in goal_count:            
            goal_id = goal[0]
            if goal_id in goal_ids:
                addSpaceColumn(worksheet, col)
                (conversions, conversion_rate, improvement, CTB) = getGoalValues(exp_id, var_id, goal_id, baseline_variation_id)
                goal_formats = getGoalFormats(goals[exp_id]["goals"][goal_id]["name"], improvement)
                writeRange(worksheet, row, col, [conversions, conversion_rate, improvement, CTB], True, goal_formats) 
        row += 1
    row += 1
    col = 0

top_row = workbook.add_format(combinedFormat(["font_bold", "fill_grey"]))
worksheet.set_row(0, None, top_row)
worksheet.set_zoom(75)
worksheet.freeze_panes(1,2)
worksheet.hide_gridlines(2)
workbook.close()
