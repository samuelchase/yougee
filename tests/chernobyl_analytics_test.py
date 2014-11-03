# run with nosetests -s -x test_adv_dash_urls

from nose.tools import eq_
import datetime
import requests
import json
import unittest


from collections import defaultdict

#pagewoo_camp_key = 'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlyOGxkREEM'
#pagewoo_camp_key = 'agpzfnBhZ2Utd29vckALEgpDYW1wYWlnbkRTIjBhZ2x6Zm01bFlYSjNiMjl5RndzU0NsbGxiSEJLYzI5dVJGTVlnSUNBZ0lEOXJRa00M'
pagewoo_camp_key = 'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVk5WUJvREEM'
year = '2013'
host = 'http://localhost:8082'


def get_data(url):
    data = None
    while not data:
        r = requests.get(url)
        data = json.loads(r.content)['data']
    return data


def sum_single(data):
    return sum(d['y'] for d in data)


def sum_across(data):
    return sum(sum_single(d) for d in data)


class TestConversionConsistency(unittest.TestCase):
    def setUp(self):
        yearly = '/chernobyl/yearly/page_conversions/<pagewoo_camp_key>/<year>'
        yearly = host + yearly.replace('<pagewoo_camp_key>', pagewoo_camp_key)
        self.yearly = yearly.replace('<year>', year)
        select = '/chernobyl/conversiontypes/<pagewoo_camp_key>/<year>'
        select = host + select.replace('<pagewoo_camp_key>', pagewoo_camp_key)
        self.select = select.replace('<year>', year)

    def get_yearly_data(self):
        return get_data(self.yearly)

    def get_select_data(self):
        return get_data(self.select)

    def test_consistency(self):
        yd = self.get_yearly_data()
        sd = self.get_select_data()
        # this is just a temporary test, and is supposed to only work for 2013
        # (which is when we're fixing this data
        today = datetime.datetime.today()
        eq_(str(today.year), year)
        anytime = yd['anytime']
        yearly = sum(yd['yearly'])
        print 'anytime: {}, yearly: {}'.format(anytime, yearly)
        eq_(anytime, yearly)
        ct_anytime = sd['anytime']
        total_ct_anytime = 0
        for d in ct_anytime:
            if d['is_selected']:
                total_ct_anytime += d['y']
            else:
                eq_(d['y'], 0)
        print 'anytime: {}, total ct anytime: {}'.format(anytime, total_ct_anytime)
        eq_(anytime, total_ct_anytime)
        ct_yearly = sd['yearly']
        eq_(ct_anytime, ct_yearly)
        total_ct_yearly = 0
        for d in ct_yearly:
            if d['is_selected']:
                total_ct_yearly += d['y']
            else:
                eq_(d['y'], 0)
        print 'anytime: {}, total ct yearly: {}'.format(anytime, total_ct_yearly)
        eq_(anytime, total_ct_yearly)
        ct_quarter = sd['quarterly']
        total_ct_quarter = 0
        quarterly_count = defaultdict(int)
        for quarter_list in ct_quarter:
            for d in quarter_list:
                if d['is_selected']:
                    total_ct_quarter += d['y']
                    quarterly_count[d['name']] += d['y']
                else:
                    eq_(d['y'], 0)
        print 'anytime: {}, total ct quarter: {}'.format(anytime, total_ct_quarter)
        eq_(anytime, total_ct_quarter)
        ct_anytime_formatted = {}
        for d in ct_anytime:
            ct_anytime_formatted[d['name']] = d['y']
        for ct, val in ct_anytime_formatted.items():
            print 'conv: {} ct anytime: {} ct over quarters: {}'.format(ct, quarterly_count[ct], val)


#pagewoo_camp_key = 'agpzfnBhZ2Utd29vcjoLEgpDYW1wYWlnbkRTIiphZ2x6Zm01bFlYSjNiMjl5RWdzU0NsbGxiSEJLYzI5dVJGTVlyOGxkREEM'
#year = '2013'
## counter_types = ['banner_views'] # 'banner_clicks', 'page_conversions']
#counter_types = ['banner_views', 'banner_clicks', 'page_conversions']
#n_history = '3'
##
#rawurls = [
#    '/chernobyl/yearly/<counter_type>/<pagewoo_camp_key>/<year>', # done
#    '/chernobyl/segments/<counter_type>/<pagewoo_camp_key>/<year>',
#    '/chernobyl/os/banner_views/<pagewoo_camp_key>/<year>',
#    '/chernobyl/conversiontypes/<pagewoo_camp_key>/<year>',
#]
#
#data = {}
#for rawurl in rawurls:
#  url = host + rawurl.replace('<pagewoo_camp_key>', pagewoo_camp_key)
#  url = url.replace('<year>', year)
#  if 'counter_type' in rawurl:
#    for ct in counter_types:
#      curl = url.replace('<counter_type>', ct)
#      r = requests.get(curl)
#      pprint('#######################################')
#      pprint(curl)
#      pprint(json.loads(r.content))
#  else:
#    r = requests.get(url)
#    pprint('#######################################')
#    pprint(url)
#    pprint(json.loads(r.content))
#
#http://testnearwoo.appspot.com/d/index.html#/newresults/ag1zfnRlc3RuZWFyd29vchILEgpBZHZlcnRpc2VyGIL8Kgw/ag1zfnRlc3RuZWFyd29vchkLEhFOZWFyV29vQ2FtcGFpZ25EUxijmysM
#
#if __name__ == '__main__':
#  argv = sys.argv[:]
#  argv.insert(1, '-s')
#  #argv.insert(1, '--nocapture')
#  argv.insert(2, '-x')
#  #argv.insert(2, '--nologcapture')
#  nose.main(argv=argv)

