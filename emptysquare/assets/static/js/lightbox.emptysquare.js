/* include Felix Hagspiel's jsOnlyLightbox first:
 * https://github.com/felixhagspiel/jsOnlyLightbox
 */

document.addEventListener("DOMContentLoaded", function () {
  var imgs = document.querySelectorAll("div.post-content img");
  for (var i = 0; i < imgs.length; i++) {
    imgs[i].setAttribute('data-jslghtbx', '');
    imgs[i].setAttribute('data-jslghtbx-group', 'group');
  }

  var onload = function (ev) {
    if (!ev) {
      /* lightbox opened */
      var navs = [
        document.getElementsByClassName("jslghtbx-prev")[0],
        document.getElementsByClassName("jslghtbx-next")[0],
        document.getElementsByClassName("jslghtbx-close")[0]];

      var showNavs = function () {
        for (var i = 0; i < navs.length; i++) {
          navs[i].style.visibility = 'visible';
        }
      };

      var hideNavs = function () {
        for (var i = 0; i < navs.length; i++) {
          navs[i].style.visibility = 'hidden';
        }
      };

      showNavs();

      var timedOut = false;
      setTimeout(function () {
        timedOut = true;
        hideNavs();
      }, 1000);

      var overlay = document.getElementById('jslghtbx');
      var mouseTimeout = 0;

      function mouseMove() {
        showNavs();
        if (mouseTimeout) {
          clearTimeout(mouseTimeout);
          mouseTimeout = 0;
        }

        mouseTimeout = setTimeout(function() {
          hideNavs();
          mouseTimeout = 0;
        }, 1000);
      }

      overlay.onmousemove = mouseMove;
    }
  };

  var lightbox = new Lightbox();
  lightbox.load({dimensions: false, maxImgSize: .98, onload: onload});
});
