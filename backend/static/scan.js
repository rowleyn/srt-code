$( function() {
	
	// initial setup
	var dialog,	tips = $( ".validateTips" ),
		type = $( "#dialog-form #type" ), duration = $( "#dialog-form #duration" ), center = $( "#dialog-form #center" ), step_num = $( "#dialog-form #step-num" ), step_size = $( "#dialog-form #step-size" ),
		name = $( "#dialog-form #name" ), position = $( "#dialog-form #position" ), lat = position.find( "#lat" ), lon = position.find( "#lon" ), source = $( "#dialog-form #source" ), sourcelist = $( "#dialog-form #sourcelist" );

	var allFields = $( [] ).add( type ).add( duration ).add( center ).add( step_num ).add( step_size).add( name ).add( lat ).add( lon ).add( sourcelist )

	position.hide();
	source.show();

	// a template for adding new rows to the queue table
	var scanlistTemplate = `<tr class="entry">
								<td id="name">Name</td>
								<td id="type">Type</td>
								<td id="source-pos"><div id="sourcename"></div><div id="lat"></div><div id="lon"></div></td>
								<td id="duration">Duration</td>
								<td id="center">Center</td>
								<td><span class="ui-icon ui-icon-circle-close close">Remove/End Scan</span></td>
								<td hidden id="id"></td>
							</tr>`


	/*
		Sets up the jquery ui dialog form for adding new scans.
	*/
	dialog = $( "#dialog-form" ).dialog({
		autoOpen: false,
		modal: true,
		buttons: {
			"Queue scan": queueScan,
			Cancel: function() {

				dialog.dialog( "close" );
			}
		},
		close: function() {

			$( "input[type=text], textarea").val("");
			if ( type.val() === "drift" ) {

				position.hide();
				source.show();
				type.val( "track" );
			};
			allFields.removeClass( "ui-state-error" );
			tips.text( "All fields are mandatory." );
		}
	});

	// set up button for opening the dialog form
	$( "#create-scan" ).button().on( "click", function() {

		$.post( "/sources", function( response ) {

			sourcelist.html( "<option value='no source'>Select source</option>");

			for (var i = 0; i < response.length; i++) {

				sourcelist.append( "<option>" + response[i]['name'] + "</option>");
			};
			
		}, "json");

		dialog.dialog( "open" );
	});

	// set up dynamic changing of the form based on selected scan type
	type.on( "change", function( event ) {

		if ( type.val() === "track" ) {

			position.hide();
			source.show();
			$( lat, "textarea" ).val("");
			$( lon, "textarea" ).val("");
		}
		else {

			$( "#tracktype" ).val( "source" );
			source.hide();
			position.show();
			sourcelist.val( "no source" );
		};
	});

	$( "#tracktype" ).on( "change", function( event ) {

		if ( $( "#tracktype" ).val() === "source" ) {

			position.hide();
			sourcelist.show();
			$( lat, "textarea" ).val("");
			$( lon, "textarea" ).val("");
		}
		else {

			sourcelist.hide();
			position.show();
			sourcelist.val( "no source" );
		};
	});

	// reveals page contents after jquery ui objects have been set up
	$( "#hiddenonstart" ).show();

	// start running self-recursive loop() function to update scan queue
	loop();


	// simple function for generating random numbers
	function getRndInteger(min, max) {

	    return Math.floor(Math.random() * (max - min) ) + min;
	}

	/*
		Builds json containing a new scan populated from the jquery ui dialog form.
		Posts the new scan to the server using ajax. 
	*/
	function queueScan() {

		// generate an id for the scan
		var randid = getRndInteger(1,1000000000000)

		// make sure position is not undefined if it is unused
		if ( $( "#tracktype" ).val() === "source" ) {

			position.find( "#lat" ).val( 0 );
			position.find( "#lon" ).val( 0 );
		}

		// submit form if it is valid
		if ( validateForm() ) {

			// build javascript object with scan parameters
			var scanvalues = { "name": name.val(), "type": type.val(), "source": sourcelist.val(), "lat": lat.val(), "lon": lon.val(),
								"duration": duration.val(), "center": center.val(), "stepnumber": step_num.val(), "stepsize": step_size.val(), "id":randid };

			// convert javascript object to json
			var scanjson = JSON.stringify( scanvalues );

			// ajax post request uploading the scan
			// uses the response to update the queue table
			$.post( "/uploadscan", scanjson, function( response ) {

				updateQueue( response );

			}, "json");

			// close the dialog form
			dialog.dialog( "close" );
		}
	}

	/*
		Populates the queue table with data received from the server.
	*/
	function updateQueue( queuedata ) {

		// clear the table for repopulation
		$( "#queued-scans tbody" ).empty();

		// build a new table row from the template and scan params
		for ( var i = 0; i < queuedata.length; i++ ) {

			var newentry =  scanlistTemplate;
			newentry = $( newentry );
			newentry.find( "#name" ).html( queuedata[i]["name"] );
			newentry.find( "#type" ).html( queuedata[i]["type"] );
			if ( queuedata[i]["type"] === "track" ) {

				if ( queuedata[i]["source"] === "no source" ) {

					newentry.find( "#source-pos" ).find( "#lat" ).html( "Gal. lat: " + queuedata[i]["lat"] );
					newentry.find( "#source-pos" ).find( "#lon" ).html( "Gal. lon: " + queuedata[i]["lon"] );
				}
				else {

					newentry.find( "#source-pos #sourcename" ).html( queuedata[i]["source"] );
				}
			}
			else {

				newentry.find( "#source-pos" ).find( "#lat" ).html( "Gal. lat: " + queuedata[i]["lat"] );
				newentry.find( "#source-pos" ).find( "#lon" ).html( "Gal. lon: " + queuedata[i]["lon"] );
			};
			newentry.find( "#duration" ).html( queuedata[i]["duration"] );
			newentry.find( "#center" ).html( queuedata[i]["center"] );
			newentry.find( "#id" ).html( queuedata[i]["id"] );

			// append the new row to the table
			$( "#queued-scans tbody" ).append( newentry );
		};

		// set event listeners on the close icons of each row
		$( ".close" ).on( "click", function() {

			var scanid = $( this ).closest( ".entry" ).find( "#id" ).html();

			removeScan( scanid );
		});

	}

	/*
		Function for validating scan form data.
	*/
	function validateForm() {

		var valid = true;
		allFields.removeClass( "ui-state-error" );

		if ( type.val() === "track" ) {

			if ( $("#tracktype" ).val() === "source" ) {

				if ( sourcelist.val() === "no source" ) {

					updateTips( "Must select a source." );
					valid = false;
				};
			}
			else {

				valid = valid && checkRegexp( lat, /-?[0-9]+\.?[0-9]*/, "Latitude must be a real number." ) && checkSize( lat, "latitude", -90, 90 );
				valid = valid && checkRegexp( lon, /[0-9]+\.?[0-9]*/, "Longitude must be a real number." ) && checkSize( lon, "longitude", 0, 360 );
			};
		}
		else {

			valid = valid && checkRegexp( lat, /-?[0-9]+\.?[0-9]*/, "Latitude must be a real number." ) && checkSize( lat, "latitude", -90, 90 );
			valid = valid && checkRegexp( lon, /[0-9]+\.?[0-9]*/, "Longitude must be a real number." ) && checkSize( lon, "longitude", 0, 360 );
		}

		valid = valid && checkRegexp( duration, /[0-9]{2}h[0-9]{2}m[0-9]{2}s/, "Duration must be in the form '00h00m00s'." );
		valid = valid && checkRegexp( center, /[0-9]+\.?[0-9]*/, "Center frequency must be a real number." ) && checkSize( center, "center frequency", 0, 10000 );
		valid = valid && checkRegexp( step_num, /[0-9]+/, "Step number must be a positive integer." ) && checkSize( step_num, "step number", 1, 1000000 );
		valid = valid && checkRegexp( step_size, /[0-9]+\.?[0-9]*/, "Step size must be a position real number." ) && checkSize( step_size, "step size", 0.04, 100 );
		valid = valid && checkRegexp( name, /.{1,30}/, "Name must be no more than 30 characters long." );

		return valid;
	}

	// helper function that evaluates regular expressions and updates the dialog display
	function checkRegexp( o, regexp, n ) {

		if ( !( regexp.test( o.val() ) ) ) {

			o.addClass( "ui-state-error" );
			updateTips( n );
			return false;
		}
		else {

			return true;
		};
	}

	// helper function that checks the size of a number and updates the dialog display
	function checkSize( o, n, min, max ) {

		if ( o.val() < min || o.val() > max ) {

			o.addClass( "ui-state-error" );
			updateTips( "Value of " + n + " must be between " + min + " and " + max + "." );
			return false;
		}
		else {

			return true;
		};
	}

	// displays tips when users give bad form input
	function updateTips( t ) {
		tips.text( t ).addClass( "ui-state-highlight" );

		setTimeout( function() {
			tips.removeClass( "ui-state-highlight", 1500 );
		}, 500 );
	}

	/*
		Ajax request to get scan queue from the server and update the table.
	*/
	function getQueue() {

		$.post( "/queue", function( response ) {

			updateQueue( response );

		}, "json" );
	}

	/*
		Ajax request to remove a scan from the queue and update the table
		with the new queue.
	*/
	function removeScan( id ) {

		$.post( "/removescan", id, function( response ) {

			updateQueue( response );

		}, "json");
	}

	/*
		Gets the initial queue data and sets the table to automatically refresh every 10 seconds.
		Naturally stops execution after the scan page is left.
	*/
	function loop() {

		getQueue();

		if ( $( ".navmenu .current" )[0] === $( ".navmenu #scan")[0] ) {

			setTimeout( loop, 10000 );
		};
	}

});