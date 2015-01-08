
angular.module("rzModule",[]).value("throttle",function(a,b,c){var d,e,f,g=Date.now||function(){return(new Date).getTime()},h=null,i=0;c||(c={});var j=function(){i=c.leading===!1?0:g(),h=null,f=a.apply(d,e),d=e=null};return function(){var k=g();i||c.leading!==!1||(i=k);var l=b-(k-i);return d=this,e=arguments,0>=l?(clearTimeout(h),h=null,i=k,f=a.apply(d,e),d=e=null):h||c.trailing===!1||(h=setTimeout(j,l)),f}}).factory("Slider",["$timeout","$document","throttle",function(a,b,c){var d=function(a,b,c){this.scope=a,this.attributes=c,this.sliderElem=b,this.range=void 0!==c.rzSliderHigh&&void 0!==c.rzSliderModel,this.handleHalfWidth=0,this.maxLeft=0,this.precision=0,this.step=0,this.tracking="",this.minValue=0,this.maxValue=0,this.valueRange=0,this.initRun=!1,this.customTrFn=null,this.fullBar=null,this.selBar=null,this.minH=null,this.maxH=null,this.flrLab=null,this.ceilLab=null,this.minLab=null,this.maxLab=null,this.cmbLab=null,this.init()};return d.prototype={init:function(){var b=this;this.scope.rzSliderTranslate&&(this.customTrFn=this.scope.rzSliderTranslate()),this.initElemHandles(),this.calcViewDimensions(),this.setMinAndMax(),this.precision=void 0===this.scope.rzSliderPrecision?0:+this.scope.rzSliderPrecision,this.step=void 0===this.scope.rzSliderStep?1:+this.scope.rzSliderStep,a(function(){b.updateCeilLab(),b.updateFloorLab(),b.initHandles(),b.bindEvents()}),angular.element(window).on("resize",angular.bind(this,this.calcViewDimensions)),this.initRun=!0;var d=c(function(){b.setMinAndMax(),b.updateLowHandle(b.valueToOffset(b.scope.rzSliderModel)),b.range&&(b.updateSelectionBar(),b.updateCmbLabel())},350,{leading:!1}),e=c(function(){b.setMinAndMax(),b.updateHighHandle(b.valueToOffset(b.scope.rzSliderHigh)),b.updateSelectionBar(),b.updateCmbLabel()},350,{leading:!1});this.scope.$watch("rzSliderModel",function(a,b){a!==b&&d()}),this.scope.$watch("rzSliderHigh",function(a,b){a!==b&&e()})},initHandles:function(){this.updateLowHandle(this.valueToOffset(this.scope.rzSliderModel)),this.range&&(this.updateHighHandle(this.valueToOffset(this.scope.rzSliderHigh)),this.updateSelectionBar(),this.updateCmbLabel())},translateFn:function(a,b,c){c=void 0===c?!0:c;var d=this.customTrFn&&c?""+this.customTrFn(a):""+a,e=!1;(void 0===b.rzsv||b.rzsv.length!=d.length)&&(e=!0,b.rzsv=d),b.text(d),e&&this.getWidth(b)},setMinAndMax:function(){this.minValue=this.scope.rzSliderFloor?+this.scope.rzSliderFloor:this.scope.rzSliderFloor=0,this.scope.rzSliderCeil?this.maxValue=+this.scope.rzSliderCeil:this.scope.rzSliderCeil=this.maxValue=this.range?this.scope.rzSliderHigh:this.scope.rzSliderModel,this.valueRange=this.maxValue-this.minValue},initElemHandles:function(){angular.forEach(this.sliderElem.children(),function(a,b){var c=angular.element(a);switch(b){case 0:this.fullBar=c;break;case 1:this.selBar=c;break;case 2:this.minH=c;break;case 3:this.maxH=c;break;case 4:this.flrLab=c;break;case 5:this.ceilLab=c;break;case 6:this.minLab=c;break;case 7:this.maxLab=c;break;case 8:this.cmbLab=c}},this),this.fullBar.rzsl=0,this.selBar.rzsl=0,this.minH.rzsl=0,this.maxH.rzsl=0,this.flrLab.rzsl=0,this.ceilLab.rzsl=0,this.minLab.rzsl=0,this.maxLab.rzsl=0,this.cmbLab.rzsl=0,this.range||(this.cmbLab.remove(),this.maxLab.remove(),this.maxH.remove(),this.selBar.remove())},calcViewDimensions:function(){var a=this.getWidth(this.minH);this.handleHalfWidth=a/2,this.barWidth=this.getWidth(this.fullBar),this.maxLeft=this.barWidth-a,this.getWidth(this.sliderElem),this.sliderElem.rzsl=this.sliderElem[0].getBoundingClientRect().left,this.initRun&&(this.updateCeilLab(),this.initHandles())},updateCeilLab:function(){this.translateFn(this.scope.rzSliderCeil,this.ceilLab),this.setLeft(this.ceilLab,this.barWidth-this.ceilLab.rzsw),this.getWidth(this.ceilLab)},updateFloorLab:function(){this.translateFn(this.scope.rzSliderFloor,this.flrLab),this.getWidth(this.flrLab)},updateHandles:function(a,b){return"rzSliderModel"===a?(this.updateLowHandle(b),this.range&&(this.updateSelectionBar(),this.updateCmbLabel()),void 0):"rzSliderHigh"===a?(this.updateHighHandle(b),this.range&&(this.updateSelectionBar(),this.updateCmbLabel()),void 0):(this.updateLowHandle(b),this.updateHighHandle(b),this.updateSelectionBar(),this.updateCmbLabel(),void 0)},updateLowHandle:function(a){this.setLeft(this.minH,a),this.translateFn(this.scope.rzSliderModel,this.minLab),this.setLeft(this.minLab,a-this.minLab.rzsw/2+this.handleHalfWidth),this.shFloorCeil()},updateHighHandle:function(a){this.setLeft(this.maxH,a),this.translateFn(this.scope.rzSliderHigh,this.maxLab),this.setLeft(this.maxLab,a-this.maxLab.rzsw/2+this.handleHalfWidth),this.shFloorCeil()},shFloorCeil:function(){var a=!1,b=!1;this.minLab.rzsl<=this.flrLab.rzsl+this.flrLab.rzsw+5?(a=!0,this.hideEl(this.flrLab)):(a=!1,this.showEl(this.flrLab)),this.minLab.rzsl+this.minLab.rzsw>=this.ceilLab.rzsl-this.handleHalfWidth-10?(b=!0,this.hideEl(this.ceilLab)):(b=!1,this.showEl(this.ceilLab)),this.range&&(this.maxLab.rzsl+this.maxLab.rzsw>=this.ceilLab.rzsl-10?this.hideEl(this.ceilLab):b||this.showEl(this.ceilLab),this.maxLab.rzsl<=this.flrLab.rzsl+this.flrLab.rzsw+this.handleHalfWidth?this.hideEl(this.flrLab):a||this.showEl(this.flrLab))},updateSelectionBar:function(){this.setWidth(this.selBar,this.maxH.rzsl-this.minH.rzsl),this.setLeft(this.selBar,this.minH.rzsl+this.handleHalfWidth)},updateCmbLabel:function(){var a,b;this.minLab.rzsl+this.minLab.rzsw+10>=this.maxLab.rzsl?(this.customTrFn?(a=this.customTrFn(this.scope.rzSliderModel),b=this.customTrFn(this.scope.rzSliderHigh)):(a=this.scope.rzSliderModel,b=this.scope.rzSliderHigh),this.translateFn(a+" - "+b,this.cmbLab,!1),this.setLeft(this.cmbLab,this.selBar.rzsl+this.selBar.rzsw/2-this.cmbLab.rzsw/2),this.hideEl(this.minLab),this.hideEl(this.maxLab),this.showEl(this.cmbLab)):(this.showEl(this.maxLab),this.showEl(this.minLab),this.hideEl(this.cmbLab))},roundStep:function(a){var b=this.step,c=(a-this.minValue)%b,d=c>b/2?a+b-c:a-c;return+d.toFixed(this.precision)},hideEl:function(a){return a.css({opacity:0})},showEl:function(a){return a.css({opacity:1})},setLeft:function(a,b){return a.rzsl=b,a.css({left:b+"px"}),b},getWidth:function(a){var b=a[0].getBoundingClientRect();return a.rzsw=b.right-b.left,a.rzsw},setWidth:function(a,b){return a.rzsw=b,a.css({width:b+"px"}),b},valueToOffset:function(a){return(a-this.minValue)*this.maxLeft/this.valueRange},offsetToValue:function(a){return a/this.maxLeft*this.valueRange+this.minValue},bindEvents:function(){this.minH.on("mousedown",angular.bind(this,this.onStart,this.minH,"rzSliderModel")),this.range&&this.maxH.on("mousedown",angular.bind(this,this.onStart,this.maxH,"rzSliderHigh")),this.minH.on("touchstart",angular.bind(this,this.onStart,this.minH,"rzSliderModel")),this.range&&this.maxH.on("touchstart",angular.bind(this,this.onStart,this.maxH,"rzSliderHigh"))},onStart:function(a,c,d){d.stopPropagation(),d.preventDefault(),""===this.tracking&&(this.calcViewDimensions(),this.tracking=c,a.addClass("active"),d.touches?(b.on("touchmove",angular.bind(this,this.onMove,a)),b.on("touchend",angular.bind(this,this.onEnd))):(b.on("mousemove",angular.bind(this,this.onMove,a)),b.on("mouseup",angular.bind(this,this.onEnd))))},onMove:function(a,b){var c,d=b.clientX||b.touches[0].clientX,e=this.sliderElem.rzsl,f=d-e-this.handleHalfWidth;return 0>=f?(0!==a.rzsl&&(this.scope[this.tracking]=this.minValue,this.updateHandles(this.tracking,0),this.scope.$apply()),void 0):f>=this.maxLeft?(a.rzsl!==this.maxLeft&&(this.scope[this.tracking]=this.maxValue,this.updateHandles(this.tracking,this.maxLeft),this.scope.$apply()),void 0):(c=this.offsetToValue(f),c=this.roundStep(c),this.range&&("rzSliderModel"===this.tracking&&c>=this.scope.rzSliderHigh?(this.scope[this.tracking]=this.scope.rzSliderHigh,this.updateHandles(this.tracking,this.maxH.rzsl),this.tracking="rzSliderHigh",this.minH.removeClass("active"),this.maxH.addClass("active")):"rzSliderHigh"===this.tracking&&c<=this.scope.rzSliderModel&&(this.scope[this.tracking]=this.scope.rzSliderModel,this.updateHandles(this.tracking,this.minH.rzsl),this.tracking="rzSliderModel",this.maxH.removeClass("active"),this.minH.addClass("active"))),this.scope[this.tracking]!==c&&(this.scope[this.tracking]=c,this.updateHandles(this.tracking,f),this.scope.$apply()),void 0)},onEnd:function(a){this.minH.removeClass("active"),this.maxH.removeClass("active"),a.touches?(b.unbind("touchmove"),b.unbind("touchend")):(b.unbind("mousemove"),b.unbind("mouseup")),this.tracking=""}},d}]).directive("rzslider",["Slider",function(a){return{restrict:"EA",scope:{rzSliderFloor:"=?",rzSliderCeil:"=?",rzSliderStep:"@",rzSliderPrecision:"@",rzSliderModel:"=?",rzSliderHigh:"=?",rzSliderTranslate:"&"},template:'<span class="bar"></span><span class="bar selection"></span><span class="pointer"></span><span class="pointer"></span><span class="bubble limit"></span><span class="bubble limit"></span><span class="bubble"></span><span class="bubble"></span><span class="bubble"></span>',link:function(b,c,d){return new a(b,c,d)}}}]);

