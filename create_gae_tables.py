import sys
import time
import datetime
from sqlalchemy import distinct
# import requests
import datetime 
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date, PrimaryKeyConstraint, Boolean
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, mapper, relation, sessionmaker

from pprint import pprint
import math

# GAE 
import remote_gae 
import models # must adjust this to point to the right models  

remote_gae.fix_path()
remote_gae.configure_gae_with_defaults(local_gae=False) 


Base = declarative_base()

engine = create_engine("postgresql+psycopg2://poweruser1:h6o3W1a5R5d@success-depot.cwgfpgjh6ucc.us-west-2.rds.amazonaws.com/sd_staging")

# App Engine - monthly summary: 
# experiments started 
# custom segments created
# which targeting features used
# high traffic allocation to one variation
# types of experiments (MVT vs A/B vs Multipage)
# Types of goals created 

# App Engine Overall Summary: 
# Analytics Integrations used 
# of collaborators on experiment 
	

# project_goals.ProjectGoal.query(project_goals.ProjectGoal.experiment_ids == exp.experiment_id, project_goals.ProjectGoal.deleted == False)

class GAppUsageMonthly(Base):
	__tablename__ = "d_app_usage_monthly"
	# Account Information  
	account_id = Column(String, index=True)
	month = Column(Integer)
	year = Column(Integer)
	poc = Column(Boolean)
	churn = Column(Boolean)
	# High Level Stats
	num_experiments_started = Column(Integer)
	number_of_custom_segments = Column(Integer)
	high_traffic_allocation = Column(Integer) # Over 85% ends on one variation
	# Targeting 
	audience_targeting = Column(Integer)
	query_param = Column(Integer)
	languages = Column(Integer)
	cookies = Column(Integer)
	referrer_urls = Column(Integer)
	ip_targeting = Column(Integer)
	geo_targeting = Column(Integer)
	segment_targeting = Column(Integer)
	custom_tags = Column(Integer)
	custom_javascript = Column(Integer)
	# Types of Tests
	mvts = Column(Integer)
	multipages = Column(Integer)
	redirect = Column(Integer)
	# Goals  
	avg_goals_per_experiment = Column(Float)
	click_goals = Column(Integer)
	pageview_goals = Column(Integer)
	revenue_goals = Column(Integer)
	__table_args__ = (PrimaryKeyConstraint('month', 'year', 'account_id'),)


class GAppUsageSummary(Base):
	__tablename__ = "d_app_usage_summary"
	# Account Information  
	account_id = Column(String, index=True)
	month = Column(Integer)
	year = Column(Integer)
	poc = Column(Boolean)
	churn = Column(Boolean)
	# High Level Stats
	num_experiments_created = Column(Integer)
	number_of_custom_segments = Column(Integer)
	high_traffic_allocation = Column(Integer) # Over 85% ends on one variation
	# Targeting 
	audience_targeting = Column(Integer)
	query_param = Column(Integer)
	languages = Column(Integer)
	cookies = Column(Integer)
	referrer_urls = Column(Integer)
	ip_targeting = Column(Integer)
	geo_targeting = Column(Integer)
	segment_targeting = Column(Integer)
	custom_tags = Column(Integer)
	custom_javascript = Column(Integer)
	# Types of Tests
	mvts = Column(Integer)
	multipages = Column(Integer)
	redirect = Column(Integer)
	# Goals  
	avg_goals_per_experiment = Column(Float)
	click_goals = Column(Integer)
	pageview_goals = Column(Integer)
	revenue_goals = Column(Integer)
	# Analytics Integration 
	integrated = Column(Boolean)
	# Other
	num_collaborators = Column(Integer)
	
	__table_args__ = (PrimaryKeyConstraint('month', 'year', 'account_id'),)


metadata = Base.metadata
metadata.create_all(engine)

Session = sessionmaker(bind=engine)
sdstaging = Session()

r = Results()
a = AppUsage()
# r.account_id = "0"
# r.month = 1
# r.year = 1 
# sdstaging.merge(r)
sdstaging.commit()