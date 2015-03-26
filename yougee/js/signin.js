app = angular.module('signinApp', ['ngAnimate', 'mgcrea.ngStrap', 'nucleusAPIConfig'])

app.controller('signinCtrl', ['$scope', '$location', '$http',  function($scope, $location, $http) {

	$scope.error_msg = false;

	$scope.signin = function() {
		$scope.loading = true;
		$scope.error_msg = false;
		var post_data = {
							'email': $scope.email,
							'password': $scope.password
						}
		
		$http.post('/adnucleus/signin', post_data).success(function(data){ 
			console.log(data)
						
				window.location = '/nucleus/index.html'
		}).error(function(data) {
			$scope.loading = false;
			$scope.error_msg = data.description;
		})

	}

	$scope.create_new_password = function() {

		var post_data = {
							'token': $scope.token,
							'email': $scope.email,
							'password': $scope.password,
							'confirm_password': $scope.confirm_password
						}
						
		$http.post('/adnucleus/createnewpassword', post_data).success(function(data){ 
			console.log(data)
			window.location = '/nucleus/signin/signin.html'
		}).error(function(data) {
			$scope.error_msg = data.description;		
		})	
	}


	$scope.email_password_token = function() {
		$scope.error_msg = false;

		var post_data = {
							'email': $scope.email
						}
		$http.post('/adnucleus/passwordtoken', post_data).success(function(data){ 
			console.log(data)
			$scope.show_sent = true;
		}).error(function(data) {
			console.log('error baby!')
			$scope.error_msg = 'Please check your email and connection and try again.';	
		})
	}


}]);
