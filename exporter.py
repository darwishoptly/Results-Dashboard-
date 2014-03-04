import xlsxwriter
import requests
import OptlyData
import datetime


# Provide a list of Experiments where a segment had a different winner that the overall
# Refactor to factor include CTB for highlighting winner
# refactor to include exponential distribution
# clean code and comment
# check set of segments with Ajith 


GAE_Auth_Cookie = "AJKiYcG6oLAqYFRpJj7i9kcQ-NCMxUQcHCSr4DyXdqIF0KiQu13SOCNVfNf_CpX5rmmO2ZJ8HrQmC9Du6gcVYBmvmrBRCz-qDr4QjTQYiO9PRqQmUwukXUZAgNS1vyHTkWzGhFixZjty79aMdMrGLVvs3futE2uR6NqjAeewi-roo3arSlYob8wysV6JEcF--S8KS7CBzEbzwZBCqr8abyyHsVLH-6HfKs6NiQqyL5QkW1ZAWvColZSCtXkhekHTykJAddKN5RAijz51dRyLIptZxibK9osvsIC-V8Lg3ktYlgqzKfa-Y8dF9HWc_Dd8qgEoI6_K_OAk0hj4faH6Vh699museKay0JVzkVHtkhqPrtEPzILHkcDnkyPV7eU4LMYwHEba6mfFeNr1ibnmypL201se2AL4bniufW5J8ZBJ8x9DpLRwBBuiF9ZcPhZDPyKD5wdozV5IGYfRVah9C1lJ9nFWniqrQlnXikqa63wWG0b5iXD94WP7Ei5jIRMxNNiJyCCqO2UVQmiPvwbv-261A3HKTBfQkspOd1ZR_ycY8qWc4UL0tjc8-hervg0rFBxauatTgCxL74S42YI_KmwbaNZs43C02LgEX6mG_cdp_HGjolegwY4BMMBUxwjsw6rEFF3WIy9Gdgwngcusck19x2BePLowQg"
# optimizely_session = "fc7393a777c80660fb925303329039693509f167"

email = "ben.cole@mec.ca"
a_name = "MEC"

account_id = 186764410
project_id = 186764410
name = a_name+"_%s.xlsx" % str(datetime.date.today())


conversion_limit = 50 ## Minimum number of conversions needed in variation and original to be considered 

print "************************** Running %s Dashboard **************************" % a_name 
D = OptlyData.client(GAE_Auth_Cookie, project_id, account_id, {"start": True, "email": email, "months_ago" : 6})

num_experiments = len(D.exp_descriptions.keys())

segment_names = {}
for segment in requests.get("https://www.optimizely.com/api/projects/%s/segments.json?default_segments=true&token=%s" % (str(project_id), D.account_token), cookies=D.cookies).json()["segments"]:
	segment_names[str(segment['id'])] = segment["name"]

segment_value_maps = {} # exp: seg value map
for exp_id in D.exp_descriptions.keys():
	print "segment_value_maps created: exp_id" , exp_id
	segment_value_maps[exp_id] = requests.get("https://api.optimizely.com/v1/segment_values/%s?token=%s" % (str(exp_id), D.token_hash[exp_id]), cookies=D.cookies).json()["segment_value_map"]

#SCHEMA ==> { s_id : {s_val : 0, count : 1 } }
# Create Segment ID, Val Pairs with frequency
segment_id_value_pairs = {}
for exp_id in D.exp_descriptions.keys():
	for s_id in segment_value_maps[exp_id]:
		for s_val in segment_value_maps[exp_id][s_id]:
			if (s_id, s_val) in segment_id_value_pairs:
				segment_id_value_pairs[(s_id, s_val)] += 1 	 
			else: 
				segment_id_value_pairs[(s_id, s_val)] = 1

sorted_seg_pairs = sorted(segment_id_value_pairs.items(), key= lambda x: x[1], reverse=True) 
## Filter out segment pairs that are not in atleast 25% of all experiments.
sorted_seg_pairs = [pair for pair in sorted_seg_pairs if float(pair[1]) / float(num_experiments) > .25]


## Segments
# Ignore Segments that are only applicable to one test
# Consider looking only at segment pairs that are in atleast 30% of experiments (Speeds things up a lot) + have over X number of visitors compared to the full experiment! 
# Ignore experiments with a small number of visitors. 

