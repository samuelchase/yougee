from models import *
from numpy import linspace

RR_ORIGIN = 'looper'
n_adjust = 20
to_add = 8000.0

query = RecurringRevenue.gql('where created_by = :1 '
         ' order by created desc', RR_ORIGIN).fetch(n_adjust)

steps = linspace(to_add, 0, n_adjust).tolist()

for rr, offset in zip(query, steps):
  rr.offset = offset
  rr.recurring_revenue += offset
  rr.put()


