'use strict';

/* Services */

// Demonstrate how to register services
// In this case it is a simple value service.


nucleusApp.factory('nwNotify', function() {
  return function(msg) {
    return 'message: ' + msg 
  };
});

nucleusApp.factory('nwUploadImage', ['$http', function($http){
    return function(set_files, upload_url){
      var fd = new FormData();
      for (var i in set_files) {
          fd.append("uploadedFile", set_files[i]);
          if (set_files[i].size > 1000000) {
            alert("Whoa, That's a big file!  Please keep it under 1MB. Thanks!");
            return;
          }
      }

      fd.append('title', $scope.creative_title)
      fd.append('')
      var xhr = new XMLHttpRequest();
      xhr.open("POST", upload_url, true);
      xhr.send(fd);
      return xhr
    }
  }])

// nwGetMetrics - helper function for accessing metrics data
// @param camp_key, String - campaign key for metrics
// @param trend_date_start, Date - start date (optional)
// @param trend_date_end, Date (ignored but present for compat)
// @param kind, String - Type of metric to request (optional, if not present,
//                       requests banner views and clicks). Options: {os, conversions, ...}
// @returns $http object.
nucleusApp.factory('nwGetMetrics', ['$http', function($http){
  return function(camp_key, trend_date_start, trend_date_end, kind) {
      // don't bother if camp is undefined
      if(!camp_key) {
          console.log('camp key is not defined, not doing anything');
          return;
      }
    var date_to_string = function(date) {
       var yyyy = date.getFullYear().toString();
       var mm = (date.getMonth()+1).toString(); // getMonth() is zero-based
       var dd  = date.getDate().toString();
       return yyyy + '-' + (mm[1]?mm:"0"+mm[0]) + '-' + (dd[1]?dd:"0"+dd[0]); // padding
      };

      var url = '/api/v1/camp/metrics/' + camp_key;
      if(kind) {
          url = url + '/' + kind;
      }
      if (trend_date_start) {
        console.log("START DATE  " + date_to_string(trend_date_start))
        var start_date = date_to_string(trend_date_start);
        var end_date = date_to_string(trend_date_end);
        var url = url + '?start_date=' + start_date + '&end_date=' + end_date
      }
      console.log(url)
    return $http.get(url)
  }
}])

nucleusApp.factory('nwGetOSMetrics', ['$http', function($http){
  return function(camp_key, trend_date_start, trend_date_end) {
    

    var date_to_string = function(date) {
       var yyyy = date.getFullYear().toString();
       var mm = (date.getMonth()+1).toString(); // getMonth() is zero-based
       var dd  = date.getDate().toString();
       return yyyy + '-' + (mm[1]?mm:"0"+mm[0]) + '-' + (dd[1]?dd:"0"+dd[0]); // padding
      };



      if (trend_date_start) {
        console.log("START DATE  " + date_to_string(trend_date_start))
        var start_date = date_to_string(trend_date_start);
        var end_date = date_to_string(trend_date_end);
        var url = '/api/v1/camp/metrics/' + camp_key+ '/os?start_date=' + start_date + '&end_date=' + end_date
      }
      else {
        var url = '/api/v1/camp/metrics/' + camp_key + '/os'
      }

      console.log(url)
    return $http.get(url)
  }
}])

nucleusApp.factory('nwMakeContent', ['$http', function($http){
  return function(gae_key, yelp_data){
    return $http.post('/makecontent/' + gae_key + '?overwrite=1', yelp_data)
  }
}])

nucleusApp.factory('nwSaveNeighborhoods', function() {
  return
})

nucleusApp.factory('nwGetConversionData', ['http', function($http) {
  return function(camp_key, data) {
    return $http.get('/api/v1/camp/conversions/' + camp_key, data)
  }
}])

nucleusApp.factory('nwGetSiteCategories', ['http', function($http) {
  return function(camp_key, data) {
    return $http.get('/api/v1/camp/sitecategories/' + camp_key, data)
  }
}])

// Example payment obj
 // { 
 //    'payment': {   
          //         'amount_subscribed' = 300 (amount due)           //required
          //         'billing_period' = 3  (in months)   //required
          //         'initial_charge' = 100 (before promo)             //required
        //           'home_price' = 25                   //required
 //                  'block_groups' = 10,                //required
 //                  'promo_category' = 'save30',        //optional
 //                  'promo_id' = 'lisazahler'           //optional
 //                  'stripe' = {                        //required
 //                              'id' = 'azqwhsdibt' 
 //                             },
 //                  'use_block_points' = 1,             //required
 //                  'downsell' = 0,                     //required
 //    // ...      rest of the yelp data goes here
 // }
