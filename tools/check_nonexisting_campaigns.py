from models import *

camp_keys = ["aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGMLVIgw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGKndIgw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGOH0Igw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGLOEIww", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGIGUIww", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGNOjIww", "aglzfm5lYXJ3b29yHgsSEU5lYXJXb29DYW1wYWlnbkRTGICAgICA7_AJDA", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGPGqKww", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGIr5Kww", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGNiILAw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGJ3oLgw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGPGeLww", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGKGMMAw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGOrxMAw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGLz-MQw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGPy8Mgw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGOTEMgw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGOG4Ngw", "aglzfm5lYXJ3b29yGQsSEU5lYXJXb29DYW1wYWlnbkRTGPrfZQw"]

pagewoo_keys = []
for camp_key in camp_keys:
  camp = NearWooCampaignDS.get(camp_key)
  print camp.name, camp.checked_out, camp.neighborhood_ct, camp.advertiser_key
  try:
    adv = ndb.Key(urlsafe=camp.advertiser_key).get()
    print adv.name
  except:
    print 'no advertiser'
  pagewoo_keys.append(camp.pagewoo_campaign_key)


pagewoo_keys = [
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlzWVFqREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVl3ZFVpREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVktZXdpREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVk4OFVpREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVk3TFlhREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlrLVVpREEM',
    u'agpzfnBhZ2Utd29vckALEgpDYW1wYWlnbkRTIjBhZ2x6Zm01bFlYSjNiMjl5RndzU0NsbGxiSEJLYzI5dVJGTVlnSUNBZ01DQWx3c00M',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlpYU1yREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVl4cm9yREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlyOElyREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlzLUF1REEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlpWmN2REEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVltZVV2REEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVl5dGd1REEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVl3cVV5REEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVl2XzR4REEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlwWXd3REEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVktYkEyREEM',
    u'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVk2XzlxREEM']


for pw_key in pagewoo_keys:
  print pw_key,
  try:
    camp = CampaignDS.get(pw_key)
    if camp is None:
      print ' is none'
  except:
    print ' could not retrieve camp'




