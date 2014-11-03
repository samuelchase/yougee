"""
Salesforce API Integration

Converts App Engine db models to dicts of Salesforce object key: data

Side notes on Salesforce:

    * Relationship fields are: FieldName.Object_Field, and custom fields get
      `__r` suffix rather than `__c` (e.g.,
      Account.Advertiser_Key__c or Campaign__r.Campaign_Key__c)
    * Custom fields are named __c as a suffix.

Relationships:

Not dependent: Promo, Account
Dependencies:
    * Campaign --> Account, Promo
    * Contact --> Account
    * Invoice --> Campaign, Account
Upload ordering:
    1. Account ("Account"), Promo ("Promo"), Partner ("Partner")
    2. Contact ("Contact")
    3. Campaign ("Campaign")
    4. Neighborhood Changes ("Neighborhood")
    5. Invoice ("Invoice")
"""
import pytz
from cStringIO import StringIO
import csv
import jcloudstorage as gcs
import datetime
import logging
import salesforce.bulk_api
import secrets
from models import NDBWrapper

# On str vs. unicode:
# ------------------
# Everything stays as bytes (str) so we can pass it to csv

__version__ = "1.0"

BUCKET = 'salesforce-bucket'
# Salesforce says up to 10K but I'd rather be conservative
MAX_RECORDS_PER_FILE = 8500
logger = logging.getLogger('nearwoo.salesforce.mapreduce')

# Salesforce API defines '#N/A' as Null, but it's a lie.
NULL = ""

# Salesforce date format - assumes UTC: YYYY-MM-DDThh:mm:ssZ, e.g.:
# 1999-01-01T23:01:01Z
SF_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def make_session():
    session = salesforce.bulk_api.Session.from_login(
        secrets.SALESFORCE_USERNAME,
        secrets.SALESFORCE_PASSWORD + secrets.SALESFORCE_SECURITY_TOKEN)
    return session

# Converter function factories (all get attributes of objects)
# ---------------------------
# Note that these all yield (utf-8 compliant) *bytes* so that you don't hit
# str/unicode issues when generating data.


def convert_datetime(attr, from_tz=None, to_tz=None):
    "Factory for datetime converter function"
    from_tz = from_tz or pytz.utc
    def dt_wrapper(obj):
        dt = getattr(obj, attr)
        if dt:
            if to_tz:
                dt = from_tz.localize(dt)
                dt = dt.astimezone(to_tz).replace(tzinfo=None)
            # Assuming UTC: YYYY-MM-DDThh:mm:ssZ, e.g.: 1999-01-01T23:01:01Z
            dt = dt.strftime(SF_DATE_FORMAT)
            return bytes(dt)
    return dt_wrapper


def make_float(attr, digits=2):
    "convert to float string with specified number of digits (returns bytes)"
    format = "%.{digits}f".format(digits=digits)

    def float_converter(obj):
        n = getattr(obj, attr)
        return format % n if n is not None else None
    return float_converter


def make_int(attr, format="%d"):
    "convert to int string (returns bytes)"
    format = str(format)

    def int_converter(obj):
        n = getattr(obj, attr)
        return format % n if n is not None else None
    return int_converter


def make_bool(attr, default=False, keep_none=True):
    "converts to bool with default of False"
    def bool_getter(obj):
        res = getattr(obj, attr, None)
        if res is not None or not keep_none:
            return str(bool(res))
        else:
            # be explicit, okay kids?
            return None
    return bool_getter


def get_key(obj):
    "Key --> Urlsafe for db and ndb"
    key = getattr(obj, "key")
    # db
    if callable(key):
        return str(key())
    # ndb
    else:
        return str(key.urlsafe())


def get_length(attr, format="%d"):
    format = str(format)

    def length_converter(obj):
        item = getattr(obj, attr)
        return format % len(item) if item is not None else None
    return length_converter


