
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

			"Resume scan": function() {

				$.post( "/scanstatus", JSON.stringify( currentstatus ), function( response ) {}, "json");

				intervalid = setInterval( getscanstatus, 10000 );
				warning.dialog( "close" );
			},
			"Cancel scan": function() {}
		},
		classes: {

			"ui-dialog": "ui-corner-all no-close",
			"ui-dialog-titlebar": "ui-corner-all"
		}
	});

	$( window ).on( "unload", function( e ) {

		$.get( "/logout", "logging out", function( response ) {});
	});

	var currentstatus = {};

	function getscanstatus() {

		$.get( "/scanstatus", function( response ) {

			currentstatus = response

			if ( currentstatus["code"] !== "ok") {

				clearInterval( interval_id );

				if (currentstatus["code"] === "timeout") {

					warning.html("<p>The telescope timed out during movement. It may be blocked or damaged.</p><p>Please check the telescope before continuing.</p>");

					warning.dialog( "option", "buttons", 
						[{
							text: "Cancel scan",
							click: function() {

								$.post( "/scanstatus", JSON.stringify( currentstatus ), function( response ) {}, "json");

								$.post( "/dequeuescan", currentstatus["id"], function( response ) {});

								interval_id = setInterval( getscanstatus, 10000 );
								warning.dialog( "close" );
							}
						}]);
				}
				else {

					if (currentstatus["code"] === "schedulefailed") {

						warning.html("<p>The scan could not be added to the schedule.</p><p>Check the schedule to make sure there is a time slot large enough for the scan, and check that the path of the scan is valid.</p>");
					}
					else if (currentstatus["code"] === "invalidparam") {

						warning.html("<p>One or more of the scan's parameters are invalid.</p><p>Please check that all entered parameters are valid.</p>");
					}
					else {

						warning.html("<p>An unknown error occurred. Please retry the last action.</p><p>If the problem persists, please contact ___</p>");
					};

					warning.dialog( "option", "buttons",
						[{
							text: "Ok",
							click: function() {

								$.post( "/scanstatus", JSON.stringify( currentstatus ), function( response ) {}, "json");

								interval_id = setInterval( getscanstatus, 10000 );
								warning.dialog( "close" );
							}
						}]);
				};

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
