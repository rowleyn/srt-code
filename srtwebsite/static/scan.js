
$( function() {
	
	// initial setup
	var scandialog,	searchdialog, tips = $( ".validateTips" ),
		type = $( "#dialog-scanform #type" ), duration = $( "#dialog-scanform #duration" ), freqlower = $( "#dialog-scanform #freqlower"), frequpper = $( "#dialog-scanform #frequpper" ),
		name = $( "#dialog-scanform #name" ), position = $( "#dialog-scanform #position" ), ras = position.find( "#ras" ), dec = position.find( "#dec" ),
		step_num = $( "#dialog-scanform #stepnum" ), source = $( "#dialog-scanform #source" ), sourcelist = source.find( "#sourcelist" );

	var allFields = $( [] ).add( type ).add( duration ).add( freqlower ).add( frequpper ).add( step_num ).add( name ).add( ras ).add( dec ).add( sourcelist );

	position.hide();
	source.show();

	// template for adding new rows to the queue table
	var scanlistTemplate = `<tr class="entry">
								<td id="name">Name</td>
								<td id="type">Type</td>
								<td id="source-pos"><div id="sourcename"></div><div id="ras"></div><div id="dec"></div></td>
								<td id="times"><div id="start"></div><div id="end"></div></td>
								<td id="freqrange"><div id="freqlower"></div><div id="frequpper"></div></td>
								<td><span class="ui-icon ui-icon-circle-close close">Cancel Scan</span></td>
								<td hidden id="id"></td>
							</tr>`;

	// template for adding new scans to the search list
	var searchlistTemplate = 	`<tr class="entry">
									<td><input type="checkbox"></td>
									<td id="scanname">name</td>
									<td id="date">00/00/00</td>
									<td hidden id="id"></id>
								</tr>`;


	var historylistTemplate = 	`<tr class="history-entry">
									<td id="name">Name</td>
									<td id="type">Type</td>
									<td id="date">Date</td>
									<td id="status">Success</td>
								</tr>`;


	/*
		Sets up the jquery ui dialog form for adding new scans.
	*/
	scandialog = $( "#dialog-scanform" ).dialog({
		autoOpen: false,
		modal: true,
		buttons: {
			"Submit scan": submitScan,
			Cancel: function() {

				scandialog.dialog( "close" );
			}
		},
		close: function() {

			$( "input[type=text], textarea" ).val("");
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

			sourcelist.html( "<option value='no source'>Select source</option><option value='sun'>Sun</option>");

			for (var i = 0; i < response.length; i++) {

				sourcelist.append( "<option>" + response[i]['name'] + "</option>");
			};
			
		}, "json");

		scandialog.dialog( "open" );
	});

	// set up dynamic changing of the form based on selected scan type
	type.on( "change", function( event ) {

		if ( type.val() === "track" ) {

			source.find( "#tracktype" ).val( "source" );
			sourcelist.val( "no source" );
			position.hide();
			source.show();
			sourcelist.show();
		}
		else {

			$( ras, "textarea" ).val("");
			$( dec, "textarea" ).val("");
			source.hide();
			position.show();
		};
	});

	source.find( "#tracktype" ).on( "change", function( event ) {

		if ( source.find( "#tracktype" ).val() === "source" ) {

			sourcelist.val( "no source" );
			position.hide();
			sourcelist.show();
		}
		else {

			$( ras, "textarea" ).val("");
			$( dec, "textarea" ).val("");
			sourcelist.hide();
			position.show();
		};
	});

	$( "#search-scans" ).button().on( "click", function() {

		searchdialog.dialog( "open" );
	});

	searchdialog = $( "#dialog-searchform" ).dialog({
		width: 800,
		height: 500,
		autoOpen: false,
		modal: true,
		open: function() {

			$( "#dialog-searchform .validateTips" ).hide();
		},
		close: function() {

			$( "input[type=text], textarea" ).val( "" );
			$( "#dialog-searchform #year" ).val( "any" );
			$( "#dialog-searchform #month" ).val( "any" );
			$( "#search-results tbody" ).html( "<tr><td></td><td></td><td></td>></tr>" );
			$( "#download" ).button( "disable" );
			$( "#delete" ).button( "disable" );
			$( "#dialog-searchform #name" ).removeClass( "ui-state-error" );			
		}
	});

	$( "#dialog-searchform #search" ).button().on( "click", function( event ) {

		event.preventDefault();
		searchScans();
	});

	$( "#dialog-searchform #download" ).button().on( "click", function( event ) {

		event.preventDefault();
		var checkedentries = $( "#search-results tbody .entry" ).has( "input:checked" );
		if ( checkedentries.length !== 0 ) {

			var scanids = [];

			for ( var i = 0; i < checkedentries.length; i++ ) {

				scanids.push( $( checkedentries[i] ).find( "#id" ).html() );
			};

			var listjson = JSON.stringify( scanids );

			fetch( "/downloadscans", { method: "POST", cache: "no-store", body: listjson } ).then( function( response ) {

				response.blob().then( function( blob ) {

					var link = document.createElement( "a" );
					link.href = window.URL.createObjectURL( blob );
					link.download = "scans.zip";

					document.body.appendChild( link );

					link.click();

					document.body.removeChild( link );

					window.URL.revokeObjectURL( blob );	
				});
			});
		};
	});

	$( "#dialog-searchform #delete" ).button().on( "click", function( event ) {

		event.preventDefault();
		var checkedentries = $( "#search-results tbody .entry" ).has( "input:checked" );
		if( checkedentries.length !== 0 ) {

			var scanids = [];

			for ( var i = 0; i < checkedentries.length; i++ ) {

				scanids.push( $( checkedentries[i] ).find( "#id" ).html() );
			};

			var listjson = JSON.stringify( scanids );

			$.post( "/deletescans", listjson, function( response ) {

				checkedentries.remove();

			}, "json");
		};
	});

	$( "#dialog-searchform #checkall" ).on( "click", function() {

		if ( $( "#checkall:checked" ).length !== 0 ) {

			$( "#search-results tbody .entry input:not(:checked)" ).prop( "checked", true );
		}
		else {

			$( "#search-results tbody .entry input:checked" ).prop( "checked", false );
		};
	});

	// reveals page contents after jquery ui objects have been set up
	$( "#hiddenonstart" ).show();

	// start running self-recursive loop() function to update scan queue
	loop();

	function updateHistory() {

		$.post( "/gethistory", function( response ) {

			$( "#scan-history tbody" ).empty();

			for ( var i = 0; i < response.length; i++ ) {

				var newentry = historylistTemplate;
				newentry = $( newentry );
				newentry.find( "#name" ).html( response[i]["name"] );
				newentry.find( "#type" ).html( response[i]["type"] );
				newentry.find( "#date" ).html( response[i]["date"] );
				newentry.find( "#status" ).html( response[i]["status"] );

				if ( response[i]["status"] === "complete" ) {

					newentry.find( "#status" ).addClass( "success" );
				}
				else {

					newentry.find( "#status" ).addClass( "failure" );
				};

				$( "#scan-history tbody" ).append( newentry );
			};

		}, "json");
	}

	function searchScans() {

		var valid = true;

		valid = valid && checkRegexp( $( "#dialog-searchform #name" ), /^.{0,30}$/, "Name must be no more than 30 characters long." );

		$( "#dialog-searchform .validateTips" ).show();

		if ( valid ) {

			var searchparams = { "name": $( "#dialog-searchform #name" ).val(), "month": $( "#dialog-searchform #month" ).val(), "year": $( "#dialog-searchform #year" ).val() };

			var searchjson = JSON.stringify( searchparams );

			$.post( "/searchscans", searchjson, function( response ) {

				updateSearchlist( response );

			}, "json");

		};
	}

	function updateSearchlist( scanlist ) {

		$( "#search-results tbody" ).empty();

		for ( var i = 0; i < scanlist.length; i++ ) {

			var newentry = searchlistTemplate;
			newentry = $( newentry );
			newentry.find( "#scanname" ).html( scanlist[i]["name"] );
			newentry.find( "#date" ).html( scanlist[i]["date"] );
			newentry.find( "#id" ).html( scanlist[i]["id"] );

			// append the new row to the table
			$( "#search-results tbody" ).append( newentry );
		};
	}

	/*
		Builds json containing a new scan populated from the jquery ui dialog form.
		Posts the new scan to the server using ajax. 
	*/
	function submitScan() {

		// make sure position is not undefined if it is unused
		if ( type.val() === "track" && $( "#tracktype" ).val() === "source" ) {

			ras.val( "0h0m0s" );
			dec.val( "0d0m0s" );
		}

		// submit form if it is valid
		if ( validateForm() ) {

			// build javascript object with scan parameters
			var scanvalues = { "name": name.val(), "type": type.val(), "source": sourcelist.val(), "ras": ras.val(), "dec": dec.val(),
								"duration": duration.val(), "freqlower": freqlower.val(), "frequpper": frequpper.val(), "stepnumber": step_num.val()};

			// convert javascript object to json
			var scanjson = JSON.stringify( scanvalues );

			// ajax post request uploading the scan
			// uses the response to update the queue table
			$.post( "/submitscan", scanjson, function( response ) {

				updateSchedule( response );

			}, "json");

			// close the dialog form
			scandialog.dialog( "close" );
		}
	}

	/*
		Populates the acive and schedule tables with data received from the server.
	*/
	function updateSchedule( scheduledata ) {

		// clear the tables for repopulation
		$( "#scheduled-scans tbody" ).empty();
		$( "#active-scan tbody" ).empty();

		var active_set = false;

		// build a new table row from the template and scan params
		for ( var i = 0; i < scheduledata.length; i++ ) {

			var newentry = scanlistTemplate;
			newentry = $( newentry );
			newentry.find( "#name" ).html( scheduledata[i]["name"] );
			newentry.find( "#type" ).html( scheduledata[i]["type"] );
			if ( scheduledata[i]["type"] === "track" ) {

				if ( scheduledata[i]["source"] !== "no source" ) {

					newentry.find( "#source-pos #sourcename" ).html( "Source: " + scheduledata[i]["source"] );
				}
			}
			newentry.find( "#source-pos" ).find( "#ras" ).html( "RA: " + scheduledata[i]["ras"] );
			newentry.find( "#source-pos" ).find( "#dec" ).html( "Dec: " + scheduledata[i]["dec"] );
			newentry.find( "#times" ).find( "#start" ).html( "Start: " + scheduledata[i]["starttime"] );
			newentry.find( "#times" ).find( "#end" ).html( "End: " + scheduledata[i]["endtime"] );
			newentry.find( "#freqrange" ).find( "#freqlower" ).html( "Min freq: " + scheduledata[i]["freqlower"] );
			newentry.find( "#freqrange" ).find( "#frequpper" ).html( "Max freq: " + scheduledata[i]["frequpper"] );
			newentry.find( "#id" ).html( scheduledata[i]["id"] );

			// display the first scan in the queue as the active scan
			if ( !active_set ) {

				if ( scheduledata[i]['current'] === true ) {

					$( "#active-scan tbody" ).append( newentry );

					$( "#active-scan .close" ).on( "click", function() {

						var scanid = $( this ).closest( ".entry" ).find( "#id" ).html();

						descheduleScan( scanid );
					});
				}
				else {
					
					$( "#scheduled-scans tbody" ).append( newentry );
				}

				active_set = true;
			}
			// display the rest of the scans as the queue
			else {
				
				$( "#scheduled-scans tbody" ).append( newentry );
			};
		};

		// set event listeners on the close icons of each row
		$( "#scheduled-scans .close" ).on( "click", function() {

			var scanid = $( this ).closest( ".entry" ).find( "#id" ).html();

			descheduleScan( scanid );
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

				valid = valid && checkRegexp( ras, /^0*(?:[0-9]|1\d|2[0-3])h0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s$|^0*24h0+m0+s$/, "Right ascension must be specified in sidereal time." );
				valid = valid && checkRegexp( dec, /^-?0*(?:[0-9]|[1-8]\d)d0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s$|^-?0*90d0+m0+s$/, "Declination must be between 90 and -90 degrees." )
			};
		}
		else {

			valid = valid && checkRegexp( ras, /^0*(?:[0-9]|1\d|2[0-3])h0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s$|^0*24h0+m0+s$/, "Right ascension must be specified in sidereal time." );
			valid = valid && checkRegexp( dec, /^-?0*(?:[0-9]|[1-8]\d)d0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s$|^-?0*90d0+m0+s$/, "Declination must be between 90 and -90 degrees." )
		}

		valid = valid && checkRegexp( duration, /^0*[0-7]h0*(?:[0-9]|[1-5]\d)m0*(?:[0-9]|[1-5]\d)s$|^0*8h0+m0+s$/, "Duration must be eight hours or less." );
		valid = valid && checkRegexp( freqlower, /^[0-9]+\.?[0-9]*$/, "Minimum frequency must be a real number." ) && checkSize( freqlower, "minimum frequency", 0, 10000 );
		valid = valid && checkRegexp( freqlower, /^[0-9]+\.?[0-9]*$/, "Maximum frequency must be a real number." ) && checkSize( freqlower, "maximum frequency", 0, 10000 );
		valid = valid && checkRegexp( step_num, /^[1-9][0-9]*$/, "Step number must be a positive integer." ) && checkSize( step_num, "step number", 1, 1000000 );
		valid = valid && checkRegexp( name, /^.{1,30}$/, "Name must be no more than 30 characters long." );

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
		Ajax request to get scan schedule from the server and update the table.
	*/
	function getSchedule() {

		$.post( "/schedule", function( response ) {

			updateSchedule( response );

		}, "json" );
	}

	/*
		Ajax request to remove a scan from the schedule and update the table
		with the new schedule.
	*/
	function descheduleScan( id ) {

		$.post( "/deschedulescan", id, function( response ) {

			updateSchedule( response );

		}, "json");
	}

	/*
		Gets the initial queue data and sets the table to automatically refresh every 10 seconds.
		Naturally stops execution after the scan page is left.
	*/
	function loop() {

		getSchedule();
		updateHistory();

		if ( $( ".navmenu .current" )[0] === $( ".navmenu #scan")[0] ) {

			setTimeout( loop, 10000 );
		};
	}

});
