/* global require */
/* global app */
/* jslint indent: 2 */
/* jslint nomen: true */
// make sure we set up global nucleusReporting and don't overwrite it


var charts_loaded = false;

app.value('reportingSegmentDescriptions', {
  'pop01': ['Top Rung', '#A275B6'],
  'pop02': ['Suburban Splendor', '#A275B6'],
  'pop03': ['Connoisseurs', '#A275B6'],
  'pop04': ['Boomburbs', '#A275B6'],
  'pop05': ['Wealthy Seaboard Suburbs', '#A275B6'],
  'pop06': ['Sophisticated Squires', '#A275B6'],
  'pop07': ['Exurbanites', '#A275B6'],
  'pop08': ['Laptops and Lattes', '#6DCDE3'],
  'pop09': ['Urban Chic', '#6E84C0'],
  'pop10': ['Pleasant-Ville', '#6E84C0'],
  'pop11': ['Pacific Heights', '#6E84C0'],
  'pop12': ['Up and Coming Families', '#C59571'],
  'pop13': ['In Style', '#6E84C0'],
  'pop14': ['Prosperous Empty Nesters', '#84B281'],
  'pop15': ['Silver and Gold', '#84B281'],
  'pop16': ['Enterprising Professionals', '#6E84C0'],
  'pop17': ['Green Acres', '#6E84C0'],
  'pop18': ['Cozy and Comfortable', '#6E84C0'],
  'pop19': ['Milk and Cookies', '#C59571'],
  'pop20': ['City Lights', '#8BBAE4'],
  'pop21': ['Urban Villages', '#C59571'],
  'pop22': ['Metropolitans', '#8BBAE4'],
  'pop23': ['Trendsetters', '#6DCDE3'],
  'pop24': ['Main Street USA', '#FEDCC3'],
  'pop25': ['Salt of the Earth', '#F8ABBD'],
  'pop26': ['Midland Crowd', '#F78078'],
  'pop27': ['Metro Renters', '#6DCDE3'],
  'pop28': ['Aspiring Young Families', '#FAE68D'],
  'pop29': ['Rustbelt Retirees', '#84B281'],
  'pop30': ['Retirement Communities', '#84B281'],
  'pop31': ['Rural Resort Dwellers', '#F78078'],
  'pop32': ['Rustbelt Traditions', '#FEDCC3'],
  'pop33': ['Midlife Junction', '#FEDCC3'],
  'pop34': ['Family Foundations', '#FEDCC3'],
  'pop35': ['International Marketplace', '#FCCC77'],
  'pop36': ['Old and Newcomers', '#6DCDE3'],
  'pop37': ['Prairie Living', '#F8ABBD'],
  'pop38': ['Industrious Urban Fringe', '#FCCC77'],
  'pop39': ['Young and Restless', '#6DCDE3'],
  'pop40': ['Military Proximity', '#C7DE90'],
  'pop41': ['Crossroads', '#F78078'],
  'pop42': ['Southern Satellites', '#F8ABBD'],
  'pop43': ['The Elders', '#84B281'],
  'pop44': ['Urban Melting Pot', '#FCCC77'],
  'pop45': ['City Strivers', '#8BBAE4'],
  'pop46': ['Rooted Rural', '#F78078'],
  'pop47': ['Las Casas', '#FCCC77'],
  'pop48': ['Great Expectations', '#FAE68D'],
  'pop49': ['Senior Sun Seekers', '#84B281'],
  'pop50': ['Heartland Communities', ''],
  'pop51': ['Metro City Edge', '#8BBAE4'],
  'pop52': ['Inner City Tenants', '#FCCC77'],
  'pop53': ['Home Town', '#F8ABBD'],
  'pop54': ['Urban Rows', '#8BBAE4'],
  'pop55': ['College Towns', '#C7DE90'],
  'pop56': ['Rural Bypasses', '#F8ABBD'],
  'pop57': ['Simple Living', '#84B281'],
  'pop58': ['NeWest Residents', '#FCCC77'],
  'pop59': ['Southwestern Families', '#C59571'],
  'pop60': ['City Dimensions', '#FCCC77'],
  'pop61': ['High Rise Renters', '#FCCC77'],
  'pop62': ['Modest Income Homes', '#8BBAE4'],
  'pop63': ['Dorms to Diplomas', '#C7DE90'],
  'pop64': ['City Commons', '#C59571'],
  'pop65': ['Social Security Set', '#84B281'],
  'pop66': ['Unclassified', '#999'],
});

