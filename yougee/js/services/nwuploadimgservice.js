'use strict'


  nucleusApp.factory('nwGetUploadUrl', ['$http', function($http){
    return function(){
      var upload_url = $http.get('/media/getuploadurl')
      return upload_url
    }

  }])



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
      var xhr = new XMLHttpRequest();
      xhr.open("POST", upload_url, true);
      xhr.send(fd);
      return xhr
    }
  }])