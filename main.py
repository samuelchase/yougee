#!/usr/bin/env python
from google.appengine.api import urlfetch
from google.appengine.api import users
import webapp2
import logging
import json
import os


from webapp2_extras import jinja2
from webapp2_extras.routes import RedirectRoute
import gae_mini_profiler.templatetags


jinja2.default_config['template_path'] = os.path.join(
    os.path.dirname(__file__),
    'server_templates'
)
jinja2.default_config['globals'] = {
    'profiler_includes': gae_mini_profiler.templatetags.profiler_includes
}

if not jinja2.default_config['environment_args']:
    jinja2.default_config['environment_args'] = {}


jinja2.default_config['environment_args'].update(dict(
    # need to not collide with angular template syntax
    variable_start_string="{!",
    variable_end_string="!}"
))



class RenderIndexHandler(webapp2.RequestHandler):

    """Renders the single static-ish index.html that then sets up the AngularJS
    code that powers the site. We use jinja to render it so we can include the
    profiler from gae_mini_profiler"""
    def get(self, directory='yougee'):
        # force adnucleus.io to redirect to /nucleus/site/index.html
        if 'adnucleus.io' in self.request.host:
            self.redirect('/nucleus/site/index.html')
            return
        if directory == 'lander':
            logging.warning(directory)
            self.redirect('/lander/index.html')
            return

        if directory == 'yougee':
            logging.warning(directory)
            self.redirect('/yougee/index.html')
            return

        if directory == 'smb_lander':
            self.redirect('/smb_lander/smb_lander.html')
            logging.error('IN SMB LANDER')
            return

        logging.info("Rendering %s" % directory)
        j2 = jinja2.get_jinja2()
        # Jinja needs path delimited by forward slash
        rv = j2.render_template('%s/index.html' % directory)
        self.response.write(rv)



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
], debug=True)
app.error_handlers[404] = Webapp2HandlerAdapter(Handle404)
app.error_handlers[500] = handle_500


