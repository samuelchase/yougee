#!/usr/bin/env python
from google.appengine.api import urlfetch
from google.appengine.api import users
import webapp2
import logging
import json
import os


from webapp2_extras import jinja2
from webapp2_extras.routes import RedirectRoute


import models

class Business(webapp2.RequestHandler):
    def get(self, attr):
        result = []
        businesses = models.Business.gql('where ' + attr + '= :1', True).fetch(1000)
        for b in businesses:
            result.append(b.to_dict())

        self.response.out.write(json.dumps(result))

    def post(self):
        data = json.loads(self.request.body)
        business = models.Business()
        business.name = data['name']
        business.address = data['address']
        business.phone = data['phone']
        business.notes = data['notes']
        business.organic = data['organic']
        business.seasonal_menu = data['seasonal_menu']
        business.locally_sourced = data['locally_sourced']
        business.free_range = data['free_range']
        business.grass_fed = data['grass_fed']
        business.no_gmo = data['no_gmo']
        business.gluten_free = data['gluten_free']
        business.vegan = data['vegan']
        business.veganic = data['veganic']
        business.composting = data['composting']
        business.bike_parking = data['bike_parking']
        business.leed_certified = data['leed_certified']
        business.renewable_energy = data['renewable_energy']
        business.put()

        self.response.out.write(business.to_json())


class RenderIndexHandler(webapp2.RequestHandler):

    """Renders the single static-ish index.html that then sets up the AngularJS
    code that powers the site. We use jinja to render it so we can include the
    profiler from gae_mini_profiler"""
    def get(self, directory='yougee'):
        if directory == 'yougee':
            logging.warning(directory)
            self.redirect('/yougee/index.html')
            return

        self.response.write('directory not found')



class Webapp2HandlerAdapter(webapp2.BaseHandlerAdapter):
    def __call__(self, request, response, exception):
        request.route_args = {}
        request.route_args['exception'] = exception
        handler = self.handler(request, response)
        return handler.get()


class Handle404(webapp2.RequestHandler):
    def get(self):
        self.response.write('<a href="javascript:window.history.go(-1);"><img src="/b/img/error/404.jpg" alt="Sorry, I could not find this page ;(" /></a><br/>')
        self.response.write('Sorry, I could not find this page ;(')


#def handle_404(request, response, exception):
#    logging.exception(exception)
#    response.write('Could not find this page :(')
#    response.set_status(404)


def handle_500(request, response, exception):
    logging.exception(exception)
    response.write('A server error occurred :(')
    response.set_status(500)


directories = ('app', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'home', 'welcome', 'lander','smb_lander')
# single slash (e.g., /g/index.html or /g/view_camp etc.)
index_routes = [webapp2.Route('/<directory:%s>/<:.*>' % directory,
                              RenderIndexHandler)
                for directory in directories]
# # just directory (e.g., /g)
index_routes += [RedirectRoute('/<directory:%s>' % directory,
                               redirect_to='/%s/' % directory)
                 for directory in directories]

app = webapp2.WSGIApplication(index_routes + [
    # this will use the default directory
    ('/', RenderIndexHandler, 'lander'),
    (r'/biz/(.*)', Business),
    ('/biz', Business),
], debug=True)
app.error_handlers[404] = Webapp2HandlerAdapter(Handle404)
app.error_handlers[500] = handle_500


