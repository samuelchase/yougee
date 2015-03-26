/* Asynchronous, Cached Loader for downloading huge requests from the server.
 * The key idea is taking a huge number of requests, batching them into
 * components, caching results and notifying about progress as they complete.
*/
/* global app */
/* jslint nomen: true */
// shim for non-universal Object.keys
var getKeys;
if (Object.keys) {
  getKeys = Object.keys;
} else {
  getKeys = function (o) {
    var keys = [];
    for (var k in o) {
      if(Object.hasOwnProperty(o)) {
        keys.push(k);
      }
    }
    return keys;
  }
}
app.factory("NucleusAsyncLoader", ["$http", "$q", function($http, $q) {
  'use strict';
  var DEFAULT_OPTIONS = {
    batchSize: 100,
    method: 'get',
    maxConcurrentRequests: 10
  }
  function fillDefaultOptions(options, defaults) {
    if(!options) {
      options = {};
    }
    var defaultKeys = getKeys(defaults);
    var key, i;
    for(i=0; i < defaultKeys.length; i++) {
      key = defaultKeys[i];
      if(options[key] === undefined) {
        options[key] = defaults[key];
      }
    }
    return options
  }
  //TODOs
  // * allow cancelling promises
  // * track pending requests so we don't double request
  function generateUniqueId(identifier) {
    return identifier + '-' + Date.now() + '-' + Math.random();
  }

  // RequestQueue is a LIFO Queue that returns promises for each item in the
  // queue.
  function RequestQueue(maxConcurrentRequests) {
    this.maxConcurrentRequests = maxConcurrentRequests;
    // mapping of id => request, where request is object with these keys:
    // {deferred: $q.deferred,
    //  func: function returning promise,
    //  id: unique identifier for requests in queue}
    this.pendingRequests = {};
    // mapping of id => request
    this.runningRequests = {};
    // order of requests so we can do LIFO ordering;
    this.requestQueue = [];
  }
  // function CancellablePromise(deferred, promise) {
  //   this.then = promise.then;
  //   this.cancel = function (reason) { deferred.cancel(reason) };
  //   this.catch = promise.catch;
  //   this['finally'] = promise['finally'];
  // }
  // function CancellableDeferred() {
  //   var self = this;
  //   var deferred = $q.defer();
  //   this.cancel_deferred = $q.defer();
  //   this.cancel_promise = this.cancel_deferred.promise;
  //   this.promise = new CancellablePromise(deferred.promise);
  //   this.notify = deferred.notify;
  //   this.reject = deferred.reject;
  //   this.resolve = deferred.resolve;
  //   this['finally'] = deferred['finally'];
  //   this._state = 'pending';
  //   this.cancelled = false;
  //   deferred.promise.then(function successCB() { self._state = 'resolved'; },
  //                         function errorCB() { self._state = 'rejected'; })
  //   this.cancel = function (reason) {
  //     this.cancel_deferred.resolve(reason);
  //     if(this._state !== 'resolved') {
  //       this.deferred.reject(reason);
  //       this.cancelled = true;
  //       return true;
  //     }
  //     return false;
  //   }
  // }

  // adds request to queue in order to be run and then returns a promise about
  // the result. In the future, you'll be able to call cancel(reason) on the
  // promise to prevent it from being run.
  RequestQueue.prototype.addRequest = function addRequest(runCallback) {
    var deferred = $q.defer();
    var id = generateUniqueId('queue');
    this.pendingRequests[id] = {deferred: deferred, func: runCallback, id: id};
    this.requestQueue.push(id);
    return deferred.promise;
  }

  // runs requests up to maxConcurrentRequests
  RequestQueue.prototype.runRequests = function runRequests() {
    var key, req, promise;
    var numCurrentRequests = getKeys(this.runningRequests).length;
    if(numCurrentRequests >= this.maxConcurrentRequests) {
      return;
    }
    var pendingKeys = getKeys(this.pendingRequests);
    while(numCurrentRequests < this.maxConcurrentRequests &&
          this.requestQueue.length > 0) {
      // LIFO queue
      key = this.requestQueue.pop();
      req = this.pendingRequests[key]
      if(req) {
        promise = req.func();
        promise.then(req.deferred.resolve, req.deferred.reject,
                     req.deferred.notify);
        promise['finally'](this.runRequests);
        this.runningRequests[key] = req;
        delete this.pendingRequests[key];
      }
    }
  }

  // clear cancels and removes all pending requests from the queue.
  RequestQueue.prototype.clear = function clear(reason) {
    var key, i, req;
    var keys = getKeys(this.pendingRequests);
    for (i = 0; i < keys.length; i++) {
      key = keys[i];
      req = this.pendingRequests[key];
      if(req) {
        req.deferred.reject(reason);
      }
      delete this.pendingRequests[key];
    }
    this.requestsQueue = [];
  }

  // NucleusAsyncLoader wraps asynchronous loading and caching of data.
  // @param requestURL - requestURL base to get data
  // @param keyAttribute - attribute to get from returned data to determine how
  //    to cache object data.
  // @param method - HTTP verb to use to make request
  // @param batchSize - integer, number of objects to request per request.
  //
  // The overall assumption is that keys are strings, requests can be made by
  // appending a list of comma-separated items to requestURL and that the data
  // returns as an array of objects that have a key keyAttribute that allows
  // them to be cached.
  //
  // e.g., var loader = NucleusAsyncLoader('http://someurl?keys=', 'group')
  // loader.getData(['a', 'b', 'c']) // requests http://someurl?groups=a,b,c and response should be something like {group: 'a', value: 100}
  // and response (as promise) would be [{group: 'a', value:100}, {group: 'b', value: 125}, ...] etc.
  function NucleusAsyncLoader(requestURL, keyAttribute, method, options) {
    options = fillDefaultOptions(options, DEFAULT_OPTIONS);
    console.log(options)
    this.resultsCache = {};
    this.requestURL = requestURL;
    this.batchSize = options.batchSize;
    this.method = method || DEFAULT_OPTIONS.method;
    this.keyAttribute = keyAttribute
    this.queue = new RequestQueue(options.maxConcurrentRequests);
  }
  // getCachedValues checks for values from the internal cache
  // @param arr - Array of strings, data to load
  // @returns - object {cachedData: <Array of Objects>, cacheMisses: <Array of Strings>}
  //    where cacheMisses are keys that could not be found in the query cache.
  NucleusAsyncLoader.prototype.getCachedValues = function getCachedValues(arr) {
    var key, i, cachedValue;
    var values = {};
    var notFound = [];
    for(i=0; i < arr.length; i++) {
      key = arr[i];
      cachedValue = this.resultsCache[key]
      if(cachedValue !== undefined) {
        values[key] = cachedValue;
      } else {
        notFound.push(key);
      }
    }
    return {
      cachedValues: values,
      cacheMisses: notFound
    };
  }
  // combineData joins all the keys of the given objects to produce a new
  // object with all keys. Later objects overwrite the keys of earlier objects.
  NucleusAsyncLoader.prototype.combineData = function () {
    var outputData = {}
    var i, elem, data, key, keys, j;
    for(i = 0; i < arguments.length; i++) {
      data = arguments[i];
      keys = getKeys(data);
      for(j = 0; j < keys.length; j++) {
        key = keys[j]
        if(data[key] !== undefined) {
          outputData[key] = data[key];
        }
      }
    }
    return outputData;
  }
  // enqueues request for data from server (not cached), handling batching and
  // returning an overall promise.
  NucleusAsyncLoader.prototype.requestData = function requestData(arr) {
    var deferred = $q.defer();
    var overallData = {};
    var numPromises = 0;
    var completedPromises = {};
    var chunk, promise, i, id;
    var self = this;
    var anyFailed = false;
    function makeSuccessCallback(id) {
      return function (httpResponse) {
        var rawData = httpResponse.data;
        var data = {};
        var obj;
        for(var i=0; i < rawData.length; i++) {
          obj = rawData[i];
          try {
            data[obj[self.keyAttribute]] = obj;
          } catch (e) {
            console.log('error storing data: ');
            console.log(e);
            console.log('for object: ');
            console.log(obj);
          }
        }
        //console.log('makeSuccessCallback: '); console.log(data);
        if(!completedPromises[id]) {
          completedPromises[id] = true;
          overallData = self.combineData(overallData, data);
        }
        var numCompleted = getKeys(completedPromises).length
        if(numCompleted === numPromises) {
          //console.log('all promises done - DATA: '); console.log(overallData);
          deferred.resolve(overallData);
        } else if (numCompleted > numPromises) {
          console.log('ERROR: completed promises > total number of promises');
          deferred.resolve(overallData);
        } else {
          // only notify when we're not in a failure state;
          if(!anyFailed) {
            deferred.notify(overallData);
          } else {
            console.log('not notifying - alrady had a failed request');
          }
        }
      }
    }
    function failureCallback(data) {
      anyFailed = true;
      deferred.reject(data);
    }
    function progressCallback(data) {
      overallData = self.combineData(overallData, data);
      if (!anyFailed) {
        deferred.notify(overallData);
      }
    }
    function makeRequestGenerator(chunk) {
      return function () {
        return $http[self.method](self.requestURL + chunk.join(','));
      }
    }
    if(arr.length === 0) {
      deferred.resolve(overallData);
    } else {
      for (i = 0; i < arr.length; i = i + this.batchSize) {
        chunk = arr.slice(i, i + this.batchSize);
        promise = this.queue.addRequest(makeRequestGenerator(chunk));
        id = generateUniqueId('promise');
        promise.then(makeSuccessCallback(id), failureCallback,
                     progressCallback);
        numPromises = numPromises + 1;
      }
      if(!numPromises) {
        console.log('ERROR: expected at least one promise to be generated. None were.');
      }
    }
    return deferred.promise;
  }
  NucleusAsyncLoader.prototype.cacheValues = function cacheValues(data) {
    var keys = getKeys(data);
    var value, key;
    for(var i=0; i < keys.length; i++) {
      key = keys[i];
      value = data[key];
      if(value !== undefined) {
        this.resultsCache[key] = value;
      }
    }
  }

  // returns a promise for data for given set of keys, using cached data or
  // requesting from server as necessary.
  NucleusAsyncLoader.prototype.getValues = function getValues(arr) {
    var self = this;
    var deferred = $q.defer();
    var cacheData = this.getCachedValues(arr);
    if(cacheData.cacheMisses.length === 0) {
      console.log('all values cached, no need to get data');
      deferred.resolve(cacheData.cachedValues);
    } else {
      console.log('requesting ' + cacheData.cacheMisses + ' uncached values');
      var dataPromise = this.requestData(cacheData.cacheMisses);
      dataPromise.then(function(data) {
        var outputData = self.combineData(cacheData.cachedValues, data);
        self.cacheValues(data);
        deferred.resolve(outputData);
      }, deferred.reject, deferred.notify);
    }
    this.queue.runRequests();
    return deferred.promise;
  }
  return NucleusAsyncLoader;
}])

