import OptlyData
from dateutil.relativedelta import relativedelta
import requests
import datetime 
import time
from sqlalchemy import *
import sqlalchemy as sqlalchemy
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
import types


class dbHelper:
	
	def __init__(self, engine):
		self.engine = engine
		
	def dbg(self, dbobj, flat=False):
		if dbobj == []:
			return
		object_list = [dbobj] if (type(dbobj) is not types.ListType) and (type(dbobj) is not orm.collections.InstrumentedList) else dbobj
		attrs = self.engine.execute("select * from " + object_list[0].__tablename__).keys()
		for obj in object_list: 
			if not flat:
				pprint([(attr, getattr(obj, attr)) for attr in attrs])
			else:
				print([(attr, getattr(obj, attr)) for attr in attrs])