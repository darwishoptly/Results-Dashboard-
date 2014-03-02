import sys
import time
import datetime
from sqlalchemy import distinct
import requests
import datetime 
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date, PrimaryKeyConstraint, Boolean
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, mapper, relation, sessionmaker

from pprint import pprint
import math

Base = declarative_base()

engine = create_engine("postgresql+psycopg2://poweruser1:h6o3W1a5R5d@success-depot.cwgfpgjh6ucc.us-west-2.rds.amazonaws.com/sd_staging")

class Results(Base):
	__tablename__ = "d_results"
	account_id = Column(String, index=True)
	account_name = Column(String)
	month = Column(Integer)
	year = Column(Integer)
	exps_w_win_vars = Column(Integer)
	goals_w_win_vars = Column(Integer)
	exps_w_lose_vars = Column(Integer)
	goals_w_lose_vars = Column(	Integer[])
	win_undecided_exp = Column(Integer)
	lose_undecided_exp = Column(Integer)
	poc = Column(Boolean)
	churn = Column(Boolean)
	__table_args__ = (PrimaryKeyConstraint('month', 'year', 'account_id'),)

## Go add advanced targeting conditions, traffic allocation, analytics integrations, 
class AppUsage(Base):
	__tablename__ = "d_app_usage"
	account_id = Column(String, index=True)
	month = Column(Integer)
	year = Column(Integer)
	avg_goals_per_experiment = Column(Float)
	num_experiments_started = Column(Integer)
	cum_number_of_custom_segments = Column(Integer)
	poc = Column(Boolean)
	churn = Column(Boolean)
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

# 
# winning_experiment_count = {} # experiments with a winning variation 
# winning_goal_count = {} # goals that have a winning variation
# losing_experiment_count = {} # experiments with a losing variation 
# losing_goal_count = {} # goals that are losing
# pos_undecided_experiment_count = {}
# neg_undecided_experiment_count = {}