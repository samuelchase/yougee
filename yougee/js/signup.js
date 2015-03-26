app = angular.module('signupApp', ['ngAnimate', 'mgcrea.ngStrap', 'nucleusAPIConfig'])

app.controller('signupCtrl', ['$scope', '$location', '$http',  function($scope, $location, $http) {

	$scope.is_error = false;
	$scope.error_msg = false;
	$scope.verifying = false;

	$scope.find_email = function() {
		$scope.error_msg = false;
		$scope.verifying = true;
		$scope.token_bg = '#ddd';
		console.log("token " + $scope.token)
		$http.get('/adnucleus/emailfortoken/' + $scope.token).success(function(data){ 
			console.log(data)
			$scope.user = data;
			$scope.email = data.contact_email;

	        setTimeout(function () {
	            $scope.$apply(function () {
	            	$scope.token_bg = null;
	                $scope.valid_token = true;
	                $scope.verifying = false;
	                setTimeout(function () {
	                	$('#password').focus();
	                }, 500);
	                
	            });
	        }, 1700);

		}).error(function(data){

	        setTimeout(function () {
	            $scope.$apply(function () {
	            	$scope.error_msg = 'This token is invalid.  Please request another token.';
	            	$scope.token_bg = null;
	                $scope.verifying = false;
	            });
	        }, 1700);

		})
	}

	$scope.valid_token = false;
	$scope.password = '';

	$scope.signup = function() {

		console.log('email ')
		console.log($scope.email)
		console.log('password')
		console.log($scope.password)
		console.log('confirm password')
		console.log($scope.confirm_password)
		$scope.error_msg = false;

		if ($scope.password == '' || $scope.password.length < 7) {
			$scope.error_msg = "Password needs to be a least 8 characters"
			return;
		}

		if ($scope.password == $scope.confirm_password) {

			var post_data = {
								'email':$scope.email,
								'password': $scope.password,
								'confirm_password':$scope.password,
								'token':$scope.token,
							}

			$scope.creating_account = true;
			$http.post('/api/v1/nucleus/signup', post_data).success(function(data){ 
				console.log(data)
				$scope.account_created = true;
				$scope.creating_account = false;

			}).error(function(data){ 
				
				console.log(data)
				$scope.creating_account = false;
				$scope.error_msg = data.description;
				
			})
		} else {
			$scope.is_error = true
			$scope.error_msg = "Please confirm your password matches"
		}
		
	}


	$scope.get_signup_info = function() {
		$http.get('/adnucleus/approvedstats').success(function(data){ 
			console.log(data)
			$scope.signups = data.signups;
			$scope.approved = data.approved;
			$scope.accounts = data.accounts;

		})
	}

	$scope.get_signup_info();


}]);