nucleusApp.factory('nwCheckout', ['http', function($http) {
  return function(yelp_key, data) {
    return $http.post('/savepayment/' + yelp_key, data)
  }
}]);


//Get Billing
nucleusApp.factory('nwGetBilling', ['$http', function($http) {
  return function(key) {
    var billing = $http.get('/api/v1/billingservice/' + key)
    return billing
  }

}]);


// Get Yelp
// Take a key of YelpJsonDS, NearWooCampaignDS, or Advertiser
// and return all YelpJson entities related to that key
nucleusApp.factory('nwGetYelp', ['$http', function($http) {
	return function (key) {
		return $http.get('/api/v1/yelp/' + key + '/')
  }
}]);

// Put Yelp
// save_type options are 'save', 'create', 'insert'
nucleusApp.factory('nwPutYelp', ['$http', function($http) {
	return function (key, save_type, data) {
		return $http.post('/api/v1/yelp/' + key + '/' +save_type , data)
  }
}]);

// Get Camp
// Take a key of YelpJsonDS, NearWooCampaignDS, or Advertiser
// and return all Advertiser entities related to that key
nucleusApp.factory('nwGetCamp', ['$http', function($http) {
	return function(key) {
	   return $http.get('/api/v1/camp/' + key)
	}
}])

// Put Camp
// save_type options are 'save', 'create', 'insert'
nucleusApp.factory('nwPutCamp', ['$http', function($http) {
  return function(key, save_type, data) {
    return $http.post('/api/v1/camp/' + save_type + '/' + key, data)
  }
}]);

// Get ADV
nucleusApp.factory('nwGetAdv', ['$http', function($http) {
  return function(key) {
    return $http.get('/api/v1/adv/' + key)
  }
}]);

// Put Adv
nucleusApp.factory('nwPutAdv', ['$http', function($http) {
  return function(key, save_type, data) {
    return $http.post('/api/v1/adv/' + save_type + '/' + key, data)
  }
}]);

// Get Partner
nucleusApp.factory('nwGetPartner', ['$http', function($http) {
  return function(key) {
    return $http.get('/api/v1/partner/' + key)
  }
}]);

// Put Partner
nucleusApp.factory('nwPutPartner', ['$http', function($http) {
  return function(key, save_type, data) {
    return $http.post('/api/v1/partner/' + save_type + '/' + key, data)
  }
}]);

// Get Rep
nucleusApp.factory('nwGetRep', ['$http', function($http) {
  return function(key) {
    return $http.get('/api/v1/rep/' + key)
  }
}]);

// Put Rep
nucleusApp.factory('nwPutRep', ['$http', function($http) {
  return function(key, save_type, data) {
    return $http.post('/api/v1/rep/' + save_type + '/' + key, data)
  }
}]);


//Get site cats

