import pdb
from google.appengine.api.app_identity import get_application_id

if 'nearwoo' in get_application_id():
  from models import *
  from wootils import *
  from kpi_data import *
else:
  from rtbopt import *
  from kpi_data import *

