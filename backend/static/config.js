$( function() {

	// initial setup
	var dialog, tips = $( ".validateTips" )

	var sourcelistTemplate = 	`<tr class="entry">
									<td id="name">Name</td>
									<td id="gallat">Gallat</td>
									<td id="gallon">Gallon</td>
									<td><span class="ui-icon ui-icon-circle-close close">Remove source</span></td>
								</tr>`

	tips.hide();

	// sets up jquery ui accordion element
	accordion = $( "#accordion" ).accordion({
		heightStyle: "content",
		create: function( event, ui ) {

			$.post( "/getconfig", "nameloc", function( response ) {

				populateTable( $( "#nameloc" ), JSON.parse( response ) );

			});
		}
	});

	// sets up buttons that submit config parameters to the server
	$( ".update" ).on( "click", function( event ) {

		var section = $( event.target ).closest( "div" ).find( "table" );

		if ( validateParams( section ) ) {

			section.find( "input" ).removeClass( "ui-state-error" );
			tips.hide();
			updateConfig( section );
		};
	});

	// sets up jquery ui buttons
	$( "button" ).button();

	// sets up jquery ui dialog form for adding sources
	dialog = $( "#dialog-form" ).dialog({
		autoOpen: false,
		modal: true,
		buttons: {
			"Add source": addSource,
			Cancel: function() {

				$( "#dialog-form .validateTips" ).hide();
				dialog.dialog( "close" );
			}
		},
		close: function() {

			$( "#dialog-form input[type=text], textarea").val("");
			$( "#dialog-form input" ).removeClass( "ui-state-error" );
		}
	});

	// sets up button that opens the dialog form for adding sources
	$( "#addsource" ).on( "click" , function() {

		dialog.find( ".validateTips" ).show();
		dialog.dialog( "open" );
	});

	// sets up automatic data updates when switching accordion divisions
	accordion.on( "accordionbeforeactivate", function( event, ui ) {

		var section = $( ui.newPanel ).find( "table" );

		if ( section.attr( "id" ) !== "sourcelist") {

			$.post( "/getconfig", section.attr( "id" ), function( response ) {

				populateTable( section, response );

			}, "json");
		}
		else {

			$.post( "/sources", function( response ) {

				updateList( response );

			}, "json");
		};
	});

	// reveals page contents after jquery ui objects have been set up
	$( "#hiddenonstart" ).show();


	/*
		Function that sends source data from the dialog form to be added to the station's database.
	*/
	function addSource() {

		$( "#dialog-form .validateTips" ).show();

		if ( validateSource() ) {

			var sourcevalues = { "name": dialog.find( "#name" ).val(), "gallat": dialog.find( "#gallat" ).val(), "gallon": dialog.find( "#gallon" ).val() };

			var sourcejson = JSON.stringify( sourcevalues );

			$.post( "/uploadsource", sourcejson, function( response ) {

				updateList( response );

			}, "json");

			dialog.dialog( "close" );

		}
	}

	/*
		Function that populates source list table with source data from the server.
	*/
	function updateList( listdata ) {

		$( "#sourcelist" ).find( "tbody" ).empty();

		for ( var i = 0; i < listdata.length; i++ ) {

			var newentry = sourcelistTemplate;
			newentry = $( newentry );

			newentry.find( "#name" ).html( listdata[i]["name"] );
			newentry.find( "#gallat" ).html( listdata[i]["gallat"] );
			newentry.find( "#gallon" ).html( listdata[i]["gallon"] );

			$( "#sourcelist" ).find( "tbody" ).append( newentry );
		};

		// set event listeners on the close icons of each row
		$( ".close" ).on( "click", function() {

			var sourcename = $( this ).closest( ".entry" ).find( "#name" ).html();

			removeSource( sourcename );
		});
	}

	/*
		Function that removes a source from the source list based on its name.
	*/
	function removeSource( sourcename ) {

		$.post( "/removesource", sourcename, function( response ) {

			updateList( response );

		}, "json");
	}

	/*
		Function that sends new config parameters to the server.
	*/
	function updateConfig( section ) {

		var sectionvalues = section.find( "input" );

		var update = [ section.attr( "id" ) ];

		for ( var i = 0; i < sectionvalues.length; i++ ) {

			update.push( $( sectionvalues[i] ).val() );
		};

		var updatejson = JSON.stringify( update );

		$.post( "/updateconfig", updatejson, function( response ) {

			populateTable( section, response );

		}, "json" );
	}

	/*
		Function that populates config data tables with data from the server.
	*/
	function populateTable( table, data ) {

		var fields = table.find( "input" );

		for ( var i = 0; i < fields.length; i++ ) {

			$( fields[i] ).val( data[i] );
		};
	}

	/*
		Function for validating source data before sending it to the server.
	*/
	function validateSource() {

		var valid = true;

		valid = valid && checkRegexp( dialog.find( "#name" ), /.{1,30}/, "Name must be no more than 30 characters long." );
		valid = valid && checkRegexp( dialog.find( "#gallat" ), /-?[0-9]+\.?[0-9]*/, "Latitude must be a real number." ) && checkSize( dialog.find( "#gallat" ), "latitude", -90, 90 );
		valid = valid && checkRegexp( dialog.find( "#gallon" ), /[0-9]+\.?[0-9]*/, "Longitude must be a real number." ) && checkSize( dialog.find( "#gallon" ), "longitude", 0, 360 );

		return valid;
	}

	function validateParams( table ) {

		valid = true;

		if ( table.attr( "id" ) === "nameloc" ) {

			valid = valid && checkRegexp( table.find( "#name" ), /.{1,100}/, "Name must be no more that 100 characters long." );
			valid = valid && checkRegexp( table.find( "#lat" ), /-?[0-9]+\.?[0-9]*/, "Latitude must be a real number." ) && checkSize( table.find( "#lat" ), "latitude", -90, 90 );
			valid = valid && checkRegexp( table.find( "#lon" ), /[0-9]+\.?[0-9]*/, "Longitude must be a real number." ) && checkSize( table.find( "#lon" ), "longitude", 0, 360 );
			valid = valid && checkRegexp( table.find( "#height" ), /[0-9]+\.?[0-9]*/, "Height must be a positive real number." ) && checkSize( table.find( "#height" ), "height", 0, 10000 );
		}
		else if ( table.attr( "id" ) === "movelimits" ) {

			valid = valid && checkRegexp( table.find( "#azlower" ), /[0-9]+\.?[0-9]*/, "Azimuth must be a positive real number." ) && checkSize( table.find( "#azlower" ), "azimuth", 0, 360 );
			valid = valid && checkRegexp( table.find( "#azupper" ), /[0-9]+\.?[0-9]*/, "Azimuth must be a positive real number." ) && checkSize( table.find( "#azupper" ), "azimuth", 0, 360 );
			valid = valid && checkRegexp( table.find( "#allower" ), /[0-9]+\.?[0-9]*/, "Altitude must be a positive real number." ) && checkSize( table.find( "#allower" ), "altitude", 0, 180 );
			valid = valid && checkRegexp( table.find( "#alupper" ), /[0-9]+\.?[0-9]*/, "Altitude must be a positive real number." ) && checkSize( table.find( "#alupper" ), "altitude", 0, 180 );
		}
		else {

			valid = valid && checkRegexp( table.find( "#freqlower" ), /[0-9]+\.?[0-9]*/, "Frequency must be a positive real number." ) && checkSize( table.find( "#freqlower" ), "frequency", 0, 10000 );
			valid = valid && checkRegexp( table.find( "#frequpper" ), /[0-9]+\.?[0-9]*/, "Frequency must be a positive real number." ) && checkSize( table.find( "#frequpper" ), "frequency", 0, 10000 );
		};

		return valid;
	}

	// helper function that evaluates regular expressions and updates the dialog display
	function checkRegexp( o, regexp, n ) {

		if ( !( regexp.test( o.val() ) ) ) {

			o.addClass( "ui-state-error" );
			updateTips( o, n );
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
			updateTips( o, "Value of " + n + " must be between " + min + " and " + max + "." );
			return false;
		}
		else {

			return true;
		};
	}

	// displays tips when users give bad input
	function updateTips( o, t ) {

		var tipbox = o.closest( "div" ).find( ".validateTips" )

		tipbox.show();

		tipbox.text( t ).addClass( "ui-state-highlight" );

		setTimeout( function() {
			tipbox.removeClass( "ui-state-highlight", 1500 );
		}, 500 );
	}

});