def removeLowExpVisitors(s, percent): 
	for exp_id in s.exp_descriptions.keys():
		total_visitors = D.visitor_count[exp_id]["total_visitors"]
		if s.visitor_count[exp_id]["total_visitors"] < percent * total_visitors: 
			del s.exp_descriptions[exp_id]
			del s.visitor_count[exp_id]
			del s.goals[exp_id]


S = []
i = 1
# pair = ('167439469'  ,  'unknown')
for pair in sorted_seg_pairs:
	# print D.exp_descriptions
	pair = pair[0] 
	print "PAIR: ", i, " out of" , str(len(sorted_seg_pairs)), pair[0], " : " , pair[1], "........", i
	s = OptlyData.client(GAE_Auth_Cookie, project_id, account_id, { "optimizely_session": D.optimizely_session,
													 				"segment_id" : pair[0],
																	"segment_value": pair[1],
																	"segment_value_maps": segment_value_maps,
																	"token_hash" : D.token_hash,
																	"start" : False,
																	"exp_descriptions": D.exp_descriptions.copy(),
																	"account_token": D.account_token,
																	"D": D
																	})
	s.setExperimentDescriptions(4)
	s.setVisitorCount()
	removeLowExpVisitors(s, .05)
	if len(s.exp_descriptions) == 0:
		continue
	s.makeExperimentsCall() ## sets variation names and original goals	
	## Finish building the hash 
	# {exp_id: "goals" { goal_id :  { "name" : goal_name , variation_id: {"conversions": value, type: "type", "sum_of_squares" : SS_val_if_rev_goal, "conversion_rate" " X, "improvment" : X,  "CTB" : X }}}} 
	s.makeRevenueCall()
	# D.setGoals()
	s.setResultStatistics()
	s.setGoalNames()
	S.append(s)
	i = i + 1



i = 0
imp_goals_positive = []
imp_goals_negative = []
summary_num = 15
num_important = 3
common_goals = D.createGoalCount()
exp_ids = D.exp_descriptions.keys()
while i < len(common_goals):
	goal_id, goal_count = common_goals[i][0], common_goals[i][1]
	goal_ids = [goal_id]
	positive = []
	negative = []
	while i < len(common_goals) - 2 and common_goals[i + 1][1] == goal_count:
		i += 1
		goal_ids.append(common_goals[i][0])
	# print goal_ids
	for g_id in goal_ids:
		# print g_id
		for exp_id in exp_ids:
			if g_id in D.goals[exp_id]['goals']:
				for var_id in D.visitor_count[exp_id]['variation'].keys():
					if exp_id not in D.goals or var_id not in D.variation_names:
						print "skipping for most imp: ", exp_id, g_id, var_id 
						continue
					CTB = D.goals[exp_id]['goals'][g_id][var_id]['CTB']	
					imp = D.goals[exp_id]['goals'][g_id][var_id]['improvement']	
					baseline_id = D.exp_descriptions[exp_id]['baseline_id']
					b_conversions = D.goals[exp_id]['goals'][g_id][baseline_id]['conversions']			
					if imp == "-" or D.goals[exp_id]['goals'][g_id][var_id]['conversions'] < conversion_limit or b_conversions < conversion_limit:
						continue
					elif CTB >= .95:
						# print {"goal_id" : g_id,  "exp_id" : exp_id, "var_id": var_id, "improvement" : imp }
						positive.append({"goal_id" : g_id, "exp_id" : exp_id, "var_id": var_id, "improvement" : imp, "b_conversion_rate" : D.goals[exp_id]['goals'][g_id][baseline_id]['conversion_rate'] })
					elif CTB <= .05:	
						negative.append({"goal_id" : g_id, "exp_id" : exp_id, "var_id": var_id, "improvement" : imp, "b_conversion_rate": D.goals[exp_id]['goals'][g_id][baseline_id]['conversion_rate'] })
	imp_goals_positive += sorted(positive, key= lambda x: x["improvement"], reverse=True)[0:3]
	imp_goals_negative += sorted(negative, key= lambda x: x["improvement"])[0:3]
	i+=1

while len(imp_goals_positive) > summary_num:
	imp_goals_positive.pop()

while len(imp_goals_negative) > summary_num:
	imp_goals_negative.pop()

