def countExp(r, exp_id, und_imp_criteria=0):
	winning_experiment_count = 0 # experiments with a winning variation 
	winning_goal_count = 0 # goals that have a winning variation
	losing_experiment_count = 0 # experiments with a losing variation 
	losing_goal_count = 0 # goals that are losing
	pos_undecided_experiment_count = 0
	neg_undecided_experiment_count = 0
	
	experiment_winner_counted, experiment_loser_counted = False, False
	pos_undecided_goals, neg_undecided_goals = 0, 0
	for goal_id in r.goals[exp_id]['goals']:
		if r.goal_names[goal_id] == "Engagement":
			continue
		print "...Counting Experiment: goal", r.goal_names[goal_id]  
		goal_winner_declared, goal_loser_declared, goal_undecided = False, False, False
		winning_variations, losing_variations = 0, 0
		for var_id in r.visitor_count[exp_id]['variation'].keys():
			if var_id not in r.variation_names:
				print ".......SKIPPING variation_id:", var_id  
				continue
			print ".......variation_id:", r.variation_names[var_id]  
			if exp_id not in r.goals or var_id not in r.variation_names:
				skipped.append((exp_id, g_id, var_id))
				continue
			else: 
				imp , CTB = r.goals[exp_id]["goals"][goal_id][var_id]['improvement'], r.goals[exp_id]["goals"][goal_id][var_id]['CTB']
				print "..............imp, CTB", imp, CTB
				if imp == "-" or CTB == "-":
					continue
				elif CTB > .95:
					print imp, CTB
					winning_variations += 1 
				elif CTB < .05: 
					losing_variations += 1
				elif imp > und_imp_criteria:
					pos_undecided_goals += 1
				elif imp < und_imp_criteria * -1:
					neg_undecided_goals += 1
		print ".............. (winning_experiment_count, winning_goal_count, losing_experiment_count, losing_goal_count, pos_undecided_experiment_count, neg_undecided_experiment_count)", (winning_experiment_count, winning_goal_count, losing_experiment_count, losing_goal_count, pos_undecided_experiment_count, neg_undecided_experiment_count)
		if winning_variations > 0: 
			# Winner has been declared for a goal
			print "..............Adding winner"
			if not experiment_winner_counted:
				winning_experiment_count += 1
			# _increment(winning_experiment_count, (r.account_id, latest.year, latest.month), 1, not experiment_winner_counted)
			experiment_winner_counted = True
			if not goal_winner_declared:
				winning_goal_count += 1
			# _increment(winning_goal_count, (r.account_id, latest.year, latest.month), 1, not goal_winner_declared)
			goal_winner_declared = True
		elif losing_variations > 0:
			# Loser has been declared for a goal
			print "..............Adding loser"
			if not experiment_loser_counted:
				losing_experiment_count += 1 
			# _increment(losing_experiment_count, (r.account_id, latest.year, latest.month), 1, not experiment_loser_counted)
			experiment_loser_counted = True
			if not goal_loser_declared:
				losing_goal_count += 1
			# _increment(losing_goal_count, (r.account_id, latest.year, latest.month), 1, not goal_loser_declared)
			goal_loser_declared = True
	# The entire Experiment has no winning or losing variations, however, there are variations with improvement > 0
	if experiment_winner_counted is False and experiment_loser_counted is False: 
		print "..............Adding goals"
		if pos_undecided_goals > 0: 
			pos_undecided_experiment_count += 1
			# _increment(pos_undecided_experiment_count, (r.account_id, latest.year, latest.month), 1)
		elif neg_undecided_goals > 0: 
			neg_undecided_experiment_count += 1
			# _increment(neg_undecided_experiment_count, (r.account_id, latest.year, latest.month), 1)
	return (winning_experiment_count, winning_goal_count, losing_experiment_count, losing_goal_count, pos_undecided_experiment_count, neg_undecided_experiment_count)