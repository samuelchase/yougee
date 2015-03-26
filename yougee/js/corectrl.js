app = angular.module('nucleusApp', ['ngAnimate', 'mgcrea.ngStrap', 'ngTagsInput', 'nucleusAPIConfig'])
  .filter('approved', function() {
    return function(input, approved) {
      input = input || '';
      var out = "";
      for (var i = 0; i < input.length; i++) {
        out = input.charAt(i) + out;
      }
      // conditional based on optional argument
      if (uppercase) {
        out = out.toUpperCase();
      }
      return out;
    };
  })



app.controller('CoreCtrl', ['$scope', '$location', '$http', '$timeout', 'nucleusReporting', function($scope, $location, $http, $timeout, nucleusReporting) {

    $scope.mypage='clientlist';
    $scope.clients = [];
    $scope.approved = [];
    $scope.waitlist = [];
    $scope.revoked = [];

    //$scope.current_user = {status:'not-approved', 'date_created':'Jan 15th, 2014', 'Spot in Line'}

    $scope.scroll_to_userinfo = function() {
        var element_top = $scope.get_position(document.getElementById('userinfo'))[0] - 30;
        $('#fullpage').animate({
            scrollTop: element_top
        }, 666, 'swing');
        console.log('scrolling to ' + element_top)
    }


    $scope.scroll_to_top = function() {
        $('#fullpage').animate({
            scrollTop: 0
        }, 666, 'swing');
    }

    $scope.show_clients = function(idx) {
        if (idx == 'clients') {
            $scope.show_list = $scope.clients;
        }
        if (idx == 'approved') {
            $scope.show_list = $scope.approved;
        }
        if (idx == 'waitlist') {
            $scope.show_list = $scope.waitlist;
        }
        if (idx == 'revoked') {
            $scope.show_list = $scope.revoked;
        }
    }

    $scope.get_position = function(node) {     

        var top = left = 0;
        while (node) {      
           if (node.tagName) {
               top = top + node.offsetTop;
               left = left + node.offsetLeft;       
               node = node.offsetParent;
           } else {
               node = node.parentNode;
           }
        } 
        return [top, left];

    }

    $scope.manual_entry = function() {
        $scope.manual = true;
        $scope.show_clients('waitlist')
        $http.post('/adnucleus/naras?email=' + $scope.invite_email,{}).success(function(data){
            $scope.manual = false;
            alert('Email added and invite sent! :)');
            $scope.invite_email = ''
            $scope.reload_waitlist();
        });   
    }

    $scope.approve_waitlist = function(idx) {
        $scope.current_user = $scope.show_list[idx];
        $scope.approve_current_user();
        // $http.post('/adnucleus/approve?email=' + $scope.show_list[idx].contact_email, {}).success(function(data){
        //     $scope.reload_waitlist();
        // });
    }

    $scope.invoice_nadv = function() {
      $http.get('/adnucleus/advertiser/' + $scope.current_user.contact_email + '/invoiced').success(function(data) {
        $scope.current_user.invoiced = data.invoiced;
      });
    }

    $scope.revoke_membership = function(idx) {
        $scope.show_clients('revoked')
        $http.post('/adnucleus/approve?revoke=true&email=' + $scope.current_user.contact_email, {revoke_reason:$scope.revoke_reason}).success(function(data){
            $scope.reload_waitlist();
        });
    }

    $scope.set_current_user = function(idx) {
        $scope.current_user = $scope.show_list[idx];
        $scope.scroll_to_userinfo();
    }

    $scope.approve_current_user = function(idx) {
        $scope.approving = true;
        $http.post('/adnucleus/approve?email=' + $scope.current_user.contact_email, {}).success(function(data){
            $scope.approving = false;
            $scope.reload_waitlist();
            $scope.current_user.approved = true;
        });
    }

    $scope.reload_waitlist = function() {
        $http.get('/adnucleus/naras').success(function(data){
            $scope.clients = data.data;
            $scope.approved = [];
            $scope.waitlist = [];
            $scope.revoked = [];

            for (var i in $scope.clients) {
                
                if ($scope.clients[i].revoke_date) {
                    $scope.revoked.push($scope.clients[i])
                } 
                if ($scope.clients[i].approved) {
                    $scope.approved.push($scope.clients[i])
                }
                if (!$scope.clients[i].approved && !$scope.clients[i].revoke_date) {
                    $scope.waitlist.push($scope.clients[i])
                } 

            }

            if ($scope.current_user) {
                for (var i in $scope.clients) {
                    if ($scope.clients[i].contact_email == $scope.current_user.contact_email) {
                        console.log('updating current user ' + $scope.clients[i].email);
                        $scope.current_user = $scope.clients[i];
                    }
                }
            } else {
                $scope.current_user = $scope.clients[0];
            }

            if (!$scope.show_list) {
                $scope.show_list = $scope.clients;
            }
            
        });
    }

    $scope.reload_waitlist();

    setTimeout(function () {
        $scope.$apply(function () {
            $scope.ready = true;
            //alert('ready!')
        });
    }, 500); 

  }])