num_high = 0
num_low = 0		
pos_undecided_goals = 0
h,l, p = [], [], []
for exp_id in D.exp_descriptions:
	plus_low, plus_high, plus_undecided = True, True, True
	for goal_id in D.goals[exp_id]['goals']:
		for var_id in D.visitor_count[exp_id]['variation'].keys():
			if exp_id not in D.goals or var_id not in D.variation_names:
				print "skipping for most imp: ", exp_id, g_id, var_id 
				continue
			imp = D.goals[exp_id]['goals'][goal_id][var_id]['improvement']
			CTB = D.goals[exp_id]['goals'][goal_id][var_id]['CTB']
			baseline_id = D.exp_descriptions[exp_id]['baseline_id']
			b_conversions = D.goals[exp_id]['goals'][goal_id][baseline_id]['conversions']	 
			# print imp, D.goals[exp_id]['goals'][goal_id][var_id]['conversions'] < 50, b_conversions < 50
			if imp == "-" or D.goals[exp_id]['goals'][goal_id][var_id]['conversions'] < conversion_limit or b_conversions < conversion_limit:
				continue
			if imp > .05 and CTB > .95 and plus_high:
				num_high += 1
				plus_high = False
				h.append(exp_id)
			if imp < -.05 and CTB < .05 and plus_low:
				num_low += 1
				print exp_id, goal_id, var_id, D.goals[exp_id]['goals'][goal_id][var_id]['conversions'], b_conversions, imp
				plus_low = False	
				l.append(exp_id)
			if imp > .05 and  plus_undecided and not plus_high:
				plus_undecided = False 
				pos_undecided_goals += 1 
				p.append(exp_id)



def segmentWeight(s):
	seg_visits = 0
	total_visits = 0	
	for exp_id in s.exp_descriptions.keys():
		seg_visits += s.visitor_count[exp_id]["total_visitors"]  
		total_visits += D.visitor_count[exp_id]["total_visitors"]
	return float(seg_visits) / total_visits



# [s for s in S if s.segment_id == '285473938' and s.segment_value == 'true'][0].goals['383680670']['goals']['330456990']

deviant_segments = []
for s in S: 
	for exp_id in s.goals.keys():
		for goal_id in s.goals[exp_id]["goals"].keys():
			for var_id in s.goals[exp_id]["goals"][goal_id].keys():					
				if var_id not in D.variation_names or var_id == 'name' or goal_id not in s.goals[exp_id]["goals"] or s.goals[exp_id]["goals"][goal_id][var_id]["improvement"] == "-":
					continue
				else: 
					seg = s.goals[exp_id]["goals"][goal_id][var_id]["improvement"]
					original = D.goals[exp_id]["goals"][goal_id][var_id]["improvement"]
					difference = seg - original 
					conversions = s.goals[exp_id]["goals"][goal_id][var_id]["conversions"]
					baseline_conversions = s.goals[exp_id]["goals"][goal_id][s.exp_descriptions[exp_id]['baseline_id']]["conversions"]
					if abs(difference) > .1 and conversions > 250 and baseline_conversions > 250: 
						deviant_segments.append((s.segment_id, s.segment_value, goal_id, exp_id, var_id, float("{0:.2f}".format(difference)), segmentWeight(s) ))
						print(exp_id, conversions, baseline_conversions)

deviant_segments = sorted(deviant_segments, key= lambda k: k[5], reverse=True)


count_deviant_segments = {}
for s in deviant_segments:
	if (s[0], s[1]) in count_deviant_segments:
		if s[3] not in count_deviant_segments[(s[0], s[1])]["exp_ids"]:
			count_deviant_segments[(s[0], s[1])]["count"] += 1
			count_deviant_segments[(s[0], s[1])]["exp_ids"].append(s[3])
	else:
		count_deviant_segments[(s[0], s[1])] = { "count" : 1, "exp_ids" : [s[3]], "weight": s[6]}

for s in count_deviant_segments:
	i, v = s[0], s[1]
	count_deviant_segments[(i, v)]["weighted_count"] = float(count_deviant_segments[(i, v)]["count"]) *  count_deviant_segments[(i, v)]["weight"]
	

t = sorted(count_deviant_segments.items(), key = lambda x: x[1]["count"], reverse=True)
t2 = sorted(count_deviant_segments.items(), key = lambda x: x[1]["weight"], reverse=True)
t3 = sorted(count_deviant_segments.items(), key = lambda x: x[1]["weighted_count"], reverse=True)


# Provide a list of Experiments where a segment had a different winner that the overall