def bytes_attrgetter(attr, encoding='utf-8'):
    """returns func that gets ``attr`` and encodes it to ``encoding``.
    (all string data in app engine comes back as unicode).

    This *assumes* that everything ought to be utf8 (or specified encoding),
    but no better way to decide on an encoding.
    """
    if not isinstance(attr, str):
        raise ValueError("All attributes must be str! Got: %s" % attr)

    def unicode_to_bytes_getter(obj):
        elem = getattr(obj, attr, None)
        if elem is not None:
            # if any attr is actually bytes AND it doesn't fit in unicode,
            # then this will cause a UnicodeDecodeError here.
            elem = elem.encode(encoding)
        return elem
    unicode_to_bytes_getter.__name__ = "{attr}_uncode_to_bytes_getter".format(
        attr=attr)
    return unicode_to_bytes_getter


def mapper_factory(mapper_name, attr_conversions,
                   sf_object, entity_kind, external_id):
    """Creates a mapping function and gives it some metadata to make it easier
    to use. attr_conversions are given as two-tuples rather than dict so that
    field order can be reconstructed.

    Strings are interpreted as attr to get and converted into attrgetter funcs.

    Function yields an appropriate csv line.
    """
    converter_funcs = [(k, (v if callable(v) else bytes_attrgetter(v)))
                       for k, v in attr_conversions]

    def conversion_mapper(obj):
        f = StringIO()
        writer = csv.writer(f)
        row = [convert_attr(obj) for _, convert_attr in converter_funcs]
        # need to swap for Salesforce
        row = [elem if elem is not None else NULL for elem in row]
        # swap out None for Salesforce null
        writer.writerow(row)
        val = f.getvalue()
        f.close()
        yield sf_object, val

    conversion_mapper.__name__ = str(mapper_name)

    fields = [field for field, _ in attr_conversions]
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(fields)
    csv_header = f.getvalue()
    f.close()
    mapper_json = dict(
        entity_kind=entity_kind,
        sf_object=sf_object,
        external_id=external_id,
        fields=fields,
        __qualname__='salesforce.converters.%s' % mapper_name,
        csv_header=csv_header,
        version=__version__,
    )
    for attr, value in mapper_json.items():
        setattr(conversion_mapper, attr, value)
    conversion_mapper.json = mapper_json
    return conversion_mapper


def csv_reducer(key, csv_strs):
    "reducer that yields lines to file"
    logger.info("%s: %d items" % (key, len(csv_strs)))
    for csv_str in csv_strs:
        yield csv_str


def constant(val):
    "don't change value"
    def wrapper(obj):
        return val
    return wrapper


def with_default(attr, default):
    """Try to get attr but if empty use default.
    (e.g., Salesforce *requires* name field)"""
    def default_setting_wrapper(obj):
        att = getattr(obj, attr) or default
        return att.encode('utf8')
    return default_setting_wrapper

contact_mapper = mapper_factory(
    'contact_mapper',
    [
        # Salesforce requires a last name, we don't split on name, so we're
        # just pushing it in here
        ("LastName",  with_default('name', '<NO NAME ENTERED>')),
        ("Phone",  'business_phone'),
        ("Contact_Type__c",
         lambda adv: "advertiser (partner)" if adv.wholesale else "partner"),
        # Salesforce defined field
        ("Email",  'business_email'),
        ("Advertiser_Email__c",  'email'),
        ("Advertiser_Key__c",  get_key),
        ("Account.Advertiser_Key__c",  get_key),
        ("Partner__r.Partner_Id__c",  'partner_id'),
        ("Rep__r.Promo_Id__c", "promo_id")
    ],
    sf_object='Contact',
    entity_kind='models.Advertiser',
    external_id='Advertiser_Key__c')

