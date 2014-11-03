from wootils import *
from kpi_data import *
import datetime


dates = [datetime.datetime(2013, 11, 18, 0, 0, 0),
    datetime.datetime(2013, 11, 19, 0, 0 ,0)]

agent = 'nearwoo'

paid = get_counters_by_time(agent, 'day', 'ncampaigns', 'paid', dates,
    add_time_labels=True, time_format='human')
free = get_counters_by_time(agent, 'day', 'ncampaigns', 'free', dates,
    add_time_labels=True, time_format='human')