def getWinningVariation(results_object, exp_id, goal_id):
	winning_variation = None
	for var_id in results_object.goals[exp_id]["goals"][goal_id].keys():			
		if var_id not in D.variation_names or var_id == 'name' or var_id not in results_object.goals[exp_id]["goals"][goal_id] or 'improvement' not in results_object.goals[exp_id]["goals"][goal_id][var_id] or results_object.goals[exp_id]["goals"][goal_id][var_id]["improvement"] == "-":
			continue
		else: 
			# print exp_id, goal_id, var_id, winning_variation	
			if winning_variation == None or results_object.goals[exp_id]["goals"][goal_id][var_id]["improvement"] > results_object.goals[exp_id]["goals"][goal_id][winning_variation]["improvement"]:
				winning_variation = var_id				
	if winning_variation and results_object.goals[exp_id]["goals"][goal_id][winning_variation]["CTB"] is not "-" and results_object.goals[exp_id]["goals"][goal_id][winning_variation]["CTB"] >= .95:		
		return winning_variation	
	else:
		return None

					
alternate_wins = []
for exp_id in D.goals.keys():
	for goal_id in D.goals[exp_id]["goals"].keys():
		for segment_id in segment_value_maps[exp_id]:
			segment_winner = None
			overall_winner = getWinningVariation(D, exp_id, goal_id) or D.exp_descriptions[exp_id]['baseline_id']
			for segment_value in segment_value_maps[exp_id][segment_id]:
				s = [s for s in S if s.segment_id == segment_id and s.segment_value == segment_value]
				if s == []:
					print "skipping", segment_id, segment_value
					continue
				else:
					
					s = s[0]					
					if exp_id not in s.goals or goal_id not in s.goals[exp_id]['goals']:
						continue					
					# if goal_id not in map(lambda x: x[0], common_goals[0:5]):
						# continue
					print "a"
					segment_value_winner = getWinningVariation(s, exp_id, goal_id)
					
					if segment_value_winner is None:
						continue
					elif (segment_winner is None and segment_value_winner):
						segment_winner = segment_value_winner
						win_s = s
					else: 
						val_imp = s.goals[exp_id]["goals"][goal_id][segment_value_winner]["improvement"]
						win_imp = s.goals[exp_id]["goals"][goal_id][segment_winner]["improvement"]
						if val_imp > win_imp or win_imp == "-":
							segment_winner = segment_value_winner
							win_s = s
				print "here: ", segment_id, segment_value, segment_winner, overall_winner
			if segment_winner is None or segment_winner == overall_winner:
				continue
			elif win_s.goals[exp_id]["goals"][goal_id][segment_winner]["improvement"] > D.goals[exp_id]["goals"][goal_id][overall_winner]["improvement"]: 
				lost_improvement = (win_s.goals[exp_id]["goals"][goal_id][segment_winner]["conversion_rate"] - win_s.goals[exp_id]["goals"][goal_id][overall_winner]["conversion_rate"]) * win_s.visitor_count[exp_id]['total_visitors'] / float(D.visitor_count[exp_id]['total_visitors']) / D.goals[exp_id]["goals"][goal_id][D.exp_descriptions[exp_id]['baseline_id']]["conversion_rate"]
				lost_improvement = lost_improvement / 100 if "Revenue" in D.goal_names == 'revenue_goal' else lost_improvement
				segment_improvement = win_s.goals[exp_id]["goals"][goal_id][segment_winner]["improvement"]
				overall_improvement = win_s.goals[exp_id]["goals"][goal_id][overall_winner]["improvement"]
				original_conversion_rate = D.goals[exp_id]["goals"][goal_id][D.exp_descriptions[exp_id]['baseline_id']]["conversion_rate"]
				difference_in_improvement = segment_improvement - overall_improvement
				alternate_wins.append((exp_id, D.goal_names[goal_id], segment_names[segment_id] if segment_id in segment_names else segment_id, segment_value, D.variation_names[overall_winner], D.variation_names[segment_winner], original_conversion_rate, overall_improvement, segment_improvement, difference_in_improvement, lost_improvement))
				# record max improvement variation 

alternate_wins = sorted(alternate_wins, key = lambda x: x[10], reverse=True)


# [(i[0][0], i[0][1]) for i in t3]

# highlight where goal is a "top 5 " goal
# [ e for e in D.exp_descriptions if datetime.datetime.strptime(D.exp_descriptions[e]['last_modified'][0:-1] , "%Y-%m-%dT%H:%M:%S") > datetime.datetime(2014,1,1,1,1,1)]

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