angular.module('nucleusApp', ['ngAnimate', 'mgcrea.ngStrap', 'rzModule'])
    .controller('AppCtrl', ['$scope', '$location', '$http', '$timeout', function($scope, $location, $http, $timeout) {

 	$scope.biz_attr = 'organic'

    $scope.biz = {
    	'name':'',
    	'address':'',
    	'website':'',
    	'phone': '',
    	'notes':'',

    	'organic':false,
    	'seasonal_menu':false,
    	'locally_sourced':false,
    	'free_range':false,
    	'grass_fed':false,
    	'no_gmo':false,
    	'gluten_free':false,
    	'vegan':false,
    	// 'veganic': false,
      'raw': false,
    	'composting':false,
    	'bike_parking':false,
    	'leed_certified':false,
    	'renewable_energy':false,
    }


    $scope.attrs = [{
                     'name':'Organic',
                     'prop':'organic'
                    },
    	           {
                    'name':'Seasonal Menu',
                    'prop':'seasonal_menu'
                   },
    	           {'name':'Locally Sourced',
                    'prop':'locally_sourced'},
    	{'name':'Free Range',
         'prop':'free_range'},
    	{'name':'Grass Fed',
         'prop':'grass_fed'},
    	{'name':'noGMO',
         'prop':'no_gmo'},
    	{'name':'Gluten Free',
         'prop':'gluten_free'},
    	{'name':'Vegan',
         'prop':'vegan'},
    	{'name':'Raw', 'prop':'raw'},
    	{'name':'Composting', 'prop':'composting'},
    	{'name':'Bike Parking', 'prop':'bike_parking'},
    	{'name':'LEED Certified', 'prop':'leed_certified'},
    	{'name':'Renewable Energy', 'prop':'renewable_energy'}]


    $scope.set_prop = function(idx) {
        var p = $scope.attrs[idx].prop;
        $scope.biz[p] = !$scope.biz[p]
        console.log($scope.biz)
    }


    $scope.submit_lat_lng = function(lat_lng, biz_key) {
      // console.log('bkey')
      // console.log(biz_key)
      // console.log('submitting lat_lng')
      // console.log(lat_lng)
      var post_obj = {
                        'lat_lng' : lat_lng,
                        'biz_key' : biz_key 
                      }
      $http.post('/biz', post_obj).success(function(data) {
        console.log('location updated');
      });
    }

    $scope.submit_business = function() {
    	$http.post('/biz', $scope.biz).success(function(data) {
    		console.log('submitting biz')
            $scope.radios = false;
             $scope.biz = {
                'name':'',
                'address':'',
                'website':'',
                'phone': '',
                'notes':'',

                'organic':false,
                'seasonal_menu':false,
                'locally_sourced':false,
                'free_range':false,
                'grass_fed':false,
                'no_gmo':false,
                'gluten_free':false,
                'vegan':false,
                // 'veganic': false,
                'raw': false,
                'composting':false,
                'bike_parking':false,
                'leed_certified':false,
                'renewable_energy':false,
            }

    	});
   	}

    

    var geocoder = new google.maps.Geocoder();

    $scope.businesses_counter = 0;
    $scope.businesses_counter_n = 5;


    $scope.save_business_lat_lng = function (b_count) {
        
        for (var i=b_count; i < $scope.businesses_counter_n; i++) {
            $scope.businesses_counter++
            console.log('businesses_counter')
            console.log($scope.businesses_counter)
            console.log($scope.businesses_counter_n)
            var dat = $scope.businesses[i];
            // console.log(dat.key)
            var address = dat.address
            $scope.curr_name = dat.name;
            $scope.location = []
            // console.log(address)
            // console.log(i)
            // console.log(dat.lattitude)
              if (dat.lattitude) {
                console.log('has lattitude')
              } 
              else{

                  geocoder.geocode( {'address': address}, function(dat, i){ 
                            return (function(results, status) {
                                console.log(status)
                                console.log('I inside closure' + i)
                                console.log('biz counter inside closure' +$scope.businesses_counter )
                                console.log($scope.businesses_counter)

                                  if (status == google.maps.GeocoderStatus.OK) {
                                    console.log('address found')
                                        var lat_lng = [results[0].geometry.location.lat(), results[0].geometry.location.lng()] ;
                                        var biz_key = $scope.businesses[i].key;
                                        console.log(biz_key)
                                        $scope.submit_lat_lng(lat_lng, biz_key);
                                    }
                                   else {
                                    console.log("Geocode was not successful for the following reason: " + status)
                                    
                                  }
                              });
                          } (dat, i));

                    
                }
          }

          $scope.businesses_counter_n = $scope.businesses_counter_n + 5;
      }
    function addInfoWindow(map, marker, message) {

            var infoWindow = new google.maps.InfoWindow({
                content: message
            });

            google.maps.event.addListener(marker, 'click', function () {
                infoWindow.open(map, marker);
            });
        }

    $scope.map_made = false;
    $scope.get_businesses = function() {
      $http.get('/biz/' + $scope.biz_attr).success(function(data) {
        $scope.bizes = data
        var values = []
        setTimeout(function () {
            $scope.$apply(function () {
                var mapStyles = [{featureType:'water',elementType:'all',stylers:[{hue:'#d7ebef'},{saturation:-5},{lightness:54},{visibility:'on'}]},{featureType:'landscape',elementType:'all',stylers:[{hue:'#eceae6'},{saturation:-49},{lightness:22},{visibility:'on'}]},{featureType:'poi.park',elementType:'all',stylers:[{hue:'#dddbd7'},{saturation:-81},{lightness:34},{visibility:'on'}]},{featureType:'poi.medical',elementType:'all',stylers:[{hue:'#dddbd7'},{saturation:-80},{lightness:-2},{visibility:'on'}]},{featureType:'poi.school',elementType:'all',stylers:[{hue:'#c8c6c3'},{saturation:-91},{lightness:-7},{visibility:'on'}]},{featureType:'landscape.natural',elementType:'all',stylers:[{hue:'#c8c6c3'},{saturation:-71},{lightness:-18},{visibility:'on'}]},{featureType:'road.highway',elementType:'all',stylers:[{hue:'#dddbd7'},{saturation:-92},{lightness:60},{visibility:'on'}]},{featureType:'poi',elementType:'all',stylers:[{hue:'#dddbd7'},{saturation:-81},{lightness:34},{visibility:'on'}]},{featureType:'road.arterial',elementType:'all',stylers:[{hue:'#dddbd7'},{saturation:-92},{lightness:37},{visibility:'on'}]},{featureType:'transit',elementType:'geometry',stylers:[{hue:'#c8c6c3'},{saturation:4},{lightness:10},{visibility:'on'}]}];

                map = new google.maps.Map(document.getElementById('targetmap'), { 
                   //mapTypeId: google.maps.MapTypeId.ROADMAP,
                   //disableDefaultUI: true,
                   zoom: 4,
                   center: new google.maps.LatLng(37.77493, -122.419416),
                  //zoom: 4,
                  panControl: false,
                  zoomControl: true,
                  scrollwheel: false,
                  scaleControl: true,
                  styles: mapStyles,
                  zoomControlOptions: {
                    style: google.maps.ZoomControlStyle.SMALL,
                    position: google.maps.ControlPosition.RIGHT_BOTTOM
                  }

               });

                $scope.map = map;

              console.log('total businesses')
              console.log(data.length)
              console.log(data)
              $scope.businesses = data;

              for (var i=0; i < data.length; i++) {
                  var dat = data[i];
                  var address = dat.address
                  $scope.curr_name = dat.name;
                  $scope.location = []
                  // console.log(address)
                  // console.log(i)
            

                  if (dat.lattitude) {
                    console.log('saved location')
                    // console.log(dat.lattitude)
                    var marker = new google.maps.Marker({
                          position: new google.maps.LatLng(dat.lattitude, dat.longitude),
                          map: map,
                          title: $scope.curr_name,
                          icon: "img/rsz_greenmarker.png"
                        });

                    var message = dat.name
                    console.log('Message ' + message)
                    addInfoWindow(map, marker, message)
 
                
                  } else {

                    geocoder.geocode( {'address': address}, function(dat, i){ 
                            return (function(results, status) {
                                console.log(status)
                                console.log('I inside closure' + i)
                                console.log('biz counter inside closure' +$scope.businesses_counter )
                                console.log($scope.businesses_counter)

                                  if (status == google.maps.GeocoderStatus.OK) {
                                     var marker = new google.maps.Marker({
                                        position: results[0].geometry.location,
                                        map: map,
                                        title: dat.name,
                                        icon: "img/rsz_greenmarker.png"
                                      });

                                        console.log('address found')
                                        var lat_lng = [results[0].geometry.location.lat(), results[0].geometry.location.lng()] ;
                                        var biz_key = $scope.businesses[i].key;
                                        console.log(biz_key)
                                        $scope.submit_lat_lng(lat_lng, biz_key);
                                    }
                                   else {
                                    console.log("Geocode was not successful for the following reason: " + status)
                                    
                                  }
                              });
                          } (dat, i));
                  
                }
              }
            });
        }, 1000);
        
            console.log('Values')
            console.log(values)


      }); 
    }

    var map = [];

    $scope.filter_results = function(idx) {
        console.log('filtering')
        $scope.biz_attr = $scope.attrs[idx].prop;
        $scope.get_businesses();
    }

    $scope.all_businesses = function() {
      $scope.biz_attr = 'all';
      $scope.get_businesses()
    }
    $scope.all_businesses()


    $scope.radios = false
    $scope.go_on = function() {
        $scope.radios = true
    }    

    $scope.codeAddress = function() {
      var address = $scope.address;
      console.log('Searching Address ' +address)
      geocoder.geocode( { 'address': address}, function(results, status) {
        if (status == google.maps.GeocoderStatus.OK) {
          map.setCenter(results[0].geometry.location);
          map.setZoom(10);
          var marker = new google.maps.Marker({
              map: map,
              position: results[0].geometry.location
          });
        } else {
          alert("Geocode was not successful for the following reason: " + status);
        }
      });
    }




  }])
