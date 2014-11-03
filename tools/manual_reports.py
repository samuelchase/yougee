from models import *
from partner_handlers import *
from wootils import *

partner_ids = ['empereon', 'chad', 'hope']
tdelta = 'month'
year = 2013
month = 10


for partner_id in partner_ids:
  reports = get_partner_all_campaign_reports(partner_id, tdelta, year, month,
      regenerate=True)
  dlist = [r.to_ordered_dict() for r in reports]
  fieldnames = PartnerCampaignReport.fieldnames()
  data = csv_str_from_dict(dlist, fieldnames=fieldnames,
         write_header=True, restval=NA_STR, html=False)
  fn = '_'.join([str(year), str(month), partner_id, 'all_campaigns.csv'])
  with open(fn, 'w') as f:
    f.write(data)
  print 'wrote ' + fn


partner_admins = ['lang', 'LANG']
for partner_admin in partner_admins:
  to_write = partner_admin_all_campaign_reports(partner_admin, tdelta, year,
          month, regenerate=True, strip_free=True,
          json_requested=False)
  fn = '_'.join([str(year), str(month), partner_admin, '_partner_admin_all_campaigns.csv'])
  with open(fn, 'w') as f:
    f.write(to_write)
