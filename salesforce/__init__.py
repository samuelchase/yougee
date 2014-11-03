import webapp2
import salesforce.handlers as sf_handlers

app = webapp2.WSGIApplication([
    ('/sf/bulk_api/submit', sf_handlers.StartPipelineHandler),
    webapp2.Route('/sf/bulk_api/all',
                  handler=sf_handlers.ListPipelinesHandler,
                  name='list_jobs'),
    webapp2.Route('/sf/bulk_api/pipelines/<pipeline_id>',
                  handler=sf_handlers.PipelineStatusHandler,
                  name='pipeline'),
    webapp2.Route(
        r'/sf/bulk_api/pipelines/<pipeline_id>/sf_objects/<sf_object>',
        handler=sf_handlers.PipelineStatusHandler,
        name='sf_object_result'),
], debug=True)
