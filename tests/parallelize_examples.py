""" to be copied and pasted into remote shell or
interactive console """

from models import Partner
from models import NearWooCampaignDS
import parallelize
reload(parallelize)

import jconfig

####

def ndb_mapper(partner):
    yield partner
ndb_query = Partner.gql('where partner_admin = :1', 'SuperHeroes')
p1 = parallelize.pmap(ndb_mapper, ndb_query)
print parallelize.get_link(p1)

######

def db_mapper(camp):
    yield camp
db_query = NearWooCampaignDS.gql('where partner_id = :1', 'batman')
p2 = parallelize.pmap(db_mapper, db_query)
print parallelize.get_link(p2)

####

input_filename = '/gs/testnearwoo.appspot.com/manual-uploads/emails_to_check2.csv'
def file_mapper(line):
    pass # if yields, needs to yield some kind of ds entity
p3 = parallelize.pmap_from_file(file_mapper, input_filename)
print parallelize.get_link(p3)

#### 
def reducer(key, values):
    yield key+'\n'
#p4 = parallelize.pmapreduce(ndb_mapper, reducer, ndb_query)
p5 = parallelize.pmapreduce(ndb_mapper, reducer, ndb_query,
        output_filename=output_filename)
p6 = parallelize.pmapreduce_from_file(ndb_mapper, reducer, input_filename)

input_filename = '/testnearwoo.appspot.com/manual-uploads/emails_to_check2.csv'
output_filename = '/testnearwoo.appspot.com/results/results.csv'


from models import Partner
from models import NearWooCampaignDS
import parallelize

import jconfig


def file_mapper(line):
  yield (line, '')

def file_reducer(key, value):
  yield key

p7 = parallelize.pmapreduce_from_file(file_mapper, file_reducer, input_filename,
        output_filename=output_filename)


input_filename = '/gs/testnearwoo.appspot.com/manual-uploads/emails_to_check2.csv'
output_filename = '/testnearwoo.appspot.com/results/results.csv'


from models import Partner
from models import NearWooCampaignDS
import parallelize

import jconfig

def link(pipeline):
   return (jconfig.get_host() + '/' + pipeline.base_path + 
       '/status?root=' + pipeline.pipeline_id)

def file_mapper(line):
  yield (line, '')

def file_reducer(key, value):
  yield key

p7 = parallelize.pmapreduce_from_file(file_mapper, file_reducer, input_filename,
        output_filename=output_filename)
print link(p7)



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