# models.Advertiser
account_mapper = mapper_factory(
    'account_mapper',
    [
        ("of_Campaigns__c",  make_int("active_campaign_count")),
        ("Create_Date__c",  convert_datetime("created")),
        ("Modified_Date__c",  convert_datetime("modified")),
        ("Status__c",  constant(u"Live Advertiser")),
        ("Lead_Source__c",  with_default('partner_id', u'NearWoo')),
        ("Advertiser_Key__c",  get_key),
        ("Advertiser_Email__c",  "email"),
        ("Partner__r.Partner_Id__c", "partner_id"),
        ("Name", with_default("name", u"<NOACCOUNTNAME>")),
        ('Account_Link__c', 'url'),
        ('Dash_Link__c', 'dash_url'),
        ('Block_Points__c', make_int('block_points')),
    ],
    sf_object='Account',
    entity_kind='models.Advertiser',
    external_id='Advertiser_Key__c'
)


# models.Invoice
invoice_mapper = mapper_factory(
    'invoice_mapper',
    [
        # this would be the external ID, not clear if I can use this for
        # master/parent relationships or whatever
        # urlsafe campaign key
        ("Campaign__r.Campaign_Key__c",  'campaign_key'),
        ("Charge_Date__c",  convert_datetime('date_created')),
        ("Charge_Amount__c",  make_float('charge_amount')),
        ("Invoice_Key__c",  get_key),
        ("Name",
         lambda invoice: (invoice.transaction_id or
                          invoice.stripe_id or
                          invoice.stripe_id_search or
                          '<NO TRANSACTION ID FOUND>').encode('utf8')),
        ("Invoice_Type__c",  'invoice_type'),
        ("Block_points_applied__c",  make_int('block_points_applied')),
    ],
    sf_object='Invoice__c',
    entity_kind='models.Invoices',
    external_id='Invoice_Key__c',
)


def get_campaign_type(campaign):
    if campaign.wholesale:
        campaign_type = "Partner"
    # elif campaign.neighborhood_ct == 1 and not campaign.home_price:
    #     campaign_type = "Free"
    # elif campaign.neighborhood_ct > 1:
    #     campaign_type = "Paid"
    elif campaign.neighborhood_ct > 0:
        campaign_type = "Paid"
    else:
        campaign_type = None
    return campaign_type


def nested_getter(attr, child_attr):
    if not callable(child_attr):
        child_func = bytes_attrgetter(child_attr)
    else:
        child_func = child_attr

    def wrapper(obj):
        child = getattr(obj, attr)
        if child:
            return child_func(child)
    wrapper.__name__ = "%s_getter" % attr
    return wrapper


def get_name_or_yelp_name(camp):
    name = camp.name
    if not name:
        name = camp.yelp.name if camp.yelp else None
    return (name or '<NO NAME ENTERED>').encode('utf8')


def multistring_to_csv(attr):
    "converts array of unicode values to bytes csv"
    def multi_to_csv(obj):
        data = getattr(obj, attr, None)
        if not data:
            return
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow([elem.encode('utf8') for elem in data])
        res = f.getvalue()
        f.close()
        return res
    return multi_to_csv


def get_clean_zipcode(camp):
    zipcode = camp.zipcode
    if zipcode == 'none':
        return None
    if zipcode.startswith('zipcode_'):
        split = zipcode.split('_')
        code = split[-1]
        return bytes(code.strip())