min_visits = 1000
goals_with_min_visits = sum([1 for exp in D.visitor_count if D.visitor_count[exp]['total_visitors'] > 1000])
avg_goals_exp = float(sum([len(D.goals[exp_id]['goals']) for exp_id in D.exp_descriptions if D.visitor_count[exp_id]['total_visitors'] > 1000])) / goals_with_min_visits

workbook = xlsxwriter.Workbook("output/" + name);
summary_sheet = workbook.add_worksheet("Summary")
segment_sheet = workbook.add_worksheet("Segments")
alt_segment_sheet = workbook.add_worksheet("Missed Segments")
worksheet = workbook.add_worksheet("Experiments Report - Detailed")
dump = workbook.add_worksheet("Dump")

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
    "fill_grey": {'bg_color': '#D9D9D9'},
	"strong_bold": {"bold": "true"},
	"bottom_heavy": {"bottom": 5},
	"top" : {"top": 1},
	"v_middle" : {"valign": "vcenter"},
	"": {"font_name": "Gill Sans Light"}
    }

def combinedFormat(list_formats): # ["percent", "fill_green"]
    combined_format = {}
    for f in list_formats: combined_format.update(formats[f])
    return combined_format

def getGoalFormats(goal_name, CTB):
    if CTB > .95 and CTB != "-": 
        percentage = workbook.add_format(combinedFormat(["percent", "fill_green", "font"]))
        decimal = workbook.add_format(combinedFormat(["decimal", "fill_green", "font"]))
    elif CTB < .05 and CTB != "-":
        percentage = workbook.add_format(combinedFormat(["percent", "fill_red", "font"]))
        decimal = workbook.add_format(combinedFormat(["decimal", "fill_red", "font"])) 
    else:
        percentage = workbook.add_format(combinedFormat(["percent", "font"]))
        decimal = workbook.add_format(combinedFormat(["decimal", "font"])) 
    if goal_name == "Total Revenue":
        return [decimal, decimal, percentage, percentage]
    else:
        return [decimal, percentage, percentage, percentage]

row, col = 1, 1
segment_sheet.set_column(0, 0, 1)
segment_sheet.set_column(1, 11, 18)
segment_sheet.set_column(4, 6, 25)
segment_sheet.set_column(7, 11, 13)
segment_sheet.hide_gridlines(2)
segment_sheet.set_zoom(90)

empty = ["" for i in range(10)]
f = workbook.add_format(combinedFormat(["font_bold", "strong_bold", "bottom_heavy"]))
f_mats = [f for i in range(11)]
writeRange(segment_sheet, row, col, [a_name.upper() + " SEGMENT DISCOVERY"] + empty, False, f_mats)
f = workbook.add_format(combinedFormat(["font_bold", "bottom"]))
f_mats = [f for i in range(12)]
headers = ["Experiment ID",
		   "Segment Name",	
		   "Segment Value",	
		   "Experiment Name",
		   	"Variation Name",	
			"Goal Name",
			"Exp Visitors",	
			"Segment Visitors",	
			"Org. Improvement",	
			"+/- Improvement",	
			"Segment Weight"]
row += 2
writeRange(segment_sheet, row, col, headers, False, f_mats)
row+=1
for d in deviant_segments:
	exp_id, var_id, goal_id = d[3], d[4], d[2]
	segment = [s for s in S if s.segment_id == d[0] and s.segment_value == d[1]][0]  
	values = [
		exp_id,
		segment_names[d[0]] if d[0] in segment_names else d[0] ,
		d[1],
		D.exp_descriptions[d[3]]['description'],
		D.variation_names[var_id],
		D.goal_names[goal_id],
		D.visitor_count[exp_id]["variation"][var_id],
		segment.visitor_count[exp_id]["variation"][var_id],
		D.goals[exp_id]["goals"][goal_id][var_id]["improvement"],
		d[5],
		count_deviant_segments[(segment.segment_id, segment.segment_value)]["weighted_count"] 
	]
	imp = "fill_green" if goal_id in imp_goals_positive else "" # short for importance
	tex = workbook.add_format(combinedFormat(["font", "v_middle", imp]))
	tex_c = workbook.add_format(combinedFormat(["font", "v_middle", "center", imp]))
	per = workbook.add_format(combinedFormat(["font", "v_middle", "percent", "center", imp]))
	dec = workbook.add_format(combinedFormat(["font", "v_middle", "decimal", "center", imp]))
	f_mats = [tex,tex, tex, tex, tex, tex, tex_c, dec, per, dec, dec ]
	writeRange(segment_sheet, row, col, values, False, f_mats)
	row += 1

