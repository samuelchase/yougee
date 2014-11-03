import jcloudstorage as gcs
import webapp2


class CSVServer(webapp2.RequestHandler):

    def serve_gcs_file(self, filename):
        gcs_file = gcs.open(filename, 'r')
        content = gcs_file.read()
        self.serve_csv(content, filename=filename)

    def serve_csv(self, csv_str, filename='no_filename.csv'):
        if not filename.endswith('.csv'):
            filename += '.csv'
        self.response.headers["Content-Type"] = 'text/csv'
        self.response.headers['Content-Disposition'] = (
            'attachment; filename=' + filename)
        self.response.write(csv_str)