campaign_mapper = mapper_factory(
    'campaign_mapper',
    [
        # PERF: This will slow stuff down.
        ("Name", get_name_or_yelp_name),
        ("Selected_Neighborhoods__c", make_int("neighborhood_ct")),
        ("Amount_Spent__c", make_float("amount_spent")),
        ("Amount_Subscribed__c", make_float("amount_subscribed")),
        ("Account__r.Advertiser_Key__c",  'advertiser_key'),
        ("Partner__r.Partner_Id__c",  'partner_id'),
        ("Rep__r.Promo_Id__c",  'promo_id'),
        ("End_Date__c", convert_datetime('end_date')),
        ("Start_Date__c", convert_datetime('start_date')),
        ("Zipcode__c", get_clean_zipcode),
        ("Partner_Promo_Category__c",  'partner_promo_category'),
        # TODO: Consider going back to having a promo object, but for now not
        #       super useful to do so (and more complicated).
        ("Absolute_Discount__c", nested_getter('promo',
                                               make_float(
                                                   'absolute_discount'))),
        ("Percent_Discount__c", nested_getter('promo',
                                              make_float(
                                                  'percent_discount'))),
        ("Discount_Is_Recurring__c", nested_getter('promo',
                                                   make_bool(
                                                       'is_recurring'))),
        ("Campaign_Type__c",  get_campaign_type),
        ("Campaign_Key__c", get_key),
        ("Charge_Day__c", make_int('charge_day')),
        ("Created__c", convert_datetime("date_created")),
        ("Completed_Campaign_Creation__c", make_bool("completed")),
        ("Campaign_Link__c", "url"),
        ("Dash_Link__c", "dash_url"),
        ("Billing_Period__c", make_int("billing_period")),
        ("Next_Billing_Date__c", convert_datetime("next_charge_date",
                                                  to_tz=pytz.timezone('America/Los_Angeles'))),
        ("Last_Bill_Date__c", convert_datetime("last_charge_date",
                                               to_tz=pytz.timezone('America/Los_Angeles'))),
        ("Home_Hood_Price__c", make_float("home_price")),
        ("Additional_Hood_Price__c", make_float("retail_price")),
        ("Campaign_Category__c", "business_category"),
        ("Total_View_Bucket__c", make_int("max_views")),
        ("All_Time_Views__c", make_int("views")),
        ("All_Time_Clicks__c", make_int("clicks")),
        ("Views_This_Month__c", make_int("monthly_views")),
        ("Clicks_This_Month__c", make_int("monthly_clicks")),
        ("Monthly_Views_Subscribed__c", make_int("total_adamounts")),
        ("Is_Recurring_Campaign__c", make_bool("is_recurring")),
        ("Paused__c", make_bool("paused")),
        ("Next_Views_Recharge__c", convert_datetime("next_recharge_date")),
        ("Calculated_Amount_Subscribed__c",
            make_float("adamounts_expected_amount_subscribed")),
        ("Competitor_Lockout__c", make_bool("lock_out_competition")),
    ],
    sf_object='Campaign__c',
    entity_kind='models.NearWooCampaignDS',
    external_id='Campaign_Key__c')

# Not using this for now, but could use it
# promo_mapper = mapper_factory(
#         'promo_mapper',
#         [
#             ("Partner_Promo_Category_Key__c", get_key)
#             ("Promo_Category__c",  'label'),
#             ("Name",  'label'),
#             ("Absolute_Discount__c",  make_float('absolute_discount')),
#             ("Is_Recurring__c",  make_bool('is_recurring', keep_none=True)),
#             ("Discount_Type__c",  'discount_type'),
#             ("Min_Block_Groups__c",  make_int('min_block_groups')),
#             ("Min_Campaign_Value__c",  make_float('min_campaign_value')),
#             ("Percent_Discount__c",  make_float('percent_discount')),
#             ("Description__c",  'description'),
#             ("Description_Short__c",  'description_short'),
#             ],
#         sf_object='Promo__c',
#         entity_kind='models.PartnerPromoCategory',
#         external_id='Partner_Promo_Category_Key__c')

neighborhood_change_mapper = mapper_factory(
    'neighborhood_change_mapper',
    [
        ("Campaign__r.Campaign_Key__c",  'camp_key'),
        ("Modified_Date__c",  convert_datetime('created')),
        ("Original_Neighborhood_Count__c",
         make_int('n_block_groups_before')),
        ("New_Neighborhood_Count__c",  make_int('n_block_groups_after')),
        ("Campaign_Edit_Key__c", get_key)
    ],
    sf_object='Neighborhood_Change__c',
    entity_kind='models.CampaignEdit',
    external_id='Campaign_Edit_Key__c')

rep_mapper = mapper_factory(
    'rep_mapper',
    [
        ("Promo_ID__c",  'promo_id'),
        ("Name",  'name'),
        ("Partner__r.Partner_Id__c",  'partner_id'),
        ("Email__c", 'email'),
    ],
    sf_object='Rep__c',
    entity_kind='models.Promotional',
    external_id='Promo_Id__c')

