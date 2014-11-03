import cStringIO as StringIO
import csv
import json


from wootils import iterate
from base_handlers import CSVServer
import models


def to_ndb_query(model, filters=None):
    """ Each filter is a tuple (field_name, operator, value)
    to be passed to a GQL Query. The first two elements 
    need to be strings. """
    if filters is None or not filters:
        query = model.query()
    else:
        qs = []
        values = []
        for i, f in enumerate(filters, 1):
            field_name, operator, value = f
            qs.append(' '.join([field_name, operator, ':' + str(i)]))
            values.append(value)
        qs = 'where ' + ' and '.join(qs)
        query = model.gql(qs, *values)
    return query


def query_to_csv(query, model):
    out = StringIO.StringIO()
    writer = csv.DictWriter(out, model._ordered_property_list)
    writer.writeheader()
    for entity in iterate(query):
        writer.writerow(entity.to_ascii_dict())
    return out.getvalue()


class CampaignEditReporter(CSVServer):

    def get(self, edit_kind, tdelta_value):
        edit_kinds = ['create', 'downgrade',
                      'upgrade', 'shuffle', 'supercharge']
        if not edit_kind in edit_kinds:
            msg = 'edit_kind needs to be one of ' + ', '.join(edit_kinds)
            raise ValueError(msg)
        tdelta = tdelta_value.split('_')[0] + '_tq'
        query = models.CampaignEdit.gql(
            'where kind = :1 and ' + tdelta + ' = :2',
            edit_kind, tdelta_value)
        csv_str = query_to_csv(query, models.CampaignEdit)
        fn = '_'.join(['downgrades', tdelta_value])
        self.serve_csv(csv_str, filename=fn)


class NDBReporter(CSVServer):

    def post(self):
        from mapreduce.util import handler_for_name
        data = json.loads(self.request.body)
        model_name = data['model']
        filters = data.get('filters', None)
        model = handler_for_name(model_name)
        query = to_ndb_query(model, filters=filters)
        csv_str = query_to_csv(query, model)
        self.serve_csv(csv_str, filename='report.csv')


# for remote / interactive shell
#tdelta_value = 'month_12_2013'
#tdelta = tdelta_value.split('_')[0] + '_tq'
# query = models.CampaignEdit.gql(
#    'where kind = :1 and ' + tdelta + ' = :2',
#    'downgrade', tdelta_value)
#csv_str = ndb_reporter.query_to_csv(query, models.CampaignEdit)
#fn = '_'.join(['downgrades', tdelta_value])