segment_sheet.autofilter( 3, 1 , len(deviant_segments) + 3, 11)




# 	ALT SEGMENT SHEET


row, col = 1, 1
alt_segment_sheet.set_column(0, 0, 1)
alt_segment_sheet.set_column(1, 11, 18)
alt_segment_sheet.set_column(4, 6, 25)
alt_segment_sheet.set_column(7, 11, 13)
alt_segment_sheet.hide_gridlines(2)
alt_segment_sheet.set_zoom(90)

empty = ["" for i in range(10)]
f = workbook.add_format(combinedFormat(["font_bold", "strong_bold", "bottom_heavy"]))
f_mats = [f for i in range(11)]
writeRange(alt_segment_sheet, row, col, [a_name.upper() + " SEGMENT DISCOVERY"] + empty, False, f_mats)
f = workbook.add_format(combinedFormat(["font_bold", "bottom"]))
f_mats = [f for i in range(12)]
headers = ["Experiment ID",
		   "Goal Name",	
		   "Segment Name",	
		   "Segment Value",
		   	"Overall Variation Winner",	
			"Segment Variation Winner",
			"Original Conversion Rate",	
			"Overall Improvement",	
			"Segment Improvement",	
			"+/- Improvement",	
			"Lost Improvement"]
row += 2
writeRange(alt_segment_sheet, row, col, headers, False, f_mats)
row+=1
for a in alternate_wins:
	values = a
	imp = "fill_green" if goal_id in imp_goals_positive else "" # short for importance
	tex = workbook.add_format(combinedFormat(["font", "v_middle", imp]))
	tex_c = workbook.add_format(combinedFormat(["font", "v_middle", "center", imp]))
	per = workbook.add_format(combinedFormat(["font", "v_middle", "percent", "center", imp]))
	dec = workbook.add_format(combinedFormat(["font", "v_middle", "decimal", "center", imp]))
	f_mats = [tex,tex, tex, tex, tex, tex, per, per, per, per, per]
	writeRange(alt_segment_sheet, row, col, values, False, f_mats)
	row += 1

alt_segment_sheet.autofilter( 3, 1 , len(deviant_segments) + 3, 11)


# alt segment sheet end 







row, col = 1, 1  
summary_sheet.set_column(0, 0, 1)
summary_sheet.set_column(1, 5, 18)
summary_sheet.set_column(6, 6, 1)
summary_sheet.set_column(7, 11, 18)
summary_sheet.set_column(12, 12, 1)
summary_sheet.set_column(13, 17, 18) 
summary_sheet.hide_gridlines(2)
summary_sheet.set_zoom(90)
   
#Main Header and High Level Stats 
empty = ["" for i in range(13)]
f = workbook.add_format(combinedFormat(["font_bold", "strong_bold", "bottom_heavy"]))
f_mats = [f for i in range(14)]
writeRange(summary_sheet, row, col, [a_name.upper() + " EXECUTIVE DASHBOARD"] + empty, False, f_mats)
f = workbook.add_format(combinedFormat(["font"]))
num = workbook.add_format(combinedFormat(["decimal", "font"]))
row, col = 2, 1
writeRange(summary_sheet, row, col, ["Date Run", "", "", str(datetime.date.today())], False, [f,f,f,f])
row, col = row + 1, 1
writeRange(summary_sheet, row, col, ["Criteria", "", "", "Modified in Last 60 days"], False, [f,f,f,f])
row, col = row + 2, 1
f = workbook.add_format(combinedFormat(["font"]))
num = workbook.add_format(combinedFormat(["decimal", "font"]))
stats = [("# Experiments Run w/ >%s visitors" % min_visits , goals_with_min_visits), ("Avg. Goals / Experiment", avg_goals_exp), ("# Experiments with Stat. Significant Winner", num_high), ("# Experiments with Stat. Significant Loser", num_low), ("# Experiments with no Winner but CVR Improvement > 5%: ", pos_undecided_goals) ]
for s in stats:
	writeRange(summary_sheet, row, col, [s[0], "", "", s[1]], False, [f,f,f,num])
	row, col = row + 1, 1

row += 1
#Set Headers for Stats 

num_head = 4

