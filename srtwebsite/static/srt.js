
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

	warning = $( "#warning" ).dialog({

		autoOpen: false,
		modal: true,
		closeOnEscape: false,
		buttons: {

			"Resume": function() {

				$.post( "/scanstatus", JSON.stringify( currentstatus ), function( response ) {}, "json");

				intervalid = setInterval( getscanstatus, 10000 );
				warning.dialog( "close" );
			}
		},
		classes: {

			"ui-dialog": "ui-corner-all no-close",
			"ui-dialog-titlebar": "ui-corner-all"
		}
	});

	$( window ).on( "unload", function( event ) {

		$.get( "/logout", "logging out", function( response ) {});
		
		event.returnValue = "logged out"
	});

	var currentstatus = {};

	function getscanstatus() {

		$.get( "/scanstatus", function( response ) {

			currentstatus = response

			if ( currentstatus["code"] !== "ok") {

				clearInterval( interval_id );

				if (currentstatus["code"] === "timeout") {

					warning.html("<p>The telescope timed out during movement. It may be blocked or damaged.</p><p>Please check the telescope before resuming.</p>");
				}

				warning.dialog( "open" );
			};

		}, "json")
	}

	/*
		Function to refresh sidebar information. Uses an ajax request to get the data
		and populates the status box with info.
	*/
	function refreshSidebar() {

		$.post( "/status", function( response ) {
			
			$( "#az" ).text( "Az: " + response["az"] );
			$( "#al" ).text( "Al: " + response["al"] );
			
			if ( response['status'] === "noactive" ) {
				
				$( "#scaninfo" ).hide();
				$( "#noactive" ).show();
				
			}
			else {
				
				$( "#noactive" ).hide();
				$( "#scaninfo" ).show();
	
				var bar = $( ".statusbar" );

				bar.find( "#name" ).html( "Name: " + response["name"] );
				bar.find( "#starttime" ).html( "Start: " + response["starttime"] );
				bar.find( "#endtime" ).html( "End: " + response["endtime"] );
			};
			
		}, "json");
	}

	/*
		Gets initial sidebar data and sets the sidebar to automatically refresh every 30 seconds.
	*/
	refreshSidebar();
	setInterval( refreshSidebar, 30000 );
	getscanstatus();
	var interval_id = setInterval( getscanstatus, 10000 );

});
