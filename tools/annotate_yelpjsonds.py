import yelp
from models import YelpJsonDS
from wootils import db_iterate_cursor


query = YelpJsonDS.all()
for yp in db_iterate_cursor(query):
  yp = yelp.annotate_yelpjsonds(yp)
  yp.put()



