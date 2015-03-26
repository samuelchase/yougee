

var total_events = events.length

$scope.batch_send_events = function(events, batch_size) {}

	var post_data = events.slice(0, batch_size)
	var rem_events = events.slice(batch_size-1, events.length)
	$http.post('/events/batch', post_data).success(function(data){
		total_events = total_events - batch_size;
		$scope.batch_send_events(rem_events, batch_size);

  	}).error(function(data){
  		console.log('Batch Post Failed Retrying...')
  		$scope.batch_send_events(events, batch_size);
  	});
}