app.factory('nucleusReporting', ['$http', 'reportingSegmentDescriptions', 'adserverOrigin', function($http, reportingSegmentDescriptions, adserverOrigin) {
  'use strict';
  var nucleusReporting = {};
  function nullOrUndefined(o) {
    return typeof o === 'undefined' || typeof o === 'null'
  }
  // ReportingDataWrapper takes in data in format {rows => list of rows, columns
  // => list of Columns} and makes it easy to slice and dice rows into either a
  // list of objects or a list of raw data. All column handling is case-insensitive for convenience.
  // (Column is an object defined as {name => string} with other data optional and currently not used)
  function ReportingDataWrapper(data) {
    var col, i;
    // wrap in IIFE so we don't leak variables into outer scope
    (function () {
      if(!data || !data.rows || !data.columns) {
        var missing = [];
        if (!data) {
          missing.push('entireObject');
        } else {
          if(!data.rows) {
            missing.push('rows');
          }
          if(!data.columns) {
            missing.push('columns');
          }
        }
        throw new Error('data for ReportingDataWrapper is missing required properties');
      }
    })()
    this.rows = data.rows;
    this.columns = data.columns;
    this.labels = data.labels;
    this._columnIndexes = {};
    this._columnNames = [];
    this._columnMapping = {};
    for (i = 0; i < this.columns.length; i++) {
      col = this.columns[i];
      if (col.name) {
        this._columnIndexes[col.name.toLowerCase()] = i;
        this._columnNames.push(col.name.toLowerCase());
        this._columnMapping[col.name.toLowerCase()] = {column: col, idx: i};
      }
    }
  }

  // toObjectArray returns a list of JS objects for the specified list of column names
  // columnNames that are not found generate nulls for that value, and if no
  // columnNames are specified, all columns are used.
  // e.g. wrapper.toObjectArray(['apple']) => [{'apple': r1}, {'apple': r2}, ...]
  ReportingDataWrapper.prototype.toObjectArray = function toObjectArray(columnNames) {
    var indexes, output, i, j, row, idx, output_row, name;
    if (!columnNames) {
      columnNames = this._columnNames;
    }
    indexes = this._columnsToIndexes(columnNames);
    if (indexes.length === 0) {
      // console.log('no matching indexes found');
      return [];
    }
    output = [];
    for (i = 0; i < this.rows.length; i++) {
      row = this.rows[i];
      output_row = {};
      output.push(output_row);
      for (j = 0; j < indexes.length; j++) {
        idx = indexes[j];
        name = columnNames[j];
        if (typeof idx !== null) {
          output_row[name] = row[idx];
        } else {
          output_row[name] = null;
        }
      }
    }
    return output;
  };


  // convert column names to an array of integer indexes into each row. If a
  // column name isn't found, returns null for that column.
  ReportingDataWrapper.prototype._columnsToIndexes = function _columnsToIndexes(columnNames) {
    var i, indexes, idx, col;
    indexes = [];
    for (i = 0; i < columnNames.length; i++) {
      col = columnNames[i];
      idx = this.getColumnIndex(col);
      if (typeof idx !== 'undefined' && typeof idx !== null) {
        indexes.push(idx);
      } else {
        // console.log('col ' + col + ' not found');
        indexes.push(null);
      }
    }
    return indexes;
  };


  // toRawArray returns data as an array of arrays with values in the order of
  // columnNames. Not found columns are converted to nulls.
  ReportingDataWrapper.prototype.toRawArray = function toRawArray(columnNames) {
    var indexes, i, output, row, idx, j, col, output_row;
    if (!columnNames) {
      columnNames = this._columnNames;
    }
    indexes = this._columnsToIndexes(columnNames);
    if (indexes.length === 0) {
      // console.log('no matching indexes found');
      return [];
    }
    output = [];
    for (i = 0; i < this.rows.length; i++) {
      row = this.rows[i];
      output_row = [];
      output.push(output_row);
      for (j = 0; j < indexes.length; j++) {
        idx = indexes[j];
        if (typeof idx !== null) {
          output_row.push(row[idx]);
        }
      }
    }
    return output;
  };

  ReportingDataWrapper.prototype.getColumnMeta = function getColumnMeta(columnName) {
    var col;
    if (columnName) {
      columnName = columnName.toLowerCase();
      col = this._columnMapping[columnName];
      if (col) {
        return col.column;
      }
    }
  };

  ReportingDataWrapper.prototype.getColumnIndex = function getColumnIndex(columnName) {
    var col;
    if (columnName) {
      columnName = columnName.toLowerCase();
      col = this._columnMapping[columnName];
      if (col) {
        return col.idx;
      }
    }
    return null;
  };

  function getKeys(obj) {
    var keys, prop;
    keys = [];
    for(prop in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, prop)) {
        keys.push(prop);
      }
    }
    return keys;
  }

  var defaultOptions = {
    'adserverBase': 'http://adserver.adnucleus.io/api/v1/origin/' + adserverOrigin
  }

  function applyDefaultOptions(options) {
    var keys, fullOptions, i, key, defaultKeys;
    if (!options) {
      options = {};
    }
    fullOptions = {};
    keys = getKeys(options);
    // copy object so we don't overwrite anything
    for(i = 0; i < keys.length; i++) {
      key = keys[i];
      fullOptions[key] = options[key];
    }
    defaultKeys = getKeys(nucleusReporting.defaultOptions);
    for(i = 0; i < defaultKeys.length; i++) {
      key = defaultKeys[i];
      if(typeof fullOptions[key] === 'undefined') {
        fullOptions[key] = nucleusReporting.defaultOptions[key];
      }
    }
    return fullOptions
  }

  // TODO: Use promise setup instead.
  nucleusReporting.getDistribution = function getDistribution(attribute, campaign_key, reporting_object, successCallback, errorCallback, options) {
    var days =reporting_object.days
    var tags = reporting_object.tags
    var reporting_scope = reporting_object.scope
    
    var meta = 'getDistribution for ' + attribute + ' on campaign ' + campaign_key + 'for days ' + days
    options = applyDefaultOptions(options);
    $http.get(options.adserverBase + '/groups/'+reporting_object.nadv_id+ '/reporting/segment_geoid/top?days=' +days+'&tags=' + tags + '&scope='+reporting_scope).success(function (data) {
      var wrapped = new ReportingDataWrapper(data);
      console.log('DISTRIBUTION');
      // console.log(data);
      // console.log(wrapped);
      successCallback(wrapped);
    }).error(function (data) {
      // console.log('ERROR getting distribution ' + meta);
      // console.log(data);
      errorCallback(data);
    })
  }

  nucleusReporting.getTopNAverage = function getTopNAverage(attribute, campaign_key, reporting_object, successCallback, errorCallback, options) {
   
    var days =reporting_object.days
    var tags = reporting_object.tags
    var reporting_scope = reporting_object.scope
    if(!campaign_key || !days) {
      // console.log('ERROR: non-truthy campaign key or invalid days!')
      return;
    }

    var meta = 'getTopN for ' + attribute + ' on campaign ' + campaign_key + 'for days ' + days
    options = applyDefaultOptions(options);
    $http.get('http://adserver.adnucleus.io/api/v1/origin/test-adserver/groups/'+reporting_object.nadv_id+ '/reporting/segment_geoid/top?days=' +days+'&tags=' + tags + '&scope='+reporting_scope).success(function (data) {
      var wrapped = new ReportingDataWrapper(data);
      // console.log('SUCCESS getting topN: ' + meta);
      // console.log(data);
      // console.log(wrapped);
      successCallback(wrapped);
    }).error(function (data) {
      // console.log('ERROR getting distribution: ' + meta);
      // console.log(data);
      errorCallback(data);
    });
  }

  nucleusReporting.getImpressions = function getImpressions(campaign_key, reporting_object, successCallback, errorCallback) {
    console.log('getImpressions kickoff');
    var days =reporting_object.days
    var tags = reporting_object.tags
    var reporting_scope = reporting_object.scope
    if(!days) {
      console.log('ERROR: invalid days! (' + days + ')')
      return;
    }
    if(!reporting_object.nadv_id) {
      throw new Error('non-truthy nadv_id (' + reporting_object.nadv_id + ')');
    }
    if(!reporting_object.tags) {
      throw new Error('non-truthy tags (' + reporting_object.tags + ')');
    }
    var meta = 'getImpressions on tags ' + tags + 'for days ' + days;
    var options = applyDefaultOptions(options);
    $http.get(options.adserverBase + '/groups/'+reporting_object.nadv_id+ '/reporting/overall?days=' +days+'&tags=' + tags).success(function (data) {
      console.log('SUCCESS: ' + meta);
      console.log(data);
      data = wrappedData = {
  "rows": [
    [
      1418804057,
      2225,
      15,
      0.75
    ],
    [
      1418717657,
      1234,
      6,
      0.75
    ],
    [
      1418631257,
      1500,
      50,
      0
    ],
    [
      1418544857,
      1242,
      100,
      0
    ],
    [
      1418458457,
      1122,
      200,
      0
    ],
    [
      1418372057,
      800,
      20,
      0
    ],
    [
      1418285657,
      2122,
      30,
      0
    ],
    [
      1418199257,
      3000,
      45,
      0
    ],
    [
      1418112857,
      1200,
      75,
      0
    ],
    [
      1418026457,
      1222,
      90,
      0
    ],
    [
      1417940057,
      1345,
      120,
      0
    ],
    [
      1417853657,
      1678,
      34,
      0
    ],
    [
      1417767257,
      1800,
      49,
      0
    ],
    [
      1417680857,
      1789,
      52,
      0
    ],
    [
      1417594457,
      1578,
      56,
      0
    ],
    [
      1417508057,
      1678,
      72,
      0
    ],
    [
      1417421657,
      1323,
      89,
      0
    ],
    [
      1417335257,
      1000,
      93,
      0
    ],
    [
      1417248857,
      2000,
      103,
      0
    ],
    [
      1417162457,
      1234,
      121,
      0
    ],
    [
      1417076057,
      1232,
      111,
      0
    ],
    [
      1416989657,
      1000,
      221,
      0
    ],
    [
      1416903257,
      1001,
      90,
      0
    ],
    [
      1416816857,
      2000,
      44,
      0
    ],
    [
      1416730457,
      3000,
      32,
      0
    ],
    [
      1416644057,
      1201,
      33,
      0
    ],
    [
      1416557657,
      1202,
      58,
      0
    ],
    [
      1416471257,
      1200,
      78,
      0
    ],
    [
      1416384857,
      2000,
      133,
      0
    ],
    [
      1416298457,
      1000,
      144,
      0
    ],
    [
      1416212057,
      1000,
      232,
      0
    ]
  ],
  "labels": {
    "interval": "day",
    "tags": [
      "nadv_1"
    ]
  },
  "columns": [
    {
      "kind": "timestamp",
      "name": "timestamp"
    },
    {
      "kind": "integer",
      "name": "views"
    },
    {
      "kind": "integer",
      "name": "clicks"
    },
    {
      "kind": "float",
      "name": "ctr"
    }
  ]
}
      var wrappedData = new ReportingDataWrapper(data);
      // console.log(wrappedData);
      successCallback(wrappedData);
    }).error(function (errorData) {
      console.log('ERROR: ' + meta);
      console.log(errorData);
      errorCallback(errorData);
    });
  }

  nucleusReporting.defaultOptions = defaultOptions;
  nucleusReporting.ERROR_STATUS = 'errored';
  nucleusReporting.LOADED_STATUS = 'loaded';
  nucleusReporting.LOADING_STATUS = 'loading';
  nucleusReporting.REPORT_NOT_AVAILABLE_STATUS = 'not_available';
  nucleusReporting.populate = function populate(pagewoo_campaign_key, reporting_object) {
    if(!pagewoo_campaign_key) {
      // console.log('ERROR: cannot populate, non-truthy pagewoo_campaign_key');
      return;
    }
    if(!reporting_object.days) {
      // console.log('ERROR: cannot populate, days not set');
    }
    reporting_object.status.top_categories = nucleusReporting.LOADING_STATUS;
    reporting_object.status.top_neighborhoods = nucleusReporting.LOADING_STATUS;
    reporting_object.status.flight_tracker = nucleusReporting.LOADING_STATUS;

    var markError = function (name) {
      return function (errorData, statusCode) {
        reporting_object.status[name] = nucleusReporting.ERROR_STATUS;
        if(statusCode === 409) {
          // console.log(name + ' report not yet available');
        } else {
          // console.log(name + ' error status code:' + statusCode);
          // console.log(errorData);
        }
      }
    };
    var toObjectArray = function (name, columnNames) {
      return function (wrappedData) {
        reporting_object.status[name] = nucleusReporting.LOADED_STATUS;
        reporting_object.data[name] = wrappedData.toObjectArray(columnNames);
        // console.log('data for ' + name);
        // console.log(reporting_object.data[name]);
      }
    }

    nucleusReporting.getTopNAverage('category', pagewoo_campaign_key, reporting_object,
                                    toObjectArray('top_categories', ['category', 'ctr']),
                                    markError('top_categories'));

    nucleusReporting.getTopNAverage('segment', pagewoo_campaign_key, reporting_object,
                                    toObjectArray('top_segments', ['segment', 'ctr']),
                                    markError('top_segments'));

    nucleusReporting.getTopNAverage('geoid', pagewoo_campaign_key, reporting_object, function (wrappedData) {
      var row, name, columnNames, data;
      name = 'top_neighborhoods';
      columnNames = ['geoid', 'ctr', 'st_abbrev'];
      reporting_object.status[name] = nucleusReporting.LOADED_STATUS;
      data = wrappedData.toObjectArray(columnNames);
      for(var i = 0; i < data.length; i++) {
        row = data[i];
        if(row.geoid) {
          var split = row.geoid.split('_');
          if (split.length > 1) {
            // TODO: show something different for zip vs. county
            row.neighborhoodLabel = split[split.length - 1];
            // TODO: Incorporate city name in here too.
            row.locationLabel = row.st_abbrev;
          } else {
            // console.log('ERROR, bad geoid: ' + row.geoid);
          }
        }
      }
      reporting_object.data[name] = data;
    }, markError('top_neighborhoods'));

    function unwrapSegments(wrappedData) {
      var row, i, segment, pct, desc;
      var outputData = [];
      var rows = wrappedData.toRawArray(['segment', 'pct_of_views']);
      var totalPercent = 0;
      for (i = 0; i < rows.length; i++) {
        row = rows[i];
        segment = row[0];
        pct = row[1];
        desc = reportingSegmentDescriptions[segment]
        if(!desc || !pct) {
          // console.log('ERROR: invalid segment: ' + segment + 'pct: ' + pct);
          continue
        }
        outputData.push({
          label: desc[0],
          color: desc[1],
          // % with one decimal place.
          data: Math.round(pct * 1000) / 10
        })
        totalPercent = totalPercent + pct;
      }
      // console.log('Missing percentages: ' + (1 - totalPercent));
      // force everything to 100% here
      for (i = 0; i < outputData.length; i++) {
        row = outputData[i];
        row.data = Math.round(row.data * 10 / totalPercent) / 10;
      }
      reporting_object.data.segment_distribution = outputData;
      reporting_object.status.segment_distribution = nucleusReporting.LOADED_STATUS;
      if(outputData && outputData.length) {
        renderDonut(outputData);
      } else {
        renderDonut([
          {label: "Top Rung", data: 40},
          {label: "Trendsetters", data: 10},
          {label: "City Strivers", data: 20},
          {label: "Metro Renters", data: 12},
          {label: "Laptops & Lattes", data: 18}
        ])
      }
      // console.log('finished processing segment distributions');
    }

    var convertTimestampsToMs = function(arrayOfArrays, colIndex) {
      colIndex = colIndex || 0;
      for (var row = 0; row < arrayOfArrays.length; row++) {
        if(arrayOfArrays[row][colIndex]) {
          arrayOfArrays[row][colIndex] = parseInt(arrayOfArrays[row][colIndex] * 1000);
        }
      }
      return arrayOfArrays;
    }

    nucleusReporting.getImpressions(pagewoo_campaign_key, reporting_object, function (wrappedData) {
      console.log('got impressions!');
      console.log(wrappedData);

      reporting_object.status.flight_tracker = nucleusReporting.LOADED_STATUS;
      var data = {
        'views': {
          'data': convertTimestampsToMs(wrappedData.toRawArray(['timestamp', 'views'])),
          'label': 'Views'
        },
        'clicks': {
          'data': convertTimestampsToMs(wrappedData.toRawArray(['timestamp', 'clicks'])),
          'label': 'Clicks',
        },
        'ctr': {
          'data': convertTimestampsToMs(wrappedData.toRawArray(['timestamp', 'ctr'])),
          'label': 'CTR'
        },
        'rawData': wrappedData,
      }
      var view_data = wrappedData.toRawArray(['views'])
      var click_data = wrappedData.toRawArray(['clicks'])

      var totalImpressions = 0;
      for (var i = 0; i < view_data.length; i++) {
        totalImpressions = totalImpressions + (view_data[i][0] || 0)
      }

      var total_clicks = 0;
      for(var i=0; i < total_clicks.length; i++) {
        total_clicks = total_clicks + (click_data[i][0] || 0)
      }
      
      reporting_object.data.flight_tracker = data;
      reporting_object.data.total_impressions = totalImpressions;
      reporting_object.data.total_clicks = total_clicks;
      reporting_object.data.flight_tracker=



      renderFlightTracker(reporting_object.data.flight_tracker);
    }, markError('flight_tracker'));
  }
  nucleusReporting.clear = function clear(reporting_object) {
    reporting_object.status = {};
    reporting_object.data = {};
  }
  function renderDonut(data) {
    if($("#flot-pie-donut").length) {
      $.plot($("#flot-pie-donut"), data, {
        series: {
          pie: {
            innerRadius: 0.4,
            show: true,
            stroke: {
              width: 0
            },
            label: {
              show: false,
              threshold: 0.05
            },
          }
        },
        colors: ["#65b5c2","#4da7c1","#3993bb","#2e7bad","#23649e"],
        grid: {
          hoverable: true,
          clickable: false
        },
        legend: { show: true },
        tooltip: true,
        tooltipOpts: {
          defaultTheme: false,
          content: "%s: %p.0%",
          id: "flotTip",
        }
      });
    }
  }

  function renderFlightTracker(data) {
    if($("#flot-sp1ine").length) {
      var plot = $.plot($("#flot-sp1ine"), [
        data.views, data.clicks
      ], {
        series: {
          lines: {
            show: false
          },
          splines: {
            show: true,
            tension: 0.4,
            lineWidth: 1,
            fill: 0.4
          },
          points: {
            radius: 0,
            show: true
          },
          shadowSize: 2
        },
        grid: {
          hoverable: true,
          clickable: true,
          tickColor: "#d9dee9",
          borderWidth: 1,
          color: '#d9dee9'
        },
        colors: ["#19b39b", "#644688"],
        // colors:["#FFFFFF", "#FFFFFF"],
        xaxis: {
          mode: 'time',
          // ms since epic are based on UTC dates (even though they reflect PST dates)
          timezone: 'utc'
        },
        yaxis: {
          ticks: 4
        },
        legend: {
          show: true,
          backgroundColor: "#336699",
          padding:'2px',
        },
        tooltip: true,
        tooltipOpts: {
          content: function(label, xval, yval, flotItem) {
            return $.plot.formatDate($.plot.dateGenerator(xval, {'timezone': 'utc'}), '%b %d, %Y') + ' - %y.0 %s';
          },
          defaultTheme: false,
          id: "flotTip",
          shifts: {
            x: 0,
            y: 20
          }
        }
      });
    }
  }

  return nucleusReporting
}])
