$(document).ready(function() {
    $(".navbar-burger").click(function() {
      $(".navbar-burger").toggleClass("is-active");
      $(".navbar-menu").toggleClass("is-active");
    });

    var options = {
      slidesToScroll: 1,
      slidesToShow: 3,
      loop: true,
      infinite: true,
      autoplay: false,
      autoplaySpeed: 3000,
    }

    var carousels = bulmaCarousel.attach('.carousel', options);
    for(var i = 0; i < carousels.length; i++) {
      carousels[i].on('before:show', state => {
        console.log(state);
      });
    }

    bulmaSlider.attach();
})
