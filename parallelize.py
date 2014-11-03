# TODO: remove lib/pypeline.py TEST_MODE=True

from google.appengine.ext import db
from google.appengine.ext import ndb
from mapreduce import mapreduce_pipeline
from mapreduce import base_handler
from mapreduce import context
from mapreduce import operation
from inspect import isfunction
import logging
import pprint


from wootils import qualified_name_to_function
from wootils import function_to_qualified_name
import jconfig


"""
  TODO: add examples
        __all__
        emulate os.environ as in dev interactive shell
            to be able to use these functions from the remote shell.
"""


TEST_MODE = True


if not TEST_MODE:
    __all__ = [
        'pmap',
    ]


def pmap(mapper, query, name='pmap', shards=20):
    options = Options(mapper, shards=shards, pipeline_name=name)
    options.add_query(query)
    pipeline = GenericMapPipeline(*options.pack())
    pipeline.wrapper_options = options
    pipeline.start()
    return pipeline


def pmap_from_file(mapper, filenames, name='pmap', shards=20):
    options = Options(mapper, shards=shards, pipeline_name=name)
    options.add_files(filenames)
    pipeline = GenericMapPipeline(*options.pack())
    pipeline.wrapper_options = options
    pipeline.start()
    return pipeline


def pmapreduce(mapper, reducer, query, to_file=False,
               name='pmapreduce', shards=20):
    options = Options(mapper, shards=shards, pipeline_name=name)
    options.add_query(query)
    options.add_reducer(reducer, to_file=to_file)
    pipeline = GenericMapreducePipeline(*options.pack())
    pipeline.wrapper_options = options
    pipeline.start()
    return pipeline


def pmapreduce_from_file(mapper, reducer, filenames, to_file=False,
                         name='pmapreduce', shards=20):
    options = Options(mapper, shards=shards, pipeline_name=name)
    options.add_files(filenames)
    options.add_reducer(reducer, to_file=to_file)
    pipeline = GenericMapreducePipeline(*options.pack())
    pipeline.wrapper_options = options
    pipeline.start()
    return pipeline


class GenericMapPipeline(base_handler.PipelineBase):

    def run(self, pipeline_name, mapper, input_reader,
            mapper_params, shards):
        yield mapreduce_pipeline.MapPipeline(
            pipeline_name, mapper, input_reader, mapper_params,
            shards=shards)


class GenericMapreducePipeline(GenericMapPipeline):

    def run(self, pipeline_name, mapper, reducer, input_reader,
            output_writer, mapper_params, reducer_params, shards):
        yield mapreduce_pipeline.MapreducePipeline(
            pipeline_name, mapper, reducer, input_reader, output_writer,
            mapper_params, reducer_params, shards)
#        yield mapreduce_pipeline.MapreducePipeline(
#            pipeline_name, mapper, reducer,
#            input_reader, output_writer,
#            mapper_params=mapper_params,
#            reducer_params=reducer_params, shards=shards)


def mapper_wrapper(entity):
    ctx = context.get()
    if ctx is None:
        logging.error('could not find context')
    else:
        extras = ctx.mapreduce_spec.mapper.params['extras']
        # reconstruct function (which should be a generator)
        mapper = qualified_name_to_function(extras['mapper'])
        # make sure we run any post_get_hooks on the entity
        if hasattr(entity, '_manual_get_hook'):
            entity._manual_get_hook()
        for val in mapper(entity):
            # if the instance is a tuple, let's pass it through
            # to a presumed reducer, else let's just save it as
            # a presumed db or ndb model instance
            if isinstance(val, tuple):
                yield val
            else:
                yield operation.db.Put(val)


