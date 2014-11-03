from models import Invoices
import datetime
import csv
import wootils


dt = datetime.datetime(2014, 1, 1, 0, 0, 0)
invoices = Invoices.gql('where date_created >= :1', dt)
invs = []
fieldnames = set()
for inv in wootils.iterate(invoices):
    d = inv.to_dict()
    invs.append(d)
    fieldnames = set(d.keys()).union(fieldnames)

outf = 'invoices_since_jan.csv'
with open(outf, 'w') as f:
    w = csv.DictWriter(f, fieldnames)
    w.writeheader()
    w.writerows(invs)