app.value("nearwooGeoHost", "http://107.178.210.79:8891");
app.factory("nucleusAvailables", ["$q", "NucleusAsyncLoader", "nearwooGeoHost", function ($q, NucleusAsyncLoader, nearwooGeoHost) {
  var host = nearwooGeoHost + "/blockcountsjsonp?callback=JSON_CALLBACK&geoids="
  var loader = new NucleusAsyncLoader(host, 'geoid', 'jsonp');
  // get count of availables by block
  loader.getCount = function getCount(blocks) {
    var deferred = $q.defer();
    function sumData(data) {
      var val;
      var keys = getKeys(data)
      var total = 0;
      for (var i=0; i < keys.length; i++) {
        val = data[keys[i]];
        if(val) {
          // skip values that are integer-like
          total = total + (+val.count||0)
        }
      }
      return total;
    }
    loader.getValues(blocks).then(
      function (data) { deferred.resolve(sumData(data)) },
      function (data) { deferred.reject(data) },
      function (data) { deferred.notify(sumData(data)) }
    );
    return deferred.promise;
  }
  return loader;
}])
app.factory("nucleusAppSites", ["$q", "NucleusAsyncLoader", "nearwooGeoHost", function ($q, NucleusAsyncLoader, nearwooGeoHost) {
  var host = nearwooGeoHost + '/sitecategoryjsonp?callback=JSON_CALLBACK&block_groups=';
  var loader = new NucleusAsyncLoader(host, 'geoid', 'jsonp');
  loader.getBlock = function getBlock(geoid) {
    var deferred = $q.defer();
    loader.getValues([geoid]).then(
      function (data) { deferred.resolve(data[geoid]) },
      function (data) { deferred.reject(data) },
      function (data) { deferred.notify(data[geoid]) }
    );
    return deferred.promise;
  }
  return loader;
}])