class QueryParser(object):

    def __init__(self, query, valid_filter_operators=['=']):
        assert isinstance(
            query, (ndb.query.Query, db.Query, db.GqlQuery))
        self._raw_query = query
        self.model = None
        self.filters = None
        self.input_reader = (
            'mapreduce.input_readers.DatastoreInputReader')
        self._add_model()
        self._add_filters(valid_filter_operators)

    def _add_model(self):
        query = self._raw_query
        if isinstance(query, (db.Query, db.GqlQuery)):
            self.model = (query._model_class.__module__ + '.' +
                          query._model_class.__name__)
        else:
            # TODO: what an ugly hack ... somehow don't hardcode
            # that we expect stuff to be in models
            self.model = 'models.' + query.kind

    def _add_filters(self, valid_filter_operators):
        self.filters = []
        query = self._raw_query
        if isinstance(query, (db.Query, db.GqlQuery)):
            for key, value in query._get_query().items():
                field, operator = key.split(' ')
                self.filters.append((field, operator, value))
        else:
            filters = query.filters
            if filters is not None:
                if not isinstance(filters, (ndb.FilterNode,
                                  ndb.ConjunctionNode)):
                    raise ValueError('unknown gql filtes of type %s',
                                     str(type(filters)))
                if isinstance(filters, ndb.FilterNode):
                    filters = [filters]
                for node in filters:
                    self.filters.append((node._FilterNode__name,
                                         node._FilterNode__opsymbol,
                                         node._FilterNode__value))
        for _, operator, _ in self.filters:
            if operator not in valid_filter_operators:
                raise ValueError(
                    'the only filters supported in a query' +
                    'are: ' + ', '.join(valid_filter_operators))


class Options(object):

    def __init__(self, mapper, shards=20,
                 pipeline_name='generic pipeline'):
        assert isfunction(mapper)
        assert isinstance(shards, (int, long)) and shards > 0
        mapper_str = function_to_qualified_name(mapper)
        self.mapper_params = {'extras': {'mapper': mapper_str}}
        # note that we're passing a wrapper function here
        self.mapper = function_to_qualified_name(mapper_wrapper)
        self.pipeline_name = pipeline_name
        self.shards = shards
        self.input_reader = None
        self.has_reducer = False
        self.reducer = None
        self.output_writer = None
        self.has_query = False
        self.has_file = False

    @property
    def is_configured(self):
        return self.has_query or self.has_file

    def add_reducer(self, reducer, to_file=False,
                    mime_type='text/csv'):
        self.has_reducer = True
        self.reducer = function_to_qualified_name(reducer)
        if to_file:
            self.output_writer = (
                'mapreduce.output_writers.FileOutputWriter')
            self.reducer_params = {
                'filesystem': 'gs',
                'gs_bucket_name': jconfig.get_gcs_bucket_name(),
                'output_sharding': 'none',
                'mime_type': mime_type, }
        else:
            self.output_writer = (
                'mapreduce.output_writers.BlobstoreOutputWriter')
            self.reducer_params = {'mime_type': 'text/plain'}

    def add_query(self, query):
        self.input_reader = (
            'mapreduce.input_readers.DatastoreInputReader')
        qp = QueryParser(query, valid_filter_operators=['='])
        self.mapper_params['entity_kind'] = qp.model
        self.mapper_params['filters'] = qp.filters
        self.has_query = True

    def add_files(self, filenames):
        self.input_reader = (
            'mapreduce.input_readers.FileInputReader')
        self.mapper_params['files'] = filenames
        self.mapper_params['format'] = 'lines'
        self.has_file = True

    def to_dict(self):
        d = {'name': self.pipeline_name,
             'mapper': self.mapper,
             'mapper_params': self.mapper_params,
             'shards': self.shards,
             'input_reader': self.input_reader, }
        if self.has_reducer:
            d['output_writer'] = self.output_writer
            d['reducer'] = self.reducer
            d['reducer_params'] = self.reducer_params
        return d

    def __repr__(self):
        return pprint.pformat(dict(self.to_dict()))

    def pack(self):
        if not self.is_configured:
            raise ValueError('no mapper config yet')
        if self.has_reducer:
            args = (self.pipeline_name, self.mapper, self.reducer,
                    self.input_reader, self.output_writer,
                    self.mapper_params, self.reducer_params,
                    self.shards)
        else:
            args = (self.pipeline_name, self.mapper, self.input_reader,
                    self.mapper_params, self.shards)
        return args


def get_link(pipeline):
    return (jconfig.get_host() + pipeline.base_path +
            '/status?root=' + pipeline.pipeline_id)

# TODO: implement _GoogleCloudStorageOutputWriter
# subclass to directly write csv to cloud storage :o
# TODO: return on success, give filename?