summary_sheet.merge_range(row, col, row, 11, "EXPERIMENT SUMMARY STATISTICS", workbook.add_format(combinedFormat(["font_bold", "bottom", "top", "center"])))
col += 11 + 1
summary_sheet.merge_range(row, col, row, col+4, "SEGMENT SUMMARY STATISTICS", workbook.add_format(combinedFormat(["font_bold", "bottom", "top", "center"])))
row, col = row + 1, 1
summary_sheet.merge_range(row, col, row, col+4, "High Improvement Variations for Frequent Goals:", workbook.add_format(combinedFormat(["font_bold", "fill_green", "center"])))
col += 6
summary_sheet.merge_range(row, col, row, col+4, "Low Improvement Variations for Frequent Goals:", workbook.add_format(combinedFormat(["font_bold", "fill_red", "center"])))
col += 6
summary_sheet.merge_range(row, col, row, col+4, "Segment Value Pairs w/ >10% deviation :", workbook.add_format(combinedFormat(["font_bold", "fill_grey", "center"])))
row, col = row + 1, 1
f = workbook.add_format(combinedFormat(["font", "bottom", "center"]))
for i in range(2):
	writeRange(summary_sheet, row, col, ["Experiment Name", " Variation", "Base CNV Rate","Improvement" , "Goal Name"], False, [f,f,f,f,f])
	col+=6

writeRange(summary_sheet, row, col, ["Segment Name", "Segment Value", "# Expmts with deviation", "Avg % Total Visitors" , "Score"], False, [f,f,f,f,f])

row, col= row + 1, 1 
data_start_row = row 
for important_set in [imp_goals_positive, imp_goals_negative]:
	for goal in important_set:
		f = workbook.add_format(combinedFormat(["font", "wrap", "v_middle"]))
		percent = workbook.add_format(combinedFormat(["percent", "font", "center", "v_middle"]))
		n_format = workbook.add_format(combinedFormat(["decimal", "font", "center", "v_middle"])) if "Revenue" in D.goal_names[goal["goal_id"]] else percent
		values = [D.exp_descriptions[goal["exp_id"]]["description"], D.variation_names[goal["var_id"]], goal["b_conversion_rate"], goal["improvement"], D.goal_names[goal["goal_id"]]]
		writeRange(summary_sheet, row, col, values, False, [f, f, n_format, percent, f])
		row += 1
	row, col = data_start_row, col + 6

# important_segments = sorted(count_deviant_segments.items(), key = lambda x: x[1], reverse=True)
for s in t3[0:15]: # TODO change name 
	f = workbook.add_format(combinedFormat(["font", "wrap", "v_middle"]))
	n = workbook.add_format(combinedFormat(["font", "wrap", "center", "v_middle"]))
	p = workbook.add_format(combinedFormat(["font", "wrap", "center", "v_middle", "percent"]))
	d = workbook.add_format(combinedFormat(["font", "wrap", "center", "v_middle", "decimal"]))
	values = [segment_names[s[0][0]], s[0][1], s[1]["count"], s[1]["weight"], s[1]["weighted_count"] ]
	writeRange(summary_sheet, row, col, values, False, [f, f, n, d, d])
	row += 1









# percentage = workbook.add_format({'num_format': '0.0%'})
# two_digit_decimal = workbook.add_format({'num_format': '0.00'})
row, col = 0 , 0 

goal_count = D.createGoalCount()
D.setGoalNames()
goal_names = D.goal_names

## Set up Headers 
headers = ["Variation Name", "Visitors"]
f = workbook.add_format(combinedFormat(["font_bold", "fill_grey"]))
writeRange(worksheet, row, col, headers, True, [f,f])
addSpaceColumn(worksheet, col)
worksheet.set_column(0, 0, 30)
worksheet.set_column(1, 1, 12)
## Set up Goal Headers
fields = ["Conversions", "CNV Rate", "Improvement", "CTB"]
for i in range(0, D.maxGoals()): 
    col_old = col
    center = workbook.add_format(combinedFormat(["center", "font_bold", "fill_grey"]))
    writeRange(worksheet, row, col, fields, True, [center, center, center, center])
    worksheet.set_column(col_old, col, 12)
    addSpaceColumn(worksheet, col)

row += 2
col = 0

expIDSortedbyVisitorCount = sorted(D.visitor_count, key=lambda x: D.visitor_count[x]['total_visitors'], reverse=True)