partner_mapper = mapper_factory(
    'partner_mapper',
    [
        ("Partner_Id__c",  'partner_id'),
        ("Name", lambda obj: (obj.name or obj.partner_id).encode('utf8')),
        ("Created__c",  convert_datetime('created')),
        ("Last_Modified__c",  convert_datetime('modified')),
        ("Wholesale__c",  make_bool('wholesale', keep_none=True)),
    ],
    sf_object='Partner__c',
    entity_kind='models.Partner',
    external_id='Partner_Id__c')


yelp_mapper = mapper_factory(
    'yelp_mapper',
    [
        ("Yelp_Json_DS_Key__c",  get_key),
        ("Campaign__r.Campaign_Key__c", 'campaign_key'),
        ("Name",  'name'),
        ("Partner__r.Partner_Id__c", 'partner_id'),
        ("Rep__r.Promo_Id__c", 'promo_id'),
        ("Created__c",  convert_datetime('date_created')),
        ("Waiting_For_Content__c", make_bool('waiting_for_content')),
        ("Build_Status__c", "rep_build_status"),
        ("Number_of_Neighborhoods__c", get_length('geoids'))
    ],
    sf_object='Initial_Campaign_Build__c',
    entity_kind='models.YelpJsonDS',
    external_id='Yelp_Json_DS_Key__c')


ordered_mappers = [
    account_mapper,
    partner_mapper,
    rep_mapper,
    contact_mapper,
    campaign_mapper,
    yelp_mapper,
    neighborhood_change_mapper,
    invoice_mapper,
]


def job_from_mapper(mapper, operation='upsert'):
    return salesforce.bulk_api.connect_to_salesforce(mapper.sf_object,
                                                     operation,
                                                     mapper.external_id)

OWNER = 'salesforce.bulk_api'

from mapreduce import base_handler
from mapreduce import mapreduce_pipeline
from google.appengine.ext import ndb


class SFPipeline(base_handler.PipelineBase):

    def run(self):
        import mapreduce.lib.pipeline
        now = datetime.datetime.utcnow()
        identifier = "%s:%s:%s" % (type(self).__name__,
                                   self.pipeline_id,
                                   now.strftime(SF_DATE_FORMAT))
        # allocate a range of IDs so we can load them after the fact
        allocated_range = SFJobDetail.allocate_ids(len(ordered_mappers))
        self.keys = range(allocated_range[0], allocated_range[1] + 1)
        assert len(self.keys) == len(ordered_mappers)
        results = []
        submission_tracker = SubmissionAlreadyRan()
        submission_tracker.identifer = identifier
        submission_tracker.pipeline_id = self.pipeline_id
        submission_tracker.put()
        for key_id, mapper in zip(self.keys, ordered_mappers):
            outfiles = yield mapreduce_pipeline.MapreducePipeline(
                '%s-%s' % (mapper.__qualname__, identifier),
                mapper.__qualname__,
                'salesforce.converters.csv_reducer',
                'mapreduce.input_readers.DatastoreInputReader',
                'mapreduce.output_writers.FileOutputWriter',
                mapper_params={'entity_kind': mapper.entity_kind},
                reducer_params={
                    'filesystem': 'gs',
                    'gs_bucket_name': BUCKET,
                    'output_sharding': 'none',
                    'mime_type': 'text/csv',
                },
                shards=100,
            )
            pipeline = yield StoreAndChunkFiles(outfiles, key_id, mapper.json,
                                                identifier, self.pipeline_id)
            results.append(pipeline)
        import gc
        gc.collect()
        with mapreduce.lib.pipeline.After(*results):
            yield SubmitEverything(self.keys, [mapper.json for mapper in
                                               ordered_mappers],
                                   str(submission_tracker.key.urlsafe()))

        def finalized(self):
            from google.appengine.api import mail
            logger.debug("Finalized called!")
            logger.debug("Keys: %s" % self.keys)
            pipeline_id = self.pipeline_id
            job_stores = SFJobDetail.query(
                SFJobDetail.pipeline_id == pipeline_id)
            job_stores = job_stores.fetch()
            link = ('http://nearwoo.appspot.com/sf/'
                    'bulk_api/pipelines/{0}'.format(pipeline_id))
            message = ['Pipeline ID: %s\nLink: %s' % (pipeline_id,
                                                      link)]
            has_failed = False
            for job_store in job_stores:
                job = job_store.build_job()
                message.append('SF_Object: %s Job: %s\n' % (job.sf_object,
                                                            job.job_id))
                for batch_id in job_store.batch_ids:
                    batch = job.get_batch(job)
                    batch.get_state()
                    message.append('\nBatch: %s' % batch.batch_id)
                    message.append('%s records processed' %
                                   batch.number_records)
                    if not batch.completed:
                        message.append('%s records failed' %
                                       (batch.failed_records))
                        has_failed = True
                    else:
                        message.append('Successfully completed!')
            message = ' '.join(message)

            mail.send_message(
                'jeff+salesforceresult@nearwoo.com',
                'jeff@nearwoo.com',
                ('%s: Salesforce Submission Finished' % ('FAILED' if has_failed
                                                         else 'OK')),
                message)


