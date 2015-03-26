  $scope.initial_advertiser = function() {
      $http.get('/api/v1/nucleus/initialadv').success(function(data){
        $scope.advertiser_key = data.data;
        $scope.advertiser = data.advertiser
        $scope.nucleus_camps = [];
        if (data.nucleus_camps) {
            $scope.nucleus_camps = data.nucleus_camps;
        }
        
        $scope.nucleus_camp_keys = Object.keys($scope.nucleus_camps)
        $scope.nflights = []
        $scope.campaign_rollup = []
        for (var i = 0; i < $scope.nucleus_camp_keys.length; i++) {
            var k = $scope.nucleus_camp_keys[i];
            var total_impressions = 0;
            var date_created = 'No Date Found'
            var tag_flights = []
            for (var z = 0; z < $scope.nucleus_camps[k].length; z++) {
                total_impressions = total_impressions + $scope.nucleus_camps[k][z].max_views;
                date_created = $scope.nucleus_camps[k][z].date_created;
                tag_flights.push($scope.nucleus_camps[k][z])
                $scope.nflights.push({'name':$scope.nucleus_camps[k][z].name,
                                     'status':'pre-flight',  //This needs to be real
                                     'ad_type': 'Mobile Display', //This needs to be real
                                     'start_date':'2011/02/13',
                                     'impressions':$scope.nucleus_camps[k][z].max_views,
                                    })
            }
            var num_flights = tag_flights.length
            var rollup = {
                         'number':i,
                         'name':k,
                         'num_flights':num_flights,
                         'impressions':total_impressions,
                         'date_created':date_created, 
                        }
            $scope.campaign_rollup.push(rollup)
        }
      })