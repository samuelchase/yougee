import wootils
import models
import csv

camps = models.NearWooCampaignDS.gql(
    'where neighborhood_ct > :1 and has_first_invoice = :2', 1, False)

outf = 'freeriders.csv'
with open(outf, 'w') as f:
    w = csv.DictWriter(f, models.NearWooCampaignDS._ordered_property_list)
    w.writeheader()
    for camp in wootils.iterate(camps):
        w.writerow(camp.to_ndb_dict())


