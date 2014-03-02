$('.sidebar-section-link img').on("click", function(event) {
	if ($(event.target).attr("src").indexOf("25b8166") > 0) {
		console.log("first");
		window.t = $(event.target);
		var i = 0; 
		window.setTimeout(function(){
			$(event.target).attr("src", "//cdn.optimizely.com/img/30013095/29c7852288f54b79803e2804c2050482.gif");
		}, 5);
	} else {
		console.log("second");
		window.t = $(event.target);
		var i = 0; 
		window.setTimeout(function(){
			$(event.target).attr("src", "//cdn.optimizely.com/img/30013095/f28c908ab02041ecae39f73b425b8166.gif")
		}, 5);
	}
});
