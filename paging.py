'''
This module contains classes for managing paging.
'''
import google.appengine.api.memcache as memcache
from google.appengine.ext import ndb
import logging
import pickle
import math

namespace = 'he3'


class CachedPagedQuery(object):


    """Uses memcache as a persistence layer for doing paging on NDB queries.

    It likely won't report page count correctly when there are more than 1K
    campaigns (that's okay for now). It also may cause extra reads/writes if
    two people try to load the same page twice.  Again, dealing with that just
    isn't worth it (for now). If we see more of it in the future, then we can
    deal with it then).


    This isn't fool proof because our id is based upon the hashed string
    representation but it's good enough for our use cases.
    """

    _MEMCACHE_TIMEOUT = 60 * 60 # store for an hour
    _page_count = None
    def __init__(self, query, page_limit, namespace=namespace):
        self.query = query
        self.page_limit = page_limit
        # TODO: Maybe move this elsewhere (costs ~100-250ms)
        persisted = memcache.get(self.id)
        self._more = None
        # this marks the cursor to *start* the page at index (0 has no cursor
        # so it's None, etc)
        self._page_cursors = [None] # we never care about first cursor anyways
        if persisted is not None:
            self._from_persisted(persisted)
        else:
            logging.info("No cached query for %s", query)

    @property
    def id(self):
        # make sure ID is unique with page size in case that changes + string
        # representation of query is 'good enough' for our purposes.
        return '%s_CachedQuery_%s_page_%s' % (namespace, hash(str(self.query)), self.page_limit)

    def clear(self):
        memcache.delete(self.id)
        self._page_cursors = [None]
        self._page_count = None
        self._more = None

    def _has_page(self, page_number):
        if len(self._page_cursors) >= page_number:
            return self._page_cursors[page_number - 1] is not None

    def _fetch_up_to(self, page_number):
        if not page_number:
            return True
        # None indicates we're not sure, False means definitely not
        if self._more is not None and not self._more:
            return self._more
        last_page = len(self._page_cursors)
        curr_page = last_page
        more = True
        if last_page > 1:
            next_cursor = self._page_cursors[last_page - 1]
            if next_cursor is not None:
                next_cursor = ndb.Cursor(urlsafe=next_cursor)
        else:
            next_cursor = None
        while curr_page < page_number and more:
            # do keys only so we only cost us a small
            _, next_cursor, more = self.query.fetch_page(self.page_limit,
                                                         start_cursor=next_cursor,
                                                         keys_only=True)
            curr_page += 1
            self._store_next_cursor(next_cursor, more, curr_page)
            # sometimes we are spuriously told ther'es more
            more = more and next_cursor
        return more

    def _store_next_cursor(self, next_cursor, more, page_number):
        if len(self._page_cursors) > page_number:
            self._page_cursors[self.page_number - 1] = next_cursor.urlsafe()
            return
        if next_cursor is not None:
            self._page_cursors.append(next_cursor.urlsafe())
        else:
            logging.info("Next cursor was none")
        self._more = bool(more) and bool(next_cursor)

    def fetch_page(self, page_number, clear=False):
        if clear:
            self.clear()
        # special case when we're *on* the page number
        if page_number == len(self._page_cursors):
            cursor = self._get_cursor(page_number)
            results, next_cursor, more = self.query.fetch_page(self.page_limit,
                                                               start_cursor=cursor)
            self._store_next_cursor(next_cursor, more, page_number)
            self.save()
            return results
        if page_number == 1:
            results, next_cursor, more = self.query.fetch_page(self.page_limit)
            # self._store_next_cursor(next_cursor, more, 1)
            self.save()
            return results
        if not self._has_page(page_number):
            self._fetch_up_to(page_number)
        cursor = self._get_cursor(page_number)
        if cursor is None and page_number != 1:
            logging.info("Nothing left to do for cursor")
            self.save()
            return []
        results, next_cursor, more = self.query.fetch_page(self.page_limit, start_cursor=cursor)
        if not self._has_page(page_number + 1):
            self._store_next_cursor(next_cursor, more, page_number)
        else:
            logging.info("Not storing next page because it's already there")
        self.save()
        return results

    def _get_cursor(self, page_number):
        "Returns the cursor to *generate* the given page_number"
        if not self._page_cursors:
            self._page_cursors = [None]
        if self._page_cursors[-1] is None and page_number != 1:
            return None
        # 0 --> is for page 0 (None)
        # 1 --> generates page 1
        urlsafe_cursor = self._page_cursors[page_number - 1]
        if urlsafe_cursor is not None:
            return ndb.Cursor(urlsafe=urlsafe_cursor)

    def save(self):
        if self._page_count is not None or self._page_cursors is not None:
            memcache.set(self.id, self._get_persisted_form(),
                         time=self._MEMCACHE_TIMEOUT)

    def _from_persisted(self, persisted_form):
        if not isinstance(persisted_form, dict):
            logging.error("Found persisted_form, expected dict, found %s",
                          type(persisted_form))
            return
        self._page_cursors = persisted_form.get('page_cursors', None)
        self._page_count = persisted_form.get('page_count', None)
        self._more = persisted_form.get('more', None)

    def _get_persisted_form(self):
        return {
                'page_cursors': [s for s in (self._page_cursors or [])],
                'page_count': self._page_count,
                'has_more': self._more,
                }

    def page_count(self):
        if self._page_count is None:
            self._page_count = math.ceil(self.query.count() * 1.0 /
                    self.page_limit)
        return self._page_count
