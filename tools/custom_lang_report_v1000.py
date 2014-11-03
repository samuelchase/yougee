import models
import csv


rows = []
count = 0
partner_admin = 'lang'
partners = models.Partner.gql('where partner_admin = :1', partner_admin)
for p in partners:
    print p.partner_id
    camps = models.NearWooCampaignDS.gql('where partner_id = :1', p.partner_id)
    for camp in camps:
        count += 1
        if count % 10 == 0:
            print count
        camp_key = str(camp.key())
        d = {}
        d['camp_key'] = camp_key
        d['is_live'] = camp.is_live
        d['camp_name'] = camp.name
        d['neighborhoods'] = camp.neighborhood_ct
        d['category'] = camp.business_type
        d['views'] = camp.views
        d['clicks'] = camp.clicks
        d['conversions'] = camp.conversions
        invoiced = 0.0
        invs = models.Invoices.gql('where campaign_key = :1', camp_key)
        for inv in invs:
            invoiced += inv.charge_amount
        d['invoiced'] = invoiced
        rows.append(d)

fields = [
    'camp_name',
    'is_live',
    'category',
    'neighborhoods',
    'views',
    'clicks',
    'conversions',
    'invoiced',
    'camp_key']

outf = 'custom_lang_report_v1000.csv'
with open(outf, 'w') as f:
    writer = csv.DictWriter(f, fields)
    writer.writeheader()
    writer.writerows(rows)


