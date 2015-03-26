
var hide_main_bg = function($scope) {
   
	var tlt = new TimelineLite();
	var lt2 = $('#loading-terms');
	tlt.to(lt2, .78, {right:0, autoAlpha:0});
   
	var tl = new TimelineLite();
	var bg = $('#init-bg');
	tl.to(bg, .78, {top:60, opacity:1}, "+=.5");
	tl.to(bg, 1, {left:199, opacity:1}, "+=0.17");
	tl.to(bg, 1, {autoAlpha:0, onComplete:draw_first_page, onCompleteParams:[$scope]}, "+=0.17");

	var tl5 = new TimelineLite();
	var nb = $('#neutrino-badge');
	tl5.to(nb, .78, {top:-30, autoAlpha:0}, "+=.5");
    
	var tl3 = new TimelineLite();
	var bg_corner = $('#back-bg');
	tl3.to(bg_corner, .78, {height:60}, "+=.5");
   
	var tl4 = new TimelineLite();
	var bg_under = $('#back-under');
	tl4.to(bg_under, .78, {opacity:1});
  
	var t2 = new TimelineLite();
	var bdg = $('#init-badge');
	t2.to(bdg, 0.5, {top:60, opacity:1}, "+=.5");
	t2.to(bdg, 1, {left:199, width:1, autoAlpha:0}, "+=0.17");

}

var draw_first_page = function($scope) {
	console.log('draw first page')
	var tl = new TimelineLite();
	tl.to($('#start1'), .33, {autoAlpha:1}, "+=0");
	tl.to($('#start2'), .33, {autoAlpha:1}, "-=0.25");
	tl.to($('#start3'), .33, {autoAlpha:1}, "-=0.25");	
}

var current_tag_name = ''

var draw_cards = function(tag_name) {
	if (main_scope.filtered_tags == undefined) {
		return;
	}
	console.log('drawing');
	console.log(tag_name);
	current_tag_name = tag_name;

	var tl = new TimelineLite();
	for (var i=0; i < main_scope.filtered_tags.length; i++) {
		var element_name = '#' + tag_name + '-' + i
		var element = $(element_name)
		if (!element) {
			break;
		}
		tl.to(element, .33, {autoAlpha:0}, "-=.33");
	}

	setTimeout(draw_cards_in, 100);

}

var draw_cards_in = function() {

	var tl = new TimelineLite();
	for (var i=0; i < main_scope.filtered_tags.length; i++) {
		var element_name = '#' + current_tag_name + '-' + i
		var element = $(element_name)
		if (!element) {
			return;
		}
		tl.to(element, .33, {autoAlpha:1}, "-=.25");
	}
}