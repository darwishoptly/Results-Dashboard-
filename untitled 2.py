start = datetime.datetime(2013, 1 ,1)

accounts = s.query(Summary).filter(Summary.plan == 'platinum', Summary.startDate >= start).all()



## Question - How to determine the valid start date? 
no_onboardings = []
def getOnboardingStartDate(account):
	tasks = account.sfdcaccount[0].taskraytasks
	onboarding_start_dates = [t.createddate for t in tasks if t.taskrayproject.project_type__c == "Onboarding"]
	## TODO refactor to minimize queries to onboardings
	if len(onboarding_start_dates) == 0:
		no_onboardings.append(account.accountID)
		return None
	else:
		onboarding_start_dates.sort()
		start_date = onboarding_start_dates[0]
		return start_date
	
	
	
	
	
	
	
	# 	Gives different numbers 
	sub_starts = [o.subscription_start_date__c for o in account.sfdcaccount[0].opportunities]
	sub_starts.sort()
	sub_starts[0]
	# column name = stage, value = closed/won | subscription level starts with Platinum or Agency 


