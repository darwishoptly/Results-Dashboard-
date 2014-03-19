from sqlalchemy import *
from sqlalchemy import create_engine, orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import csv 
import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, mapper, relation, sessionmaker
from pprint import pprint
import db_helper

test = "James"

Base = declarative_base()


engine = create_engine("postgresql+psycopg2://poweruser1:h6o3W1a5R5d@success-depot.cwgfpgjh6ucc.us-west-2.rds.amazonaws.com/sd_staging")
# helper = db_helper.dbHelper(engine)


#engine = create_engine("postgresql+psycopg2://agregory:password@localhost/postgres")
# engine = create_engine("postgresql+psycopg2://darwish:@172.20.100.16/SuccessDepotStaging")
metadata = MetaData(engine)
metadata.reflect()
Base.metadata = metadata

class ZDOrg(Base): 
	__tablename__ = "zdorg"
	tickets = relationship("ZDTicket", primaryjoin="ZDOrg.id == foreign(ZDTicket.organization_id)", backref="organization")

class ZDTicket(Base):
	__tablename__ = "zdticket"
	ratings = relationship("Nicereply", primaryjoin="ZDTicket.id == foreign(Nicereply.ticketid)", backref="zdticket")

class ZDUser(Base): 
	__tablename__ = "zduser"
	tickets_via_requester_id = relationship("ZDTicket", primaryjoin="ZDUser.id == foreign(ZDTicket.requester_id)", backref="requester")
	tickets_via_submitter_id = relationship("ZDTicket", primaryjoin="ZDUser.id == foreign(ZDTicket.submitter_id)", backref="submitter")
	tickets_via_assignee_id = relationship("ZDTicket", primaryjoin="ZDUser.id == foreign(ZDTicket.assignee_id)", backref="assignee")

class ZDGroup(Base):
	__tablename__ = "zdgroup"
	tickets = relationship("ZDTicket", primaryjoin="ZDGroup.id == foreign(ZDTicket.group_id)", backref="group")

class TotangoUser(Base):
	__tablename__ = "totangouser"

class TotangoActivity(Base):
	__tablename__ = "totangoactivity"

class TotangoAccount(Base):
	__tablename__ = "totangoaccount"

class TaskRayTask(Base):
	__tablename__ = "taskraytask"

class TaskRayProject(Base):
	__tablename__ = "taskrayproject"
	tasks = relationship("TaskRayTask", primaryjoin=("TaskRayProject.id == foreign(TaskRayTask.taskray__project__c)"), backref="taskrayproject", uselist=False)

class SFDCUser(Base):
	__tablename__ = "sfdcuser"

class SFDCTask(Base):
	__tablename__ = "sfdctask"

#class UsageSummary(Base):
#	__tablename__ ="prd_usage_monthly_summary"
		

class SFDCOpportunity(Base):
	__tablename__ = "sfdcopportunity"

class SFDCLead(Base):
	__tablename__ = "sfdclead"

# class SFDCEvent(Base):
# 	__tablename__ = "sfdcevent"

class SFDCContact(Base):
	__tablename__ = "sfdccontact"

class SFDCAccount(Base):
	__tablename__ = "sfdcaccount"
	
	opportunities = relationship("SFDCOpportunity", primaryjoin="SFDCAccount.id == foreign(SFDCOpportunity.accountid)", backref="account")
	sfdctasks = relationship("SFDCTask", primaryjoin="SFDCAccount.id == foreign(SFDCTask.accountid)", backref="account")
	zdorgs = relationship("ZDOrg", primaryjoin="SFDCAccount.zendesk__zendesk_organization_id__c == foreign(ZDOrg.id)", backref=backref("sfdcaccount" , uselist=False))
	payments = relationship("Payments", primaryjoin=("SFDCAccount.recurly__account_code__c == foreign(Payments.account_id)"), backref="sfdcaccount")
	totangoaccount = relationship("TotangoAccount", primaryjoin=("SFDCAccount.recurly__account_code__c == foreign(TotangoAccount.accountid)"), backref=backref("sfdcaccount", uselist=False), uselist=False)
	taskraytasks = relationship("TaskRayTask", primaryjoin=("SFDCAccount.id == foreign(TaskRayTask.account__c)"), backref="account")
	# projects = relationship("TaskRayProject", primaryjoin=("SFDCAccount.id == foreign(SFDCTaskRayProject.accountid)"), backref="account")
	# recurly__account_code__c = Column(String, primary_key=True)

class Payments(Base):
	__tablename__ = "payments"

class Nicereply(Base):
	__tablename__ = "nicereply"

class Auth(Base):
	__tablename__ = "auth"

class ZDComment(Base):
	__tablename__ = "zdcomment"


class UsageMonthly(Base):
	__tablename__ = "prd_usage_monthly_summary"

class Summary(Base):
	__tablename__ = "prd_account_summary"
	sfdcaccount = relationship("SFDCAccount", primaryjoin=("Summary.accountID == foreign(SFDCAccount.recurly__account_code__c)"), backref="summary")

class SummaryMonthly(Base):
	__tablename__ = "prd_account_monthly_summary"

class Results(Base):
	__tablename__ = "d_results"

class Account(Base):
	__tablename__ = "prd_account_master"

class User(Base):
	__tablename__ = "user_master"
	account = relationship("Account", primaryjoin=("User.account_id == foreign(Account.accountID)"), backref="user")

class AppUsage(Base):
	__tablename__ = "d_app_usage"



Session = sessionmaker(bind=engine)
s = Session()