for exp_id in expIDSortedbyVisitorCount:
# exp_id = '523462609'
	print "ADDING: Experiment ID: ", exp_id
	try: 
		D.visitor_count[exp_id]
	except:
		print ("ERROR:", exp_id, var_id)
		continue
	font = workbook.add_format(formats["font"])
	font_bold = workbook.add_format(combinedFormat(["font_bold", "wrap"]))
	worksheet.write(row, 0, D.exp_descriptions[exp_id]['description'] + " (" + str(exp_id) + ")", font_bold) 
	col+=2
	goal_ids = D.goals[exp_id]["goals"].keys()
	setGoalHeaders(worksheet, row, col, goal_ids)   
	row += 1
	# sort variations with baseline first 
	var_ids  = D.visitor_count[exp_id]['variation'].keys()
	baseline_variation_id = filter(lambda var_id: var_id == D.exp_descriptions[exp_id]["baseline_id"] , var_ids)    
	baseline_variation_id = baseline_variation_id[0] if len(baseline_variation_id) > 0 else var_ids[0]
	var_ids.remove(baseline_variation_id)
	var_ids.insert(0, baseline_variation_id)
	# Add Variation Names 
	for var_id in var_ids:
		col = 0
		if var_id not in D.variation_names:
			print "..........VARIATION DELETED........ ", var_id
			continue
		writeRange(worksheet, row, col, [D.variation_names[var_id], D.visitor_count[exp_id]['variation'][var_id]], True, [font, font])
		for goal in goal_count:            
			goal_id = goal[0]
			if goal_id in goal_ids:
				addSpaceColumn(worksheet, col)
				g = D.goals[exp_id]["goals"][goal_id][var_id]
				(conversions, conversion_rate, improvement, CTB) = g["conversions"], g["conversion_rate"], g["improvement"], g["CTB"] 
				goal_formats = getGoalFormats(D.goals[exp_id]["goals"][goal_id]["name"], CTB)
				writeRange(worksheet, row, col, [conversions, conversion_rate, improvement, CTB], True, goal_formats) 
		row += 1
	row += 1
	col = 0

top_row = workbook.add_format(combinedFormat(["font_bold", "fill_grey"]))
worksheet.set_row(0, None, top_row)
worksheet.set_zoom(75)
worksheet.freeze_panes(1,2)
worksheet.hide_gridlines(2)

row, col = 0, 0 
f = workbook.add_format(combinedFormat(["font_bold", "fill_grey", "center"]))
headers = ["Experiment ID", 
		   "Variation ID", 
		   "Experiment Name", 
		   "Variation Name",
		   "Visitors", 
		   "Conversions", 
		   "Conversion Rate", 
		   "Improvement", 
		   "CTB",
		   "Segment Name",
		   "Segment Value"]
f_mats = [f for h in headers]
writeRange(dump, row, col, headers, False, f_mats) 
row += 1

arr = [D] + S
skipped = [] 
for results_object in arr:
	print results_object.segment_id, results_object.segment_value
	for exp_id in results_object.exp_descriptions.keys():
		for goal_id in results_object.goals[exp_id]['goals']:
			for var_id in results_object.visitor_count[exp_id]['variation'].keys():
				if exp_id not in results_object.goals or var_id not in results_object.variation_names:
					skipped.append((exp_id, g_id, var_id))
					continue
				if results_object.segment_id == '': 
					seg_name = "Original"
				elif results_object.segment_id not in segment_names:
					seg_name = "Deleted"
				else:
					seg_name = segment_names[results_object.segment_id]
				r = [exp_id,
					var_id,
					results_object.exp_descriptions[exp_id]["description"],
					results_object.variation_names[var_id],
					results_object.visitor_count[exp_id]['variation'][var_id],
					results_object.goals[exp_id]['goals'][goal_id][var_id]["conversions"],
					results_object.goals[exp_id]['goals'][goal_id][var_id]["conversion_rate"],
					results_object.goals[exp_id]['goals'][goal_id][var_id]["improvement"],
					results_object.goals[exp_id]['goals'][goal_id][var_id]["CTB"],
					seg_name,
					results_object.segment_value]
				text = workbook.add_format(combinedFormat(["font"]))
				num = workbook.add_format(combinedFormat(["decimal", "font"]))
				percent = workbook.add_format(combinedFormat(["percent", "font"]))
				f_mats = [num,
						num,
						text,
						text,
						num,
						num,
						percent,
						percent,
						percent,
						text,
						text]
				writeRange(dump, row, col, r, False, f_mats)
				row+=1

print "Skipped Experiment IDs for Dump ( e_id, g_id, v_id) ", skipped

dump.hide_gridlines(2)
dump.set_column(0, len(f_mats)-1, 14)
dump.autofilter(0, 1 , row, len(f_mats)-1)
workbook.close()