class SubmitEverything(base_handler.PipelineBase):

    def run(self, keys, lst_of_mapper_jsons, submission_tracker_key):
        tracker = ndb.Key(urlsafe=submission_tracker_key).get()
        assert len(keys) == len(lst_of_mapper_jsons), "Length of keys and json\
                not equal: %d != %d" % (len(keys), len(lst_of_mapper_jsons))
        assert len(keys) == len(ordered_mappers), "Length of keys != length of\
                mappers: %d != %d" % (len(keys), len(ordered_mappers))
        try:
            import gc
            gc.collect()
            # make sure we haven't been called multiple times
            # skip out quickly if something appears wrong
            if not tracker:
                logger.debug("No tracker found: %s" % submission_tracker_key)
                return
            if tracker.started:
                tracker.num_called += 1
                tracker.put()
                logger.debug("NOT RUNNING AGAIN: %s" % tracker)
                return
            tracker.started = True
            tracker.put()
            session = make_session()
            stores = []
            for key, mapper_json in zip(keys, lst_of_mapper_jsons):
                store = submit_job_data(key, mapper_json, session)
                stores.append(store)
            return {store.sf_object: (store.job_id, store.batch_ids,
                                      store.status) for store in stores}
        except:
            # reset so we try again
            tracker.started = False
            tracker.put()
            raise


def submit_job_data(key_id, mapper_json, session):
    "loads chunked files from job detail and submits them"
    store = ndb.Key(SFJobDetail, key_id).get()
    assert store.sf_object == mapper_json['sf_object']
    job = salesforce.bulk_api.Job(
        session,
        sf_object=mapper_json['sf_object'],
        operation='upsert',
        external_id=mapper_json['external_id']
    )
    job.open()
    try:
        store.job_id = job.job_id
        for chunked_file in store.chunked_filenames:
            with gcs.open(chunked_file, 'r') as f:
                # bytes (utf-8 encoded)
                data = f.read()
            batch = job.add_batch(data)
            store.batch_ids.append(batch.batch_id)
        store.status = SFJobDetail.UPLOADED
        try:
            logger.debug(str(job.get_all_batch_states()))
        except:
            logger.exception(store.to_dict())
        return store
    finally:
        if len(store.batch_ids) != len(store.chunked_filenames):
            store.status = SFJobDetail.APP_ENGINE_ERRORED
        else:
            store.status = SFJobDetail.UPLOADED
        logger.info("Subission: {0}-JobID{1}\nBatches:\n{2}".format(
            job.sf_object, job.job_id,
            ", ".join(store.batch_ids)))
        logger.info("Store status: %s" % store.status)
        try:
            job.close()
            store.closed = job.closed
        finally:
            store.put()


