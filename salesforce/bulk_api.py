"""
Handles access to the Salesforce Bulk API

Bulk API requires a mixture of SOAP (for the session) and REST (for actual bulk
uploading) and is totally asynchronous (i.e., when you upload a batch, the
request returns immediately, so you need to make a request later to see if it
were successful)

Overview of the API flow:

* Make a session via the login SOAP (use the Session.from_login() method)
* Use Session to initialize a Job (need 1 job per Salesforce object) [GET]
* Create batches by uploading Nearwoo data to Salesforce with a csv generated
  by salesforce.converters (max of 2,000 records per batch) [POST]
* Close job to start processing of batches. [GET]
* Use Batch object to check for errors (which return as a csv file). [GET]
  (just get them from the Job).

Instantiating Batch and Job objects doesn't cause any requests (so, if, for
example, you have a job_id, you can create a Job object and use that to get at
Batches, etc.)
"""
import csv
import functools
import logging
import os
import urlparse

import requests

import BeautifulSoup
# third party libraries required: requests
# need to download this from Salesforce
logger = logging.getLogger("nearwoo.salesforce.bulk_api")
SALESFORCE_DIRECTORY = os.path.dirname(__file__)
DEFAULT_LOGIN_URL = 'https://login.salesforce.com/services/Soap/u/29.0'


XML_APPLICATION = "application/xml; charset=UTF-8"
CSV_TYPE = "text/csv; charset=UTF-8"


class Session(object):

    """encapsulates session information needed for authentication
    (set auto_connect=False if you don't want the session to connect when it's
    instantiated)

    Public properties:
    * auth_headers - add this to headers to validate Rest API / Bulk API
      request
    * session_id - session id (but not really necessary, use auth_headers)
    * sf_server - server url to use with salesforce requests

    Semi-Public properties:
    * client - suds Client object
    """
    login_response = None
    client = None

    def __init__(self, session_id, sf_server):
        """Create a session object, need to call connect to instantiate it."""
        self.session_id = session_id
        self.sf_server = sf_server

    @classmethod
    def from_login(cls, username, password, url=DEFAULT_LOGIN_URL):
        # thanks to Brightcove Salesforklift for the brilliant idea to just
        # copy out the envelope for login and not need a SOAP library (suds
        # isnice though)
        body = (
            # You might ask - Jeff, why haven't you pretty formatted this?
            # Jeff answers: because Salesforce can be sensitive to whitespace
            # *EVEN IF IT DOESN'T CHANGE XML MEANING*
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<env:Envelope xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
            ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">'
            '<env:Body>'
            '<n1:login xmlns:n1="urn:partner.soap.sforce.com">'
            '<n1:username>{username}</n1:username>'
            '<n1:password>{password}</n1:password>'
            '</n1:login>'
            '</env:Body>'
            '</env:Envelope>'
            ).format(username=username, password=password)
        headers = {'Content-Type': 'text/xml;charset=UTF-8',
                   'SOAPAction': 'login'}
        response = requests.post(url, body, headers=headers)
        soap = BeautifulSoup.BeautifulSOAP(response.content)
        sess_url_parsed = urlparse.urlparse(soap.serverurl.text)

        session_id = soap.sessionid.text
        sf_server = sess_url_parsed.netloc
        session = cls(session_id, sf_server)
        return session

    @property
    def auth_headers(self):
        "headers needed for Salesforce to accept request"
        return {'X-SFDC-Session': self.session_id}

    def __repr__(self):
        return "%s(session_id=%r, sf_server=%r)" % (
            type(self).__name__,
            self.session_id, self.sf_server)


