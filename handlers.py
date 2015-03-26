
import models

class DemoRequest(webapp2.RequestHandler):
    def get(self, key):
        dr = models.DemoRequest.urlsafe_get(key)
        result = json.dumps(dr.to_dict())
        self.response.out.write(result)

    def post(self):
        email = self.request.get('email')
        if email:
            dr = models.DemoRequest.gql('where email = :1', email).get()
            if not dr:
                dr = models.DemoRequest()
                dr.email = email
                dr.put()
            else:
                self.response.out.write('email exists')
        else:
            self.response.out.write('no email found')

class Business(webapp2.RequestHandler):
    def get(self, attr):
        result = []
        if attr == 'all':
            businesses = models.Business.query().fetch(1000)
        else:
            businesses = models.Business.gql('where ' + attr + '= :1', True).fetch(1000)
        for b in businesses:
            result.append(b.to_dict())

        self.response.out.write(json.dumps(result))

    def post(self):
        data = json.loads(self.request.body)

        if data.get('lat_lng') != None:

            # save lat_lng for later
            biz_key = data['biz_key']
            lat_lng = data['lat_lng']

            logging.error(lat_lng)
            logging.error(biz_key)

            biz = models.Business.urlsafe_get(biz_key)
            biz.lattitude = lat_lng[0]
            biz.longitude = lat_lng[1]
            biz.put()

            self.response.out.write(biz.to_json())
            return

        self.response.out.write(business.to_json())

        