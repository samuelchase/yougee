import webapp2
from google.appengine.api import mail
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
from google.appengine.api import users
from protorpc import messages
import cgi
import json
import models
import logging
import random
import wootils
from wootils import PageWooError
from wootils import make_status_message
import jchernobyl_client
from StringIO import StringIO
import csv


class ChangeKind(messages.Enum):
    woos = 1
    block_points = 2


class ChangeLog(ndb.Expando):
    kind = msgprop.EnumProperty(ChangeKind, required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    user = ndb.UserProperty()
    user_str = ndb.StringProperty(default='<no user>')
    related_key = ndb.StringProperty()


# TODO: Move this into handlers and use this everywhere
class BaseHandler(webapp2.RequestHandler):
    def write_status_message(self, success=True, message=None, code=200,
                             data=None):
        """Formats data appropriately for the JS front end and modifies status
        code to match given code"""
        if code:
            code = int(code)
        log_func = logging.debug

        if not success:
            log_func = logging.info

        if code != 200:
            log_func = logging.warning

        log_func("Writing status message. Success: %s. Message: %s", success,
                 message)
        if code is not None:
            self.response.set_status(code)
        if self.request.get('format') and self.request.get('format') == 'csv':
            if not data:
                fieldnames = ['Error']
                results = [{'Error': 'no results'}]
            elif 'results' in data and data['results']:
                fieldnames = sorted(set(k for r in data['results'] for k in r))
                results = data['results']
            elif 'result' in data and isinstance(data['result'], dict):
                fieldnames = data['result'].keys()
                results = [data['result']]
            elif 'result' in data and data['result']:
                fieldnames = ['Result']
                results = [{'Result': data['result']}]
            else:
                fieldnames = ['Error']
                results = [{'Error': 'no results'}]

            if not success:
                fieldnames = ['Error']
                results = [{'Error': 'no results'}]
            f = StringIO.StringIO()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
            resp = f.getvalue()
            self.response.content_type = 'text/csv'
            name = self.request.path.split('/') or 'data'
            dispo = 'attachment; filename="%s.csv"' % name
            self.response.headers['Content-Disposition'] = dispo
            self.response.write(resp)
        else:
            msg = make_status_message(success=success, message=message, code=code,
                                    data=data)
            self.response.content_type = 'application/json'
            self.response.write(msg)


class WooBucket(BaseHandler):
    def get(self, camp_key):
        self.response.write(
                wootils.make_status_message(success=False,
                    message='not yet supported'))

    def post(self, camp_key):
        # TODO: adapt this to the new format (nearwoo knows everything)
        """Update woo bucket. Two options for format:

        1 - {'woos_left': N}  # sets woos left (and handles max views for you)
        2 - {'max_views': N}  # sets max_views (and woos left will just fall out
        """
        user = users.get_current_user()
        if not user:
            self.write_status_message(success=False,
                                      message=('You are not permitted to'
                                               ' change woos'))
            return
        # TODO: Bleach this stuff
        camp = models.NearWooCampaignDS.urlsafe_get(camp_key)
        if camp is None:
            self.write_status_message(success=False,
                                      message='campaign not found')
            return
        logging.info("%s wants to set woos on PW for camp %s", user,
                     camp.key.urlsafe())
        logging.info(("Trying to changing nearwoo: %s with user %s") %
                     (camp.key.urlsafe(), users.get_current_user()))
        # don't pass along crap data or extraneous args
        body = json.loads(self.request.body)
        logging.info("Request data: %s", body)
        set_woos_left = body.get('woos_left', None)
        set_max_views = body.get('max_views', None)

        # boilerplate for checking assumptions
        if set_max_views is not None and set_woos_left is not None:
            self.write_status_message(success=False,
                                      message=('Can only set one of max_views'
                                               ' and woos_left')
                                      )
            return

        if set_max_views is None and set_woos_left is None:
            self.write_status_message(success=False,
                                      message=('need to specify either max'
                                               ' views or woos left'))

        if not camp.pagewoo_campaign_key and set_woos_left is not None:
            self.write_status_message(success=False,
                                      message=('Cannot set woos left without'
                                               ' sending to Pagewoo'))
            return

        current_views_anytime = camp.views
        # try to get data from PW if possible, otherwise fall back to existing
        # NW information.
        if camp.pagewoo_campaign_key:
            try:
                current_views_anytime = jchernobyl_client.get_pagewoo_counters(
                        camp.pagewoo_campaign_key,
                        'anytime', 'banner_views', {}, 1, raise_on_error=True,
                        add_time_labels=False)[0]
                logging.info("Views anytime from PW: %s", current_views_anytime)
            except PageWooError as e:
                logging.exception("PW failure with woos tool")
                self.write_status_message(success=False,
                                        message='Pagewoo Error: %s' % e)
                return
        existing_max_views = camp.max_views
        # we're not caring about supercharge views now (because it'll just end
        # up giving them more views, not less, which is fine).
        existing_supercharge_views = 0

        # force to zero at lowest
        existing_woos_left = ((existing_max_views + existing_supercharge_views)
                                 - current_views_anytime)

        if set_woos_left:
            delta = set_woos_left - existing_woos_left
            logging.info("With set_woos_left of %s, change in max_views should"
                         " be %s", set_woos_left, delta)
        else:
            delta = set_max_views - (existing_max_views + existing_supercharge_views)
            logging.info("With set_max_views of %s, change in max_views should"
                         " be %s", set_max_views, delta)
        new_max_views = existing_max_views + delta
        msg = ''
        if new_max_views < 0:
            logging.info("Max views would be less than 0 (%s), forcing to 0")
            new_max_views = 0
            msg += 'NOTE: Max views were set to 0\n'
        new_net_woos_left = new_max_views - current_views_anytime
        camp.max_views = new_max_views
        def txn():
            store_woos_change(camp, existing_woos_left, new_net_woos_left,
                              existing_max_views, new_max_views, set_woos_left,
                              set_max_views)
            camp.put()
        ndb.transaction(txn, xg=True)
        jchernobyl_client.call_chernobyl(camp, use_pw_max_views=False)
        msg = ('Max views set to %s, net woos left approx. %s'
               ' [total views: %s]') % (new_max_views, new_net_woos_left,
                                        current_views_anytime)
        self.write_status_message(success=True, message=msg)


# old change deltas were just a delta, now we want to set woos_left and use max
# views to do it.
def store_woos_change(camp, previous_woos_left, current_woos_left,
                      previous_max_views, current_max_views, set_woos_left,
                      set_max_views):
    user = users.get_current_user()
    change = ChangeLog()
    change.kind = ChangeKind.woos
    change.related_key = camp.key.urlsafe()
    if user:
        change.user = user
        change.user_str = str(user)
    change.previous_woos_left = previous_woos_left
    change.current_woos_left = current_woos_left
    change.set_woos_left = set_woos_left
    change.set_max_views = set_max_views
    change.previous_max_views = previous_max_views
    change.current_max_views = current_max_views
    change.woos_left_delta = ((current_woos_left or 0) -
                              (previous_woos_left or 0))
    change.max_views_delta = ((current_max_views or 0) -
                              (previous_max_views or 0))
    change.put()
    logging.debug("Storing change: %s" % change)
    return change


def send_change_email(user, camp, woos_left, change):
    try:
        kwargs = {}
        user_email = user.email() or ''
        # only cc to nearwoo
        if user_email and user_email.endswith('nearwoo.com'):
            kwargs['cc'] = user_email
        subject = 'Woos changed on %s' % camp.name
        body = '%s (%s) updated %s (key: %s)' % (user.nickname(),
                user.email(), camp.name, camp.key.urlsafe())
        body += ' Woos set to %s (%s)' % (woos_left, change)

        mail.send_mail('change-notification@nearwoo.appspotmail.com',
                        'justin@nearwoo.com',
                        subject,
                        body,
                        **kwargs)
    except:
        logging.exception("Couldn't send email")
    return True

class ForceResendCamp(webapp2.RequestHandler):

    "Equivalent to using call chernobyl in the console"
    def get(self, camp_key):
        camp = models.NearWooCampaignDS.urlsafe_get(camp_key)
        if not camp:
            self.response.set_status(400)
            self.response.write(make_status_message("Campaign not found"))
            return
        if not camp.pagewoo_campaign_key:
            self.response.write(make_status_message(success=False,
                                                    message='no pw key'))
            return
        try:
            jchernobyl_client.call_chernobyl(camp, use_pw_max_views=True)
        except Exception:
            logging.exception("Failed to call chernobyl for camp: %s",
                              camp.key.urlsafe())
            self.response.write(make_status_message(success=False,
                                                    message='Server error'))
            return
        if self.request.get('format') == 'json':
            self.response.write(make_status_message(success=True,
                                                    message='pushed again'))
        else:
            self.response.write("Camp saved to PW as: <pre>%s</pre><br /> (data: <pre>%s</pre>)"
                                % (cgi.escape(str(camp.pagewoo_campaign_key)),
                                   cgi.escape(str(camp))))


class RedirectToPWShow(BaseHandler):
    def get(self, camp_key):
        camp = models.NearWooCampaignDS.urlsafe_get(camp_key)
        if not camp.pagewoo_campaign_key:
            self.response.write('Sorry, not on pagewoo :-/')
            return
        url = ('http://page-woo.appspot.com/show/{pw_key}'
               '?is_test=True&camp_key={pw_key}'.format(
                   pw_key=camp.pagewoo_campaign_key))
        self.redirect(url)


class DailyData(BaseHandler):
    def get(self, camp_key):
        camp = models.NearWooCampaignDS.urlsafe_get(camp_key)
        pw_key = camp.pagewoo_campaign_key
        if not pw_key:
            self.write_status_message(success=False, message='Not on pagewoo')
            return
        views = wootils.get_pagewoo_counters(pw_key, 'day', 'banner_views', {}, 60)
        clicks = wootils.get_pagewoo_counters(pw_key, 'day', 'banner_clicks',
                                              {}, 60)
        view_numbers = zip(*views)[1]
        click_numbers = zip(*clicks)[1]
        dates = zip(*views)[0]
        pacing = [random.random() for _ in views]
        data = []
        for view, click, date, pace in zip(view_numbers, click_numbers, dates,
                                           pacing):
            data.append({
                'views': view,
                'clicks': click,
                'date': date,
                'pacing': pace
            })
        self.write_status_message(success=True,
                                  message='found analytics',
                                  data=data)
template = """
<html>
    <head>
    <link href="//maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css" rel="stylesheet">
    <title>Search for campaigns</title>
    </head>
    <body>
    <h3> NearWoo Campaign Search </h3>
    <nav class="navbar navbar-default" role="navigation">
        <div class="container-fluid">
            <div class="navbar-header">
                <div class="navbar-brand">Find Campaigns</div>
                </div>
                <div>
                    <form class="navbar-form navbar-left" role="search" action='/admin/search', method='GET'>
                        <div class="form-group">
                            <input type='text' id='query' name='query'
                            class="form-control"
                            placeholder='Enter search string'
                            value='{query}'></input>
                        </div>
                        <button type='submit' class="btn btn-default">Search</button>
                    </form>
                </div>
            </div>
        </div>
    </nav>
    <div class="container-fluid">
        <div class="row row-fluid">
            {data}
        </div>
    </div>
    </body>
</html>
"""

class CampaignSearchAPI(BaseHandler):
    def get(self, query=None):
        query = query or self.request.get('query')
        format = self.request.get('format')
        if not query and format != 'json':
            self.write_html()
            return
        camp_keys, search_results = wootils.search_for_campaigns(query)
        logging.info('Search results: %s', search_results)
        camps = models.ndb.get_multi(camp_keys)
        data = []
        for camp in camps:
            if not camp:
                continue
            data.append({
                'dash_url': camp.dash_url,
                'nw_v1_url': camp.url,
                'nw_v2_url': camp.url_v2,
                'name': camp.store or camp.name,
                'camp_key': camp.key.urlsafe(),
                'pagewoo_key': camp.pagewoo_campaign_key,
                'camp': camp,
            })
        if format == 'json':
            self.write_status_message(success=True,
                                    message='search results',
                                    data=data)
        else:
            self.write_html(query, data)

    def write_html(self, query=None, camp_search_data=None):
        if not query:
            data = ''
            query = ''
            self.response.write(template.format(data=data, query=query))
            return
        header = '<th>' + '</th><th>'.join(['Name', 'Master Dash', 'V1 Dash',
                                            'V2 Dash', 'Bucket', 'Views',
                                            'Remaining', 'Paused']) + '</th>'
        tmpl = ('<tr>'
                '<td>{name}</td>'
                '<td><a href="{dash_url}"> Master Dash </a></td>'
                '<td><a href="{nw_v1_url}"> V1 Dash </a></td>'
                '<td><a href="{nw_v2_url}"> V2 Dash </a></td>'
                '<td>{camp.max_views}</td>'
                '<td>{camp.woos_left}</td>'
                '<td>{camp.views}</td>'
                '<td>{camp.paused}</td>'
                '</tr>')
        rows = '\n'.join([tmpl.format(**d) for d in camp_search_data or []])
        data = '<table class="table table-striped table-bordered"><thead>%s</thead><tbody>%s</tbody></table>' % (header,
                                                                      rows)
        self.response.write(template.format(data=data, query=query))


app = webapp2.WSGIApplication([
    (r'/admin/woobucket/(.*)', WooBucket),
    (r'/admin/re-callchernobyl/(.*)', ForceResendCamp),
    (r'/admin/redirect/pagewoo-show/(.*)', RedirectToPWShow),
    (r'/admin/search', CampaignSearchAPI),
    (r'/admin/search/(.*)', CampaignSearchAPI),
    ])