class Job(object):

    """Handler for a single Bulk API Job. Doesn't allow multiple object types
    in a request, even though the Salesforce API is okay with it.

    Parameters
    ----------
    session : salesforce.Session
        single session object, needs to provide ``sf_server`` and
        ``auth_headers`` to be used for future requests.
    sf_object : str
        Salesforce object type that we're going to be manipulating.
    external_id : str
        *Required* for upsert - Salesforce field name for external id
    operation : str {'upsert', 'insert', 'update'} (default upsert)
        Operation type (upsert means insert or update)
    job_id : str
        Job ID returned from Salesforce request (if you pass this, the job
        won't make a new request to open itself).

    Keeps track of all batches submitted under the job.

    Example
    -------

    >>> session = Session.from_login(username, password) # connects to get url
    >>> job = Job(session, 'Contact', 'upsert', 'Advertiser_Key__c')
    >>> job.open() # makes request to salesforce

    If you pass a job_id, then no request will be made on open().
    """
    #: Salesforce has many different API versions, this is the one active when
    #: when we started using the Bulk API
    API_level = "29.0"
    _log_request_types = set([XML_APPLICATION])
    closed = False

    def __init__(self, session, sf_object, operation='upsert',
                 external_id=None, job_id=None):
        self.session = session
        self.external_id = external_id
        if not self.session.session_id:
            raise ValueError("Need to pass connected session!")
        # mapping of batch_id to Batch object
        self.batches = {}
        url = "https://{sf_server}/services/async/{API_level}".format(
            sf_server=self.session.sf_server,
            API_level=self.API_level)
        self.base_url = url
        self.sf_object = sf_object
        self.operation = operation
        self.job_id = job_id

    def _request(self, url, payload=None, method="GET", content_type=None,
                 headers=None,
                 expected_response_type=None, **kwargs):
        """adds headers, makes request and raises errors on bad status
        code/response type

        Returns Google API Response Object (from urlfetch)"""
        headers = headers or {}
        headers.update(self.session.auth_headers)
        if content_type is not None:
            headers.setdefault('Content-Type', content_type)
        logger_prefix = "SF:%s:(%s)" % (method, url)
        logger.info(logger_prefix)
        if method == 'POST':
            response = requests.post(url, payload, headers=headers, **kwargs)
        elif method == 'GET':
            response = requests.get(url, headers=headers, **kwargs)
        else:
            raise ValueError("Invalid method: %s" % method)
        if content_type in self._log_request_types or content_type is None:
            logger.debug("%s\nREQUEST:%s" % (logger_prefix, payload))
        logger.debug("%s:RESPONSE status_code: %s\ncontent:%s" %
                     (logger_prefix, response.status_code,
                      response.content))
        if (response.status_code // 200) != 1:
            logger.debug('Exception producing response: %s' %
                         response.content)
            if 'xml' in response.headers.get('Content-Type', ''):
                soap = BeautifulSoup.BeautifulSOAP(response.content)
                if hasattr(soap, 'exceptioncode'):
                    raise SFResponseError(soap)
            raise ValueError("Bad response. Expected 200-level, got %d" %
                             response.status_code)
        # sometimes content types is None, we're always going to allow it
        resp_ct = response.headers.get('Content-Type', None)
        # e.g. xml in application/xml etc.
        if resp_ct is not None and expected_response_type not in resp_ct:
            raise ValueError("Didn't get expected response type: %r not in %r"
                             % (expected_response_type, resp_ct))
        return response

    def xml_request(self, url, payload=None, method="GET", content_type=None,
                    headers=None, **kwargs):
        """Handles requests that should return xml. Parses and returns xml
        content.

        Returns
        -------
        soap, response : (BeautifulSOAP, Google Response object)"""
        try:
            response = self._request(url, payload=payload, method=method,
                                     content_type=content_type,
                                     headers=headers,
                                     expected_response_type='xml', **kwargs)
        except Exception:
            logger.exception("Failed to load url: %s" % url)
            raise
        return BeautifulSoup.BeautifulSOAP(response.content), response

    def csv_request(self, url, payload=None, method="GET", content_type=None,
                    headers=None, content_only=False, **kwargs):
        """Makes sync request that expects csv response, handles errors and
        parses response.

        Returns
        -------
        reader, response : tuple
            where reader is a csv.DictReader and response is the Google
            Response Object"""
        try:
            response = self._request(url, payload=payload, method=method,
                                     content_type=content_type,
                                     headers=headers,
                                     expected_response_type='csv', **kwargs)
        except Exception:
            logger.exception("Failure with url: %s" % url)
            raise
        if content_only:
            return response.content, response

        import StringIO
        reader = csv.DictReader(StringIO.StringIO(response.content))
        return reader, response

    request = functools.partial(_request, expected_response_type=None)

    def get_all_batch_states(self):
        url = "{base_url}/job/{job_id}/batch".format(
            base_url=self.base_url,
            job_id=self.job_id)
        soap, _ = self.xml_request(url, method="GET")
        return soap

    def open(self):
        "Creates job (but skips if already created"
        if self.closed:
            raise ValueError("Can't re-open closed job")
        if self.job_id is not None:
            pass
        else:
            self._initialize_job()

    def _initialize_job(self):
        """Makes request to initialize job."""
        if self.external_id:
            external_id_xml = (
                "<externalIdFieldName>%s</externalIdFieldName>" %
                self.external_id)
        else:
            external_id_xml = ''
        url = "{base_url}/job/".format(base_url=self.base_url)
        # sometimes Salesforce screws up if there's spaces in the xml
        data = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">'
                '<operation>{operation}</operation>'
                '<object>{sf_object}</object>'
                '{external_id_xml}'
                '<contentType>CSV</contentType>'
                '</jobInfo>'
                ).format(operation=self.operation, sf_object=self.sf_object,
                         external_id_xml=external_id_xml)
        job_soap, _ = self.xml_request(url, data, method="POST",
                                       content_type=XML_APPLICATION)
        self.job_id = job_soap.id.text
        return job_soap

    def close(self):
        "Closes job (and initiates processing of Salesforce side)"
        url = "{base_url}/job/{job_id}/".format(base_url=self.base_url,
                                                job_id=self.job_id)
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">'
            '<state>Closed</state>'
            '</jobInfo>'
        )
        soap, response = self.xml_request(url, data, method="POST",
                                          content_type=XML_APPLICATION)
        try:
            self.closed = soap.state.text == "Closed"
        except:
            pass
        return soap, response

    def __enter__(self, *args, **kwargs):
        self.open()
        return self

    def __exit__(self, *args, **kwargs):
        self.close()
        return self

    def add_batch(self, data):
        "add data to this batch"
        if self.closed:
            raise ValueError("Can't add batch to closed Job")
        if not self.job_id:
            self.open()
        batch = Batch(self, data=data)
        batch_id, _ = batch.submit()
        self.batches[batch_id] = batch
        return batch

    def get_batch(self, batch_id):
        "Return batch connected to *this* job with given batch_id"
        if batch_id not in self.batches:
            self.batches[batch_id] = Batch(self, batch_id=batch_id)
        return self.batches[batch_id]

    def __repr__(self):
        attrs = ", ".join(['%s=%r' % (attr, getattr(self, attr))
                           for attr in ('sf_object', 'job_id', 'operation', 'session')])
        return "%s(%s)" % (type(self).__name__, attrs)


