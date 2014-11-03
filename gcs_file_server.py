import webapp2

import jcloudstorage as gcs
import jconfig


ANALYTICS_BY_CAMPAIGN_CATEGORY_FILENAME = 'insights.csv'


class AnalyticsByCampaignCategory(webapp2.RequestHandler):
    def get(self):
        bucket = jconfig.get_gcs_bucket_name()
        filename = '/' + bucket + ANALYTICS_BY_CAMPAIGN_CATEGORY_FILENAME
        content = read_gcs_file(filename)
        self.response.headers["Content-Type"] = 'text/csv'
        self.response.write(content)


def read_gcs_file(filename):
    gcs_file = gcs.open(filename)
    content = gcs_file.read()
    gcs_file.close()
    return content
