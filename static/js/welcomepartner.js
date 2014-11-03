
var STATIC_SHARED = '/static';
var WelcomePartnerApp = angular.module('WelcomePartnerApp', ['ngRoute'])
  .config(function($routeProvider, $locationProvider) {
    // $routeProvider.when('/welcome', {
    //     templateUrl: 'index.html',
    //     controller: 'NoPartner'
    //   });
    $routeProvider.when('/welcome/:partnerId', {
        templateUrl: STATIC_SHARED + '/welcome.html',
        controller: 'WelcomePartner'
      });
   
    // configure html5 to get links working on jsfiddle
    $locationProvider.html5Mode(true);
  })


  WelcomePartnerApp.controller('WelcomePartner', ['$route', '$location', '$scope', '$routeParams', '$http', '$timeout', function($route, $location, $scope, $routeParams, $http, $timeout){
    $scope.$route = $route;
    $scope.$location = $location;
    $scope.$routeParams = $routeParams;
    console.log('parnter id')
    console.log($location.path())
    console.log($routeParams.partnerId)
    $scope.parnter_name = $scope.$routeParams.partnerId

    $scope.form = {full_name:'', email:'', phone:'', company:'', message:''}

    $http.get('/partners/info/' + $scope.parnter_name).success(function(partner_data){
      console.log(partner_data)
      $scope.partner_data = partner_data
      $('#header-logo').attr('src', partner_data.data.logo_url)
      $scope.partner_id = $scope.partner_data.data.partner_id
      $scope.partner_email = partner_data.data.email
    }).error(function(){
      location.href= "/"
    })

    $scope.submit_form = function(){
      
      console.log('parnter_id' + $scope.partner_id)
      var count = 0;
      for (a in $scope.form){
        if(!$scope.form[a]){
          console.log('false')
          $scope.form_message = 'Please fill out from';
          break;
        }else{
          console.log('true')
          count++
          $scope.form_message = 'Submitting your message...'
        }
      }

      if(count >= 4){
        $http.post('/partners/outbound/email/' + $scope.partner_id + '/' + $scope.partner_email, $scope.form).success(function(data){
          console.log(data)
          if(data.status === 'success'){
            $scope.form_message = 'Thanks, your message has been sent!'
            for (a in $scope.form){
              $scope.form[a] = ''
            }
          }
        }).error(function(){
          console.log('500 server error')
            $scope.form_message = '500 Server error. Please try again.'
        })
      }


    }



  }]);