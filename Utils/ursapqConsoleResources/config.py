import json
import os
from collections import namedtuple

def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
def json2obj(filename): return json.load(filename, object_hook=_json_object_hook)

local_dir = os.path.dirname(os.path.abspath(__file__))
file = open(local_dir + '/config.json', 'r')
config = json2obj(file)
file.close()
