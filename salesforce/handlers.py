"""
Handlers for Salesforce Bulk API Integration (mostly for mapreduce ops)
"""
import logging
import os
import traceback

import webapp2
from salesforce.converters import SFPipeline, SFJobDetail, ordered_mappers
logger = logging.getLogger('nearwoo.salesforce.handlers')


def get_pipeline_path(pipeline_id):
    return '/sf/bulk_api/pipelines/%s' % pipeline_id


class StartPipelineHandler(webapp2.RequestHandler):

    def get(self):
        import jconfig
        if not jconfig.on_real_app():
            if os.environ.get('FORCE_SF_INTEGRATION'):
                pass
            else:
                self.response.write('Not running on test server')
                self.response.set_status(500)
                return
        pipeline = SFPipeline()
        pipeline.start()
        self.redirect(self.url_for('pipeline',
                                   pipeline_id=pipeline.pipeline_id))


class ListPipelinesHandler(webapp2.RequestHandler):

    def get(self):
        jobs = SFJobDetail.query().order(-SFJobDetail.created).fetch(10)
        seen = set()
        pipelines = []
        for j in jobs:
            if j.pipeline_id not in seen:
                pipelines.append(j.pipeline_id)
                seen.add(j.pipeline_id)
        self.response.write('<ul>')
        for pipeline_id in pipelines:
            link = self.url_for('pipeline', pipeline_id=pipeline_id)
            self.response.write(
                '<li><a href=' + link + '>Pipeline %s</a></li>' % pipeline_id)
        self.response.write('</ul>')


class PipelineStatusHandler(webapp2.RequestHandler):

    def get(self, pipeline_id, sf_object=None):
        try:
            pipeline = SFPipeline.from_id(pipeline_id)
            mr_path = pipeline.base_path + \
                '/status?root=' + pipeline.pipeline_id
            self.response.write(
                '<a href=' + mr_path + '>Mapreduce Console</a>')
        except Exception as e:
            self.response.write('Mapreduce not available: %s' % e)
            logger.exception("Couldn't get mapreduce pipeline in job_detail")

        # no sf object then just print link to each object
        jobs = {j.sf_object: j for j in
                SFJobDetail.query(SFJobDetail.pipeline_id ==
                                  pipeline_id).fetch()}
        self.response.write('<h2>Overall status</h2>')
        for mapper in ordered_mappers:
            this_sf_object = mapper.sf_object
            job = jobs.get(this_sf_object)
            if job is None:
                status = 'Not started'
            else:
                status = job.status
            href = self.url_for('sf_object_result', pipeline_id=pipeline_id,
                                sf_object=this_sf_object)
            self.response.write(
                '<p><a href={href}>{sf_object}</a>Status: {status}</p>'.format(
                    href=href,
                    sf_object=this_sf_object,
                    status=status)
            )
        if not sf_object:
            return

        selected_jobs = [job for job in jobs.values()
                         if job.sf_object == sf_object]
        if len(selected_jobs) != 1:
            self.response.write('Got too many jobs :-/: %s' %
                                (repr(selected_jobs)))
        else:
            try:
                job_store = selected_jobs[0]
                if not job_store.job_id:
                    self.response.write('<p>Job not created yet.</p>')
                    return
                sf_job = job_store.build_job()
                results = job_store.request_results_and_compare(sf_job)
                self.response.write('<p>Submitted %s records. %s failed.</p>' %
                                    (getattr(job_store, 'total_records', None),
                                     getattr(job_store, 'failed_records', None)
                                     ))
                self.response.write(
                    '<table><thead><tr><th>Error'
                    'Message</th><th>Data-{fields}</th></tr></thead>'.format(
                        fields=job_store.fields
                    )
                )
                self.response.write('<tbody>')
                failed_state = False
                for batch_id in results:
                    self.response.write(
                        '<tr><td colspan=2>BATCH: ' + batch_id + '</td></tr>'
                    )
                    for failure, line in results[batch_id]:
                        self.response.write(
                            '<tr><td>' + failure +
                            '</td><td>' + line + '</td></tr>'
                        )
                        if failure == SFJobDetail.FAILED_BATCH:
                            failed_state = True
                self.response.write('</tbody></table>')
                if failed_state:
                    self.response.write('<pre>')
                    try:
                        self.response.write(sf_job.get_all_batch_states())
                    except:
                        self.response.write(traceback.format_exc())
                    self.response.write('</pre>')
            except Exception:
                self.response.write(traceback.format_exc())
