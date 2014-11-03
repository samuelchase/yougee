import logging
import json
import webapp2
import urllib
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore
from google.appengine.api import images


def display_message(self, status, data):
    params = {
        'status': status,
        'data': data
    }
    self.response.write(json.dumps(params))


class MediaDelete(webapp2.RequestHandler):

    def get(self):
        blob_key = self.request.get('blob_key')
        blobstore.delete(blob_key)
        status = 'success'
        data = 'key :' + blob_key
        display_message(self, status, data)


class MediaUpload(blobstore_handlers.BlobstoreUploadHandler):

    def post(self):
        upload_files = self.get_uploads()
        blob_info = upload_files[0]
        logging.info(upload_files)
        status = 'success'
        data = '/media/cdn/' + str(blob_info.key())
        display_message(self, status, data)


class MediaCDN(blobstore_handlers.BlobstoreDownloadHandler):

    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)


class MediaUrl(webapp2.RequestHandler):

    def get(self):
        upload_url = blobstore.create_upload_url('/media/upload')
        status = 'success'
        data = upload_url
        display_message(self, status, data)


class MediaBannerImg(webapp2.RequestHandler):
    def get(self, blob_key):
        url = images.get_serving_url(blob_key, size=None, crop=False, secure_url=None)
        self.response.write(url)

class MediaDeleteServingUrl(webapp2.RequestHandler):
    def get(self, blob_key):
        url = images.delete_serving_url_async(blob_key, rpc=None)
        self.response.write(url)