class Batch(object):

    """
    Single batch (to be) submitted to the Salesforce API
    """
    _state = None
    completed = None
    last_response = None
    status = None
    closed = None
    failed = None
    failed_records = None
    number_records = None

    def __init__(self, job, data=None, batch_id=None):
        self.job = job
        self.batch_id = batch_id
        self.data = data
        self.base_url = "{job_base_url}/job/{job_id}".format(
            job_base_url=self.job.base_url,
            job_id=self.job.job_id)

    def get_state(self):
        """Returns state of request (uses cached request if completed)"""
        # careful of circular reference with completed property
        if not self.completed:
            url = "{base_url}/batch/{batch_id}".format(
                base_url=self.base_url,
                batch_id=self.batch_id)
            soap, _ = self.xml_request(url, method="GET")
            self._state = soap
            status = soap.state.text
            self.completed = status == "Completed"
            failed_records = soap.numberrecordsfailed.text
            self.number_records = int(soap.numberrecordsprocessed.text)
            self.failed = status == "Failed" or int(failed_records) > 0
            self.closed = self.completed or self.failed
            self.failed_records = failed_records
        return self._state

    def xml_request(self, *args, **kwargs):
        "intermediary for job so that response can be saved"
        response = self.job.xml_request(*args, **kwargs)
        self.last_response = response
        return response

    def csv_request(self, *args, **kwargs):
        "intermediary for job so that response can be saved"
        response = self.job.csv_request(*args, **kwargs)
        self.last_response = response
        return response

    @property
    def state(self):
        "returns last fetched state"
        if not self.closed:
            self._state = self.get_state()
        return self._state

    def get_results(self, content_only=False):
        url = "{base_url}/batch/{batch_id}/result".format(
            base_url=self.base_url,
            batch_id=self.batch_id)
        reader, _ = self.csv_request(url, method="GET",
                                     content_only=content_only)
        return reader

    def submit(self, data=None, content_type=CSV_TYPE):
        data = data or self.data
        url = "{base_url}/batch/".format(base_url=self.base_url)
        batch_soap, _ = self.xml_request(url, data, method='POST',
                                         content_type=content_type)
        self.batch_id = batch_soap.id.text
        del self.data
        return self.batch_id, batch_soap

    def __repr__(self):
        return "{klass}(batch_id={batch_id!r}, job={job!r})".format(
            klass=type(self).__name__,
            job=self.job,
            batch_id=self.batch_id)


class SFResponseError(Exception):

    def __init__(self, soap):
        self.exception_code = soap.exceptioncode.text
        self.exception_message = soap.exceptionmessage.text
        self.soap = soap
        Exception.__init__(self, str(self))

    def __str__(self):
        return "%s: %s" % (self.exception_code, self.exception_message)

    def __repr__(self):
        attrs = ", ".join("%s=%r" % (attr, getattr(self, attr, None))
                          for attr in ('exception_code', 'exception_message'))
        return "%s(%s)" % (type(self).__name__, attrs)
