$(function() {

	/*
		Event listener for the navigation bar, making an ajax request for page contents
		and pasting them into the corrent locations.
	*/
	$( ".navmenu" ).on( "click", "div", function( event ) {

		if ( $( ".navmenu" ).find( ".current" )[0] !== event.target ) {

			$( ".navmenu" ).find( ".current" ).toggleClass( "current" );

			$( event.target ).toggleClass( "current" );

			// user clicked on home tab, get home page
			if ( event.target.id === "home") {
				
				$.get( "/home", function( response ) {

					$( "#replace" ).remove();
					$( "main" ).html( response );
					$( "p:empty" ).remove();
				});
			}

			// user clicked on config tab, get config page
			else if ( event.target.id === "config" ) {

				$.get( "/config", function( response ) {

					$( "main" ).empty().append( $( response ).find( "#content").html() );
					$( "#replace" ).remove();
					$( "head" ).append( $( response ).find( "#script" ).html() );
					$( "head" ).append( $( response ).find( "#style" ).html() );
					$( "p:empty" ).remove();
				});
			}

			// user clicked on scan tab, get scan page
			else {

				$.get( "/scan", function( response ) {

					$( "main" ).empty().append( $( response ).find( "#content").html() );
					$( "#replace" ).remove();
					$( "head" ).append( $( response ).find( "#script" ).html() );
					$( "head" ).append( $( response ).find( "#style" ).html() );
					$( "p:empty" ).remove();
				});
			};
		};
	});

	/*
		Event listeners to style nav menu boxes on mouseover.
	*/
	$( ".navmenu" ).on( "mouseleave", "div", function( event ) {

		event.target.style.boxShadow = "0px 0px 0px 0px rgba(0, 0, 0, 0.7)";
	});
	$( ".navmenu" ).on( "mouseenter", "div", function( event ) {

		event.target.style.boxShadow = "0px 0px 1px 1px rgba(0, 0, 0, 0.7)";
	});

	/*
		Function to refresh sidebar information. Uses an ajax request to get the data
		and populates the status box with info.
	*/
	function refreshSidebar() {

		$.post( "/status", function( response ) {

			$( "#az" ).text( "Az: " + response["config"]["az"] );
			$( "#al" ).text( "Al: " + response["config"]["al"] );

			var currentscan = response["scanqueue"];

			if ( currentscan["type"] === "track" ) {

				$( ".statusbar" ).find( "#source" ).text( "Source: " + currentscan["source"] );
				$( ".statusbar" ).find( "#drift" ).hide();
				$( ".statusbar" ).find( "#source" ).show();
			}
			else {

				$( ".statusbar" ).find( "#source" ).hide();
				$( ".statusbar" ).find( "#drift" ).show();
				$( ".statusbar" ).find( "#lat" ).text( "Lat: " + currentscan["lat"] );
				$( ".statusbar" ).find( "#lon" ).text( "Lon: " + currentscan["lon"] );
			};

			$( ".statusbar" ).find( "#center" ).text( "Center: " + currentscan["center"] + " MHz" );
			
			}, "json" );
	}

	/*
		Gets initial sidebar data and sets the sidebar to automatically refresh every 30 seconds.
	*/
	refreshSidebar();
	setInterval( refreshSidebar, 30000 );

});