window.addEventListener("load", function() {
  var areas = document.getElementsByTagName('area');
  var image = document.querySelector('.background-image');
  function updateAreaCoords() {
    var imageWidth = image.offsetWidth;
    var imageHeight = image.offsetHeight;
  
    // loop through the areas and update their coordinates
    for (var i = 0; i < areas.length; i++) {
      var coords = areas[i].getAttribute('data-coord').split(',');
      var pixelCoords = '';
  
      for (var j = 0; j < coords.length; j++) {
        if (j % 2 === 0) {
          // convert x coordinate from percentage to pixel value
          var xPercent = parseInt(coords[j]);
          var xPixel =(xPercent / 100000 * imageWidth);
          pixelCoords += xPixel + ',';
        } else {
          // convert y coordinate from percentage to pixel value
          var yPercent = parseInt(coords[j]);
          var yPixel =(yPercent / 100000 * imageHeight);
          pixelCoords += yPixel;
  
          // add comma between x and y coordinates, except for the last y coordinate
          if (j !== coords.length - 1) {
            pixelCoords += ',';
          }
        }
      }
      // set the pixel coordinates as the new value of the coords attribute
      areas[i].setAttribute('coords', pixelCoords);
    }
  };
  updateAreaCoords(); // update once on page load

 
})
window.addEventListener("resize", function() {
  updateAreaCoords(); // update on window resize
});
window.addEventListener("load", function() {
  var video = document.querySelector('.video-embedded');
  var image = document.querySelector('.background-image');

  function updateVideoCoords() {
    var imageWidth = image.offsetWidth;
    var imageHeight = image.offsetHeight;
    var offsetLeft = image.offsetLeft;
    var offsetTop = image.offsetTop;

    var coords = video.getAttribute('data-coord').split(',');
    var pixelCoords = '';

    for (var j = 0; j < coords.length; j++) {
      if (j % 2 === 0) {
        // convert x coordinate from percentage to pixel value
        var xPercent = parseInt(coords[j]);
        var xPixel =((xPercent / 100000 * imageWidth) + offsetLeft);
        pixelCoords += xPixel + ',';
      } else {
        // convert y coordinate from percentage to pixel value
        var yPercent = parseInt(coords[j]);
        var yPixel =((yPercent / 100000 * imageHeight) + offsetTop);
        pixelCoords += yPixel;

        // add comma between x and y coordinates, except for the last y coordinate
        if (j !== coords.length - 1) {
          pixelCoords += ',';
        }
      }
    }

    // set the pixel coordinates as the new value of the coords attribute
    video.style.left = pixelCoords.split(',')[0] + 'px';
    video.style.top = pixelCoords.split(',')[1] + 'px';

    video.style.width = ((coords[2]-coords[0])*imageWidth/100000) + 'px';
    video.style.height = ((coords[3]-coords[1])*imageHeight/100000) + 'px';
  }

  updateVideoCoords(); // update once on page load
});
function openPopup(id) {

  // show the popup container with the matching id
  var popup = document.getElementById('popup-' + id);
  var bgimage = document.querySelector('.background-image');
  var video = document.querySelector('.video-embedded');
  popup.style.display = 'block';
  bgimage.classList.add('background-blur');
  video.classList.add('background-blur');
}


function closePopup(id) {

  // show the popup container with the matching id
  var popup = document.getElementById('popup-' + id);
  var bgimage = document.querySelector('.background-image');
  var video = document.querySelector('.video-embedded');
  popup.style.display = 'none';
  bgimage.classList.remove('background-blur');
  video.classList.remove('background-blur');
}
function openVideo(id) {
  // show the popup container with the matching id
  const container = document.getElementById('video-' + id);
  var bgimage = document.querySelector('.background-image');
  bgimage.classList.add('background-blur');
  container.style.display = 'block';
}



function closeVideo(id) {
  const container = document.getElementById('video-' + id);
  const videoElement = container.querySelector('video');
  var bgimage = document.querySelector('.background-image');
  bgimage.classList.remove('background-blur');
  
  // Pause the video
  videoElement.pause();
  
  // Reset the video to the beginning
  videoElement.currentTime = 0;
  
  // Hide the video container
  container.style.display = 'none';
}
