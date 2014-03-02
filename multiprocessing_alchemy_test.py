import OptlyData
import requests
import datetime 

from sqlalchemy import *
from sqlalchemy import create_engine, orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import csv 
import psycopg2
import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, mapper, relation, sessionmaker
from pprint import pprint
import math
import requests

GAE_Auth_Cookie = "AJKiYcH8Cb4b4xKEqs9M-mNL1kLoCszp1NXp45IRqOcFrIYFvG65H63jK7CkKhyW-8wdrSner5v4jK_YoeBKvkLEv6h7dez8frKgOnbplWYLhmlMHEZlA4bIT7OUof49qnhM8Azv7aAFcwHG_iPooKg-mCnvcQnv_mY1bKcnrk354feqPuCa2oKpgbtcqit3eBtU9ZzBonM98v-gk01Yq_kUlBitmnPB2u5LVey_5UW9JH5rsbOHDzzzH7Zw8GboqkckDhjZ-klw-3EjRUTBEzkM3mIs8_gqX0xc-bTIBL-_S8JmfZWlS5NDNU0sL0mQlZf7V6l8PRba2s0XmIGo5QQZrXKQipvd-GJiCu1i2aRq-DO1BCZWpropFpyVu_PX-KCkK1ds-SYLhsmLeNT9uiVXkAsVLTLRrQLIwO1pvkbHD6Hk3YFS3ab_rUhHZrBWRxv6q_VVK6Qnour7Q5X7WNxTuIFMcmObDrox1ec64_raoriN0q16Nos8LelEQ0G7gIzH7qG-iH8it1vbwe5q8zAz_iIT9Vjwytq8n4Bl66ezN1Tw0G046_UPPZFKoNbHoHi5TV51NU2gZcUi70QewBfdBNZZPN-Yd4tYYtr_x9NzMj4-iwBpuHhenTuEth1-K_YhA82eILBiO2IJygA5aSDphTmTjHwOMQ"
start = datetime.datetime(2013, 3 ,1)

Base = declarative_base()

engine = create_engine("postgresql+psycopg2://poweruser1:h6o3W1a5R5d@success-depot.cwgfpgjh6ucc.us-west-2.rds.amazonaws.com/sd_staging")

#engine = create_engine("postgresql+psycopg2://agregory:password@localhost/postgres")
# engine = create_engine("postgresql+psycopg2://darwish:@172.20.100.16/SuccessDepotStaging")
metadata = MetaData(engine)
metadata.reflect()
Base.metadata = metadata

class UsageMonthly(Base):
	__tablename__ = "prd_usage_monthly_summary"

class Summary(Base):
	__tablename__ = "prd_account_summary"

class SummaryMonthly(Base):
	__tablename__ = "prd_account_monthly_summary"

class Results(Base):
	__tablename__ = "results"

class Account(Base):
	__tablename__ = "prd_account_master"

class User(Base):
	__tablename__ = "user_master"
	account = relationship("Account", primaryjoin=("User.account_id == foreign(Account.accountID)"), backref="user")

Session = sessionmaker(bind=engine)
s = Session()



