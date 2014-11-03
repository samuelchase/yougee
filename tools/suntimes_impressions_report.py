from collections import defaultdict
import csv
import datetime

import models
import wootils


# TODO: filter campaigns that weren't created for the time frane
# specific reports are for

partner_id = 'suntimes'
camps = models.NearWooCampaignDS.gql('where partner_id = :1', partner_id)

dates = [datetime.datetime(2014, 4, 15, 0, 0, 0)]
report = defaultdict(list)
for camp in camps:
    if not camp.pagewoo_campaign_key:
        continue
    res = wootils.get_pagewoo_counters_by_time(
        camp.pagewoo_campaign_key, 'month', 'banner_views', {}, dates,
        add_time_labels=True, time_format='human')

    for label, views in res:
        label = label.replace(' ', '_')
        cpm = round((views/1000.0)*5.0, 2)
        row = {}
        row['name'] = wootils.to_ascii(camp.name)
        row['start_date'] = camp.start_date
        row['end_date'] = camp.end_date
        row['checked_out'] = camp.checked_out
        row['first_invoice'] = camp.first_invoice_date_created_pacific
        row['impressions'] = views
        row['cost'] = cpm
        row['key'] = camp.key.urlsafe()
        report[label].append(row)

for k, rows in report.items():
    fn = partner_id + '_' + k + '.csv'
    fieldnames = ['no campaigns found']
    if rows:
        fieldnames = rows[0].keys()
    with open(fn, 'w') as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print 'wrote ', fn


