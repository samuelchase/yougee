


from google.appengine.ext import ndb
import json
import datetime


class NDBWrapper(ndb.Model):
    # local cache only helps for explicit gets (on keys) within the same
    # request. Since we don't really use that, we want to disable local
    # caching.
    _use_cache = False
    #: number of records to return for items like invoices and edits
    _default_fetch_number = 100
    _excluded_attributes = tuple()

    def _manual_get_hook(self):
        """Calls _post_get_hook on the model with appropriate arguments
        (important because _post_get_hook doesn't get called by queries)"""
        future = DummyFuture(self)
        type(self)._post_get_hook(self.key, future)

    def to_ndb_dict(self, transform=None):
        if transform is not None:
            assert inspect.isfunction(transform)
        d = OrderedDict()
        props = getattr(self, '_ordered_property_list', self._properties)
        for prop in props:
            d[prop] = getattr(self, prop, None)
            if transform is not None:
                d[prop] = transform(d[prop])
            # ENUMS aren't JSON serializable
            if isinstance(d[prop], messages.Enum):
                d[prop] = d[prop].name
        return d

    @property
    def _origin(self):
        # strip leading 's~'
        return self.key.app()[2:] if self.key else None

    @classmethod
    def get_most_recent(cls, n, attr_name=None):
        "Convenience method - don't rely on this in production"
        properties = cls._properties
        if not attr_name:
            for k in ('created', 'date_created', 'modified'):
                if k in properties:
                    attr_name = k
                    break
        if not attr_name:
            raise ValueError("Can't determine which property to use")
        orderer = getattr(cls, attr_name, None)
        results = cls.query().order(-orderer).fetch(n)
        for o in results:
            o._manual_get_hook()
        return results

    @classmethod
    def urlsafe_get(cls, key, raise_on_error=False):
        """gets object by urlsafe key and raises if type doesn't match.

        Will raise on other errors if raise_on_error=True.

        While you could use the broad `Key(urlsafe=<key>)` function, the
        benefit of this classmethod is to help better reason about correctness
        (and prevent sending wrong kind of key to the wrong method)."""
        result = None
        if key:
            try:
                result = ndb.Key(urlsafe=key).get()
            except:
                if raise_on_error:
                    raise
        if result and not isinstance(result, cls):
            raise WrongKindError("Expected: %s, Got: %s" % (
                cls.__name__,
                type(result).__name__,
                ))
        return result

    @classmethod
    def get_all(cls):
        import wootils
        return wootils.iterate(cls.query())


    def to_dict(self, transform=None):
        if transform is not None:
            assert inspect.isfunction(transform)
        d = OrderedDict()
        props = getattr(self, '_ordered_property_list', self._properties)
        for prop in props:
            d[prop] = getattr(self, prop, None)
            if transform is not None:
                d[prop] = transform(d[prop])
            # ENUMS aren't JSON serializable
            if isinstance(d[prop], messages.Enum):
                d[prop] = d[prop].name
        return d

    def to_ascii_dict(self):
        return self.to_dict(to_ascii)


class Tag(NDBWrapper):
    name = ndb.StringProperty()
    popularity = ndb.IntegerProperty(default=0)
    created = ndb.DateTimeProperty(auto_now_add=True)


class DemoRequest(NDBWrapper):
    email = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)


class Business(NDBWrapper):
    tag_keys = ndb.StringProperty(repeated=True)
    name = ndb.StringProperty()
    address = ndb.StringProperty()
    website = ndb.StringProperty()
    email = ndb.StringProperty()
    phone = ndb.StringProperty()
    notes = ndb.StringProperty()

    lattitude = ndb.FloatProperty()
    longitude = ndb.FloatProperty()

    # Booleans
    farm = ndb.BooleanProperty()
    market = ndb.BooleanProperty()
    restaraunt = ndb.BooleanProperty()
    organic = ndb.BooleanProperty()
    seasonal_menu = ndb.BooleanProperty()
    locally_sourced = ndb.BooleanProperty()
    free_range = ndb.BooleanProperty()
    grass_fed= ndb.BooleanProperty()
    no_gmo = ndb.BooleanProperty()
    gluten_free = ndb.BooleanProperty()
    vegan = ndb.BooleanProperty()
    veganic = ndb.BooleanProperty()
    raw = ndb.BooleanProperty()
    composting = ndb.BooleanProperty()
    bike_parking = ndb.BooleanProperty()
    leed_certified = ndb.BooleanProperty()
    renewable_energy = ndb.BooleanProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    def to_dict(self):
        data = self._to_dict()
        data['key'] = self.key.urlsafe()
        data['created'] = self.created.strftime("%m-%d-%Y")
        return data

    def to_json(self):
    	return json.dumps(self.to_dict())

