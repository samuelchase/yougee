angular.module('homeWooApp', ['ngRoute', 'angulartics', 'angulartics.google.analytics','angulartics.mixpanel'])

// .config(function($routeProvider, $locationProvider) {
//    $routeProvider.when('/', {templateUrl: 'static/partials/home.html', controller: 'MapHome'});
//    // $routeProvider.when('/howitworks', {templateUrl: 'partials/learn.html', controller: learnCtrl});
// })




.controller('MapHome', ['$scope', '$http', '$analytics', '$timeout', function($scope, $http, $analytics, $timeout){

   $analytics.pageTrack('/')
   $analytics.eventTrack('welcome_new', {category:'website', label:'view home page'})
   var address = 'Santa Monica, CA';

   $scope.search_phase = false;
   $scope.start_phase = true;
   //$scope.step2 = false;
   $scope.step1 = true;
   $scope.alert_message = false;

   $scope.polys = []

    $scope.open_blog = function() {
      var win = window.open('http://nearwoo.co', '_blank');
      win.focus();
    }

   $scope.learn_more = function(){
      $timeout(function(){
        window.location='http://nearwoo.appspot.com/b/#/learn';
      }, 300)
   }



   $scope.search_address = function() {
   		console.log('search!')

   		for (var poly in $scope.polys) {
   			$scope.polys[poly].line.setMap(null);
   			$scope.polys[poly].setMap(null);
   		}
   		$scope.polys = [];

	    var geocoder = new google.maps.Geocoder();
	    
	    geocoder.geocode( { 'address': $scope.search}, function(results, status) {
	      console.log('status ' + status)
	      if (status == google.maps.GeocoderStatus.OK) {
	      	//console.log('ok')
	        $scope.address_lat = results[0].geometry.location.lat();
	        $scope.address_lng = results[0].geometry.location.lng();
	        //lat, lng, number_of_blocks, show_marker, is_home
	   		// geocode the address and get the lat lng

			$scope.show_by_lat_lng($scope.address_lat, $scope.address_lng);	        

	      }
	    });

   }

   $scope.show_by_lat_lng = function(lat, lng) {

   		map.setCenter(new google.maps.LatLng(lat, lng))

   		var load_number = 222;
	    var nearest_url = 'http://23.236.50.139:8891/nearestneighborsjsonp?lat='+lat+'&scope=block_group&max_results='+load_number+'&lon='+lng+'&callback=JSON_CALLBACK'
	    $http.jsonp(nearest_url).success(function(data) {

	    	$scope.neighborhood_data = data;
		    for (var p in $scope.neighborhood_data) {
		       make_neighborhood($scope.neighborhood_data[p]);
		    }

		    // select first 3 neighborhoods
		    $scope.poly_click($scope.polys[0])
		    $scope.poly_click($scope.polys[0])
		    $scope.poly_click($scope.polys[0])
		    $scope.poly_click($scope.polys[1])
		    $scope.poly_click($scope.polys[1])
		    $scope.poly_click($scope.polys[2])
		    $scope.poly_click($scope.polys[3])
		    //$scope.poly_click($scope.polys[4])

	    });

   }

   $scope.count_neighborhoods = function() {
   	var i = 0;
   	for (var poly in $scope.polys) {
   		if ($scope.polys[poly].level > 0) {
   			//console.log('ct' + i)
   			i++;
   		}

   	}
   	return i;
   }

   $scope.go_on = function() {
    // console.log('polys +++ ')
    // console.log($scope.polys)
   		var geoids = [];
   		var adamounts = [];
   		for (var poly in $scope.polys) {
   			if ($scope.polys[poly].level > 0) {
   				geoids.push($scope.polys[poly].geoid);
   				adamounts.push($scope.polys[poly].level)
   			}
   		}
      // console.log('geoids +++ ')
      // console.log(geoids)
      if(geoids.length <= 0){
        $scope.alert_message = ' Please select a neighborhood!'
      }else{
     		var data = {'geoids':geoids, 'adamounts':adamounts, 'lat':$scope.address_lat, 'lng':$scope.address_lng}
  	    $http.post('/sethomehoods', data).success(function(data) {

  	        window.location = '../b/#/business_listings/undefined/undefined'
  	    
  	    });
      }

   }

   $scope.map_click = function() {
   	//$scope.step1 = false;
   	//$scope.step2 = true;	

   	var hoods = 0;
   	var ads = 0;
   	for (var poly in $scope.polys) {
   		if ($scope.polys[poly].level > 0) {
   			hoods++;
   		}
   		ads += $scope.polys[poly].level;
   	}

   	$scope.neighborhoods = hoods;
   	$scope.ads = ads;
   	//console.log($scope.neighborhoods)
   	if (!$scope.$$phase) {
   		$scope.$apply();
   	}
   	
   }

    $scope.show_position = function(position)
    {
    	console.log('got coords')
    	$scope.show_by_lat_lng(position.coords.latitude, position.coords.longitude)
      $scope.address_lat = position.coords.latitude;
      $scope.address_lng = position.coords.longitude;
   
    }

    $scope.pos_error = function(err){alert(err);}



   $scope.start_page = function() {

   		console.log('start page')
        if (navigator.geolocation)
        {
        	console.log('getting location')
            navigator.geolocation.getCurrentPosition($scope.show_position, $scope.pos_error);
        } else {
        	alert('Geo Not Available')
        }

	   $scope.search_phase = true;
	   $scope.start_phase = false; 
	   $scope.search_address();
	   $('#search_phase').css('display', 'block');
	   //$scope.$apply();
   }

   $scope.the_search_page = function() {

   	   console.log('search page')

	   $scope.search_phase = true;
	   $scope.start_phase = false; 
	   $scope.search_address();
	   $('#search_phase').css('display', 'block');
	   //$scope.$apply();
   }

   $scope.ads = 0;
   $scope.neighborhoods = 0;

   var map = new google.maps.Map(document.getElementById('the_map'), { 
       //mapTypeId: google.maps.MapTypeId.ROADMAP,
       //disableDefaultUI: true,
       zoom: 15,
	    //zoom: 4,
	    panControl: false,
	    zoomControl: true,
	    scaleControl: true,
	    zoomControlOptions: {
	      style: google.maps.ZoomControlStyle.SMALL,
	      position: google.maps.ControlPosition.RIGHT_BOTTOM
	    }

   });

   var geocoder = new google.maps.Geocoder();

   geocoder.geocode({
      'address': address
   }, 
   function(results, status) {
      if(status == google.maps.GeocoderStatus.OK) {
         new google.maps.Marker({
            position: results[0].geometry.location,
            map: map
         });
         map.setCenter(results[0].geometry.location);
      }
      else {
         // Google couldn't geocode this request. Handle appropriately.
      }
   });


   var nwMakePoints = function(pt_arr) {
      var boundaries = []
      for (var i in pt_arr) {

          var pt_list = pt_arr[i];
          var points = [];
          for (var i = 0; i < pt_list.length; i+=2) {
              points.push(new google.maps.LatLng(pt_list[i], pt_list[i+1]))
          }
          //points.push(points[0])
          boundaries.push(points);    

      }

      return boundaries;
   }

  var makePoints = function(pt_arr){
  // START MAKE POINTS

      // //console.log('making points')
      // //console.log(pt_arr)

      pt_arr = pt_arr
      var boundaries = []
      for (var i in pt_arr) {

          var pt_list = pt_arr[i];
          //console.log('pts')
          //console.log(pt_list.length)
          var points=[]
          for (var i = 0; i < pt_list.length; i+=2) {
              ////console.log('making pt ' + pt_list[i] + ' 2: ' + pt_list[i+1])
              points.push(new google.maps.LatLng(pt_list[i], pt_list[i+1]))
          }
          boundaries.push(points);    

      }

      return boundaries;
  }


   var make_neighborhood = function(neighborhood_data) {

      var polygon = neighborhood_data.polygon;
      var geoid = neighborhood_data.geoid;

      ////console.log('fyck ball ') 
      ////console.log(polygon_array.length)

      var coords = makePoints(polygon);
      var boundaries = nwMakePoints(polygon)

      //console.log('coords!')
      //console.log(coords)
      
      var lineSymbol = {
          path: 'M 0,-1 0,1',
          strokeOpacity: .31,
          scale: 2, 
          color: '#999'
      };

      var line = new google.maps.Polyline({
          path: coords[0],
          strokeOpacity: 0,
          icons: [{
              icon: lineSymbol,
              offset: '0',
              repeat: '10px'
          }],
          map: map
      });

      var poly = new google.maps.Polygon({
          paths: boundaries,
          strokeColor: '#7d7d7d',
          strokeOpacity: 0,
          strokeWeight: 1,
          fillColor: '#e6e6e6',
          fillOpacity: 0
      });

      // add more properties if need be.
      poly.geoid = geoid;
      poly.block_data = neighborhood_data;
      poly.level = 0;
      poly.line = line;

      var map_hover = google.maps.event.addListener(poly,"mouseover",function(){

      	$scope.current_poly = poly.block_data;
      	$scope.$apply();

      });

      var map_clicker = google.maps.event.addListener(poly,"click",function(){

      	$scope.poly_click(poly);
      	$scope.$apply();

      });

      poly.setMap(map);
      $scope.polys.push(poly)

   }

   $scope.poly_click = function(poly) {
        $scope.alert_message = false;

      	poly.level += 1000;
      	if (poly.level > 3000) {
      		poly.level = 0;
      	}
      	$scope.map_click();


      	// multiple neighborhood options
        if (poly.level == 0) {
        	poly.setOptions({fillOpacity:0, fillColor:'#5bc0de'})
        } else if (poly.level == 1000) {
        	poly.setOptions({fillOpacity:.6, fillColor:'#ffca04'})
        } else if (poly.level == 2000) {
        	poly.setOptions({fillOpacity:.6, fillColor:'#5bc0de'})
        } else if (poly.level == 3000) {
        	poly.setOptions({fillOpacity:.6, fillColor:'#ed1650'})
        }
        
        $scope.is_poly = poly.geoid;

   }

}])



var start_enter = function() {
	console.log('start enter')
	var element = document.getElementById('main-controller')
	var scope = angular.element(element).scope()
	scope.start_page()
}

var search_enter = function() {
	var element = document.getElementById('main-controller')
	//console.log('ele')
	//console.log(element)
	var scope = angular.element(element).scope()
	scope.search_address()
}

var search_page = function() {
	var element = document.getElementById('main-controller')
	//console.log('ele')
	//console.log(element)
	var scope = angular.element(element).scope()
	scope.the_search_page()
}