class StoreAndChunkFiles(base_handler.PipelineBase):

    """
    Takes in list of filenames from output writer, reads them in and chunks
    them into batches of 2,000 items, to later be submitted to the Salesforce
    Bulk API.
    """

    def run(self, outfiles, key_id, mapper_json, identifier, pipeline_id):
        import gc
        gc.collect()
        # we can only get to the files by yielding to this pipeline, so we pass
        # a key to this so can access in the finalized method of the original
        # pipeline
        key = ndb.Key(SFJobDetail, key_id)
        job_store = key.get() or SFJobDetail(key=key)
        if job_store.input_filenames and job_store.chunked_filenames:
            logger.debug('redoing chunking for job: %s' % job_store)
        outfiles = list(outfiles)
        assert len(outfiles) > 0, "%s:Couldn't find files for: %s" % (
            identifier, mapper_json)
        # don't do anything if we've already added the filenames
        filelist = [strip_gs_from_filename(filename) for filename in outfiles]
        job_store.input_filenames = filelist
        job_store.chunked_filenames = []
        job_store.sf_object = mapper_json['sf_object']
        job_store.pipeline_id = pipeline_id
        job_store.converter_version = __version__
        job_store.status = SFJobDetail.PENDING
        job_store.fields = mapper_json['fields']
        job_store.put()
        file_id = 0
        bucket_name = BUCKET
        base_name = '/{bucket}/{sf_object}'.format(
            bucket=bucket_name,
            sf_object=mapper_json['sf_object'])
        options = {
            'x-goog-meta-sf_object': mapper_json['sf_object'],
            'x-goog-meta-mr-identifier': identifier,
            'x-goog-meta-SFJobDetail-ID': str(key_id),
            'x-goog-meta-pipeline': pipeline_id
        }
        for chunked_batch in chunk(gcs_file_iterator(filelist)):
            filename = '{base_name}.{file_id}.{identifier}.csv'.format(
                base_name=base_name,
                file_id=file_id,
                identifier=identifier
            )
            batch_data = ''.join(chunked_batch)
            assert isinstance(batch_data, str), "need str to talk to gcs"
            file_id += 1
            # json returned as unicode, not string!
            header = mapper_json['csv_header'].encode('utf-8')
            with gcs.open(filename,
                          'w',
                          content_type='text/csv',
                          options=options) as f:
                f.write(header)
                f.write(batch_data)
                job_store.chunked_filenames.append(filename)
        assert file_id > 0, "Didn't put in any files... :-/"
        job_store.status = job_store.CHUNKED
        job_store.put()
        return job_store.to_json()


