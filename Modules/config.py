import json
from collections import namedtuple

def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
def json2obj(filename): return json.load(filename, object_hook=_json_object_hook)

file = open('config.json', 'r')
config = json2obj(file)
file.close()
