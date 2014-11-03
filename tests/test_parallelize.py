# run as
# nosetests --nologcapture parallelize_test.py


# import nose
from nose.tools import eq_ as equal
try:
  import parallelize
except ImportError:
  import sys
  sys.path.append('..')
  import parallelize


def mapper_dummy(entity): 
  pass


def test_expand_function_name():
  test_fnc_path = parallelize.expand_function_name(mapper_dummy)
  true_fnc_path = 'tests.test_parallelize.mapper_dummy'
  print 'test', test_fnc_path
  print 'true', true_fnc_path
  equal(test_fnc_path, true_fnc_path)

#true_fnc_path = 'tests.test_parallelize.mapper_dummy'



#TRIGGER_FUNCTIONS = []
#
#def setup_package():
#  TRIGGER_FUNCTIONS = [
#    new_campaign_event,
#  ]
#
#
#def test_camp_partner_promo():
#  for f in TRIGGER_FUNCTIONS:
#    yield f, camp, partner, promo
#
#
#def new_campaign_event(camp, promo_id, partner_promo_category):
#  pass
