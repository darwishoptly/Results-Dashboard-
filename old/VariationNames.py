import requests
from bs4 import BeautifulSoup
import json 


def endIndex(string):
	curly_count = 0
	index = 0; 
	for c in r:
		if c == "{":
			curly_count += 1
		elif c=="}":
			curly_count -= 1
		if curly_count == 0 and index > 5:
			return index
		index += 1
	raise "never closed"


r = requests.get("https://cdn.optimizely.com/js/285656357.js").text
start_index = r.find("DATA")+5
r = r[start_index:-1]
r = r[0:endIndex(r)+1]

data = json.loads(r)

data['variations']