nucleusApp.factory('nwGetSiteCats', ['$http', function($http) {
  return function(){
    // return $http.get('/insightcategories/')
    return {data:[{is_selected:true, cat_name:'Arts & Entertainment', cat_img: 'image.png', cat_color:'arts', site_list:['BBC', 'Bravo' , 'CBS']},{is_selected:true, cat_name:'Auto', cat_img: 'image.png', cat_color:'auto', site_list:['AutoTrader', 'Cars.com' , 'Edmunds' ]},{is_selected:true, cat_name:'Business', cat_img: 'image.png', cat_color:'busi', site_list:['Business Insider', 'Craigslist' , 'eBay']},{is_selected:true, cat_name:'Careers', cat_img: 'image.png', cat_color:'car', site_list:['Monster', 'SnagAJob' , 'Job.com' ]},{is_selected:true, cat_name:'Education', cat_img: 'image.png', cat_color:'edu', site_list:['About.com', 'eHow.com' , 'Answers.com']},{is_selected:true, cat_name:'Family & Parenting', cat_img: 'image.png', cat_color:'fam', site_list:['Home & Garden', 'Family Circle' , 'Parenting.com' ]},{is_selected:true, cat_name:'Food & Drink', cat_img: 'image.png', cat_color:'food', site_list:['OpenTable', 'Allrecipes.com' , 'Delish']},{is_selected:true, cat_name:'Health & Fitness', cat_img: 'image.png', cat_color:'health', site_list:['Shape', 'Health.com' , 'Dailyburn.com' ]},{is_selected:true, cat_name:'Hobbies & Interests', cat_img: 'image.png', cat_color:'hobby', site_list:['Scrabble', 'Angry Birds' , 'Candy Crush']},{is_selected:true, cat_name:'Home & Garden', cat_img: 'image.png', cat_color:'home', site_list:['Women’s Day', 'HGTV' , 'Good Housekeeping' ]},{is_selected:true, cat_name:'Law, Gov\'t & Politics', cat_img: 'image.png', cat_color:'law', site_list:['CNN', 'Huffington Post' , 'Gawker']},{is_selected:true, cat_name:'News', cat_img: 'image.png', cat_color:'news', site_list:['Examiner', 'Weather.com' , 'NBC News']},{is_selected:true, cat_name:'Personal Finance', cat_img: 'image.png', cat_color:'finance', site_list:['Kiplinger', 'Seeking Alpha' , 'Bank Rate' ]},{is_selected:true, cat_name:'Pets', cat_img: 'image.png', cat_color:'pet', site_list:['Dogs Blog', 'Dogs Health' , 'Pet Daycare World']},{is_selected:true, cat_name:'Real Estate', cat_img: 'image.png', cat_color:'real', site_list:['Zillow', 'Trulia' , 'Realtor.com' ]},{is_selected:true, cat_name:'Society', cat_img: 'image.png', cat_color:'society', site_list:['Time', 'US Weekly' , 'Cosmopolitan']},{is_selected:true, cat_name:'Science', cat_img: 'image.png', cat_color:'science', site_list:['Discovery', 'Nature.com' , 'PopSci.com' ]},{is_selected:true, cat_name:'Style', cat_img: 'image.png', cat_color:'style', site_list:['InStyle', 'Vogue' , 'Allure' ]},{is_selected:true, cat_name:'Shopping', cat_img: 'image.png', cat_color:'shop', site_list:['Etsy', 'eLux' , 'Zappos']},{is_selected:true, cat_name:'Sports', cat_img: 'image.png', cat_color:'sprt', site_list:['SB Nation', 'ESPN' , 'NBC Sports' ]},{is_selected:true, cat_name:'Technology & Computing', cat_img: 'image.png', cat_color:'tech', site_list:['Popular Science', 'CNET.com' , 'Apple Insider']},{is_selected:true, cat_name:'Travel', cat_img: 'image.png', cat_color:'trav', site_list:['Expedia', 'SeatGuru' , 'Trip Advisor' ]},{is_selected:true, cat_name:'Other', cat_color:'other', cat_img: 'image.png'}]}
  }
}])



nucleusApp.factory('nwChangePassword', ['$http', function($http){
  return function(advertiser_key, password_data){
    return $http.post('/api/v1/advertiser/' +  advertiser_key + '/password', password_data)
  }
}])


// For lazy loading d3... 
// TODO: needs work to function with d3 plugins
nucleusApp.factory('d3Service', ['$document', '$window', '$q', '$rootScope',
  function($document, $window, $q, $rootScope) {
    var d = $q.defer(),
        d3service = {
          d3: function() { return d.promise; }
        };
    function onScriptLoad() {
      // Load client in the browser
      $rootScope.$apply(function() { d.resolve($window.d3); });
    }
    var scriptTag = $document[0].createElement('script');
    scriptTag.type = 'text/javascript'; 
    scriptTag.async = true;
    scriptTag.src = 'http://d3js.org/d3.v3.min.js';
    scriptTag.onreadystatechange = function () {
      if (this.readyState == 'complete') onScriptLoad();
    }
    scriptTag.onload = onScriptLoad;
 
    var s = $document[0].getElementsByTagName('body')[0];
    s.appendChild(scriptTag);

    return d3service;
}]);


// Get Referral Url
nucleusApp.factory('nwGetRef', ['$http', function($http) {
  return function(key) {
    return $http.get('/refer/make/' + key);
  }
}]);


// Get short Referral Url (4 Tweet)
nucleusApp.factory('nwGetShortRef', ['$http', function($http) {
  return function(key) {
    return $http.get('/refer/bitlyfy/' + key);
  }
}]);

// Shorten Link
nucleusApp.factory('nwShortenURL', ['$http', function($http) {
  return function(url) {
    return $http.get('/social/shorten/' + url);
  }
}]);

// Only checks at top level
// nucleusApp.factory('containsUndefined', function() {
//   return function(obj) {
//     for (k in obj) {
//       if (obj.hasOwnProperty(k) && obj[k] === undefined) {
//         return true;
//       }
//     }
//     return false;
//   }
// })

