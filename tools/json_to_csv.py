import csv
import json

proc = ['empereon_8', 'empereon_9']

for fb in proc:
  print fb
  inf = fb + '.json'
  with open(inf, 'r') as f:
    data = json.loads(f.read())['data']

  outf = fb + '.csv'
  fieldnames = data['fieldnames']
  reports = data['reports']
  with open(outf, 'w') as f:
    writer = csv.DictWriter(f, fieldnames)
    writer.writeheader()
    writer.writerows(reports)

