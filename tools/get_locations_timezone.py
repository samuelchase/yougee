import requests
import json
import csv
import sys
import time

geocode_url = 'http://maps.googleapis.com/maps/api/geocode/json'
timezone_url = 'https://maps.googleapis.com/maps/api/timezone/json'


def normalize_location(loc):
  consts = loc.split()
  newconsts = []
  for c in consts:
    c = c.strip()
    c = c.capitalize()
    newconsts.append(c)
  return ' '.join(newconsts)


results = {}
inf = 'locations.csv'
with open(inf, 'r') as f:
  for line in f:
    loc = normalize_location(line)
    qparams = {'address': loc, 'sensor': 'false'}
    r = requests.get(geocode_url, params=qparams)
    res = json.loads(r.content)
    if res['status'] == 'OK':
      if len(res['results']) > 1:
        lat = res['results'][0]['geometry']['location']['lat']
        lng = res['results'][0]['geometry']['location']['lng']
        print loc, lat, lng,
        qparams = {'location': str(lat) + ',' + str(lng),
            'timestamp': int(time.time()),
            'sensor': 'false'}
        r = requests.get(timezone_url, params=qparams)
        res = json.loads(r.content)
        if res['status'] == 'OK':
          locd = {'lat': lat, 'lng': lng, 'timeZoneId': res['timeZoneId']}
          results[loc] = locd

outf = 'timezones.json'
with open(outf, 'w') as f:
  f.write(json.dumps(results))