class SFJobDetail(NDBWrapper):

    """
    Details for a particular job run in Salesforce (used to then perform bulk
    uploads).
    """
    UPLOADED = 'uploaded'
    APP_ENGINE_ERRORED = 'ae-errored'
    FAILED_BATCH = 'failed'
    CHUNKED = 'chunked'
    COMPLETED = 'completed'
    PENDING = 'pending'
    job_id = ndb.StringProperty(default='')
    job_closed = ndb.BooleanProperty(default=False, indexed=False)
    batch_ids = ndb.StringProperty(repeated=True, indexed=False)
    sf_object = ndb.StringProperty(default='')
    input_filenames = ndb.StringProperty(repeated=True, indexed=False)
    chunked_filenames = ndb.StringProperty(repeated=True, indexed=False)
    output_filenames = ndb.StringProperty(repeated=True, indexed=False)
    created = ndb.DateTimeProperty(auto_now_add=True)
    status = ndb.StringProperty(default=PENDING, indexed=False)
    modified = ndb.DateTimeProperty(auto_now=True, indexed=False)
    pipeline_id = ndb.StringProperty(default='')
    fields = ndb.StringProperty(repeated=True, indexed=False)

    def to_json(self):
        return {k: getattr(self, k, None) for k in self._properties}

    def delete_all_files(self):
        for path in self.input_filenames:
            gcs.delete(path)

        for path in self.chunked_filenames:
            gcs.delete(path)

        for path in self.output_filenames:
            gcs.delete(path)

    def build_job(self):
        "return a salesforce job based on stored details"
        if not self.job_id:
            raise ValueError("Job hasn't actually been created.")
        session = make_session()
        return salesforce.bulk_api.Job(session,
                                       job_id=self.job_id,
                                       sf_object=self.sf_object,
                                       operation='upsert',
                                       )

    def request_results_and_compare(self, job):
        """Requests results from Salesforce and returns a dict of batch_id:
           list of (error_message, failed_data) [or an error message lines
           if there was a broader failure."""
        from itertools import izip
        out = {}
        for chunk_path, batch_id in zip(self.chunked_filenames,
                                        self.batch_ids):
            failed_lines = []
            total_records = 0
            failed_records = 0
            try:
                batch = salesforce.bulk_api.Batch(job, batch_id=batch_id)
                results = batch.get_results()
                input_chunk = gcs_file_iterator(chunk_path)
                # skip fields at top of file
                next(input_chunk)
                for result_line, data_line in izip(results, input_chunk):
                    total_records += 1
                    if result_line['Error']:
                        failed_records += 1
                        failed_lines.append((result_line['Error'], data_line))
                out[batch_id] = failed_lines
                self.total_records = total_records
                self.failed_records = failed_records
            except Exception as e:
                message = "%s: Failure: %s" % (batch_id, e)
                logging.exception(message)
                out.setdefault(batch_id, []).append((self.FAILED_BATCH,
                                                     message))
        return out


def count_lines(filenames, open):
    counts = 0
    filenames = filenames or []
    for path in filenames:
        with open(path, 'r') as f:
            data = f.read()
            buffer = StringIO()
            buffer.write(data)
            buffer.seek(0)
            reader = csv.reader(buffer)
            counts += sum(1 for _ in reader)
    return counts


def compare_lines(job):
    open = lambda *args, **kwargs: gcs.open(*args, **kwargs)
    in_files = job.input_filenames or []
    chunked_files = job.chunked_filenames or []
    return (job.sf_object, job.job_id, len(in_files), count_lines(in_files,
                                                                  open),
            len(chunked_files), count_lines(chunked_files, open))


def gcs_file_iterator(filenames):
    "returns lines of str (bytes)"
    if isinstance(filenames, basestring):
        filenames = [filenames]
    for filename in filenames:
        # make sure no unicode for this :P
        data_in = StringIO()
        # potentially could be more efficient by calling readline() repeatedly,
        # however that causes in-python searches for '\n' so who knows if it's
        # actually better.
        with gcs.open(filename, 'r') as f:
            data = f.read()
        data_in.write(data)
        data_in.seek(0)
        for line in data_in:
            assert isinstance(line, str)  # DELETEME
            yield line
        data_in.close()


def chunk(generator, n=MAX_RECORDS_PER_FILE):
    "type agnostic"
    out = []
    length = 0
    for line in generator:
        out.append(line)
        length += 1
        if length == n:
            yield out
            out = []
            length = 0
    if out:
        yield out


def strip_gs_from_filename(name):
    "strip off the extra /gs from the output_writer"
    if name.startswith('/gs'):
        name = name[3:]
    return name


mapper_dict = {mapper.sf_object: mapper for mapper in ordered_mappers}


def _make_csv_gen_interactive(mapper, objects, yield_fields=True):
    "convenience function for working interactively"
    if yield_fields:
        yield ",".join(mapper.fields) + "\r\n"
    func = mapper.mapper
    for obj in objects:
        key, value = next(func(obj))
        yield value


class SubmissionAlreadyRan(NDBWrapper):

    "Necessary because apparently sometimes MR calls pipelines multiple times"
    started = ndb.BooleanProperty(default=False, indexed=False)
    num_called = ndb.IntegerProperty(default=0, indexed=False)
    identifier = ndb.StringProperty(default='', indexed=False)
    # queryable
    pipeline_id = ndb.StringProperty(default='')
