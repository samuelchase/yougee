from partner_handlers import *
from wootils import *


year = 2013
month_or_week = 11
partner_ids = ['lang']
fieldnames = PartnerCampaignReport.fieldnames()
for partner_id in partner_ids:
    print partner_id,
    reports = get_partner_all_campaign_reports(partner_id, 'month', year,
        month_or_week, regenerate=False, include_free=False)
    print 'got reports',
    dlist = [r.to_ordered_dict() for r in reports]
    data = dicts_to_csv_str(dlist, fieldnames=fieldnames,
        write_header=True, restval=NA_STR, html=False)
    outf = '_'.join(['partner', partner_id, str(year), str(month_or_week), 'itemized.csv'])
    with open(outf, 'w') as f:
      f.write(data)
    print 'wrote data'

year = 2013
month_or_week = 11
for partner_admin in ['LANG', 'lang']:
    data = partner_admin_all_campaign_reports(partner_admin, 'month', year,
             month_or_week, regenerate=False, include_free=False, json_requested=False)
    outf = '_'.join(['partner_admin', partner_admin, str(year), str(month_or_week), 'itemized.csv'])
    with open(outf, 'w') as f:
        f.write(data)

partner_admin = 'LANG'
partner_admin = 'lang'
query = Partner.gql('where partner_admin = :1', 'lang')
for p in ndb_iterate_cursor(query):
    #for p in query:
    print p.partner_id, p.partner_admin, len(p.campaigns)


