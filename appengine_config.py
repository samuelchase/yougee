from google.appengine.api import users


def webapp_add_wsgi_middleware(app):
    import gae_mini_profiler.profiler
    # from google.appengine.ext.appstats import recording
    # app = recording.appstats_wsgi_middleware(app)
    app = gae_mini_profiler.profiler.ProfilerWSGIMiddleware(app)
    return app


appstats_SHELL_OK = True


def gae_mini_profiler_should_profile_production():
    import wootils
    return wootils.is_superadmin(users.get_current_user())

def appstats_should_record(env):
  from gae_mini_profiler.config import should_profile
  if should_profile():
      return True
  return False
