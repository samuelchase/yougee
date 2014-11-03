import csv
import datetime


import wootils
import models


partner_ids = [
    p.partner_id for p in
    models.Partner.gql('where partner_admin in :1', ['lang', 'LANG'])]
dts = [datetime.datetime(2014, 1, 15, 0, 0, 0),
       datetime.datetime(2014, 2, 15, 0, 0, 0)]
month_tqs = [wootils.get_time_qualifier('month', dt=dt) for dt in dts]


for month_tq in month_tqs:
    invs = models.Invoices.gql(
        'where partner_id in :1 and month_tq = :2',
        partner_ids, month_tq)
    rows = [inv.to_dict() for inv in invs]
    if rows:
        fieldnames = rows[0].keys()
        fn = 'lang_' + month_tq + '.csv'
        with open(fn, 'w') as f:
            writer = csv.DictWriter(f, fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print 'wrote %s' % fn
    else:
        print 'no invoices found for %s' % month_tq
    



