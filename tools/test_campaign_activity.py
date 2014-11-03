from models import *
from kpi_data import *


# testnearwoo campaign
camp_key = 'ag1zfnRlc3RuZWFyd29vchkLEhFOZWFyV29vQ2FtcGFpZ25EUxjp4AwM'
camp = NearWooCampaignDS.get(camp_key)
promo_id = camp.promo_id
ppc = camp.partner_promo_category

# track_campaign_edit(camp_key, 'created', 0, 5, 0.0, 20.00, 0, 50.00, 0)
# activity = CampaignActivity.get_by_id('campaign_activity_' + camp_key)

partner_promo_category = ppc
amount_charged = 15.00
n_block_groups = 2
block_points_used = None

if block_points_used is None:
  block_points_used = 0
track_campaign_edit(camp_key, 'create', 0, n_block_groups, 0.0,
    camp.amount_subscribed, block_points_used, amount_charged, 0)


track_new_campaign(camp_key, 10.00, 2, block_points_used=0,
    promo_id=promo_id, partner_promo_category=ppc)

track_upgrade(camp_key, 50.00, 10.00, 60.00, 2, 6,
    block_points_used=0, promo_id=promo_id, partner_promo_category=ppc)

track_supercharge(camp_key, 25.00, 9000, block_points_used=1,
    promo_id=promo_id, partner_promo_category=ppc)

track_downgrade(camp_key, 60.00, 0.00, 6, 1, promo_id=promo_id,
    partner_promo_category=ppc)


