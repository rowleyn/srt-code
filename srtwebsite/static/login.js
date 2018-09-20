
$( function() {
	
	var form = $( "#dialog-form" ).find( "form" )

	var login = $( "#dialog-form" ).dialog({
		autoOpen: true,
		modal: false,
		closeOnEscape: false,
		draggable: false,
		resizable: false,
		buttons: {
			"Log in": function() { form.submit() }
		},
		classes: {
			"ui-dialog": "ui-corner-all no-close",
			"ui-dialog-titlebar": "ui-corner-all"
		}
	});

	form.on( "submit", function( event ) {

		var valid = validateLogin();

		if ( !valid ) {

			event.preventDefault()

			//~ $.post( "/login", formdata, function( response ) {

				//~ if ( response === "failure" ) {

					//~ updateTips( form, "The username or password you entered was incorrect." );
				//~ }
				//~ else if ( response === "toomanyusers" ) {

					//~ updateTips( form, "There are too many current users for you to log on." );
				//~ }
				//~ else {

					//~ $( "html" ).html( response );
				//~ };
			//~ });
		};
	});

	function validateLogin() {

		var valid = true;

		valid = valid && checkRegexp( form.find( "#username" ), /^.{1,30}$/, "Username must be less than 30 characters." );
		valid = valid && checkRegexp( form.find( "#password" ), /^.{1,30}$/, "Password must be less than 30 characters." );

		return valid;
	}

	// helper function that evaluates regular expressions and updates the dialog display
	function checkRegexp( object, regexp, message ) {

		if ( !( regexp.test( object.val() ) ) ) {

			object.addClass( "ui-state-error" );
			updateTips( object, message );
			return false;
		}
		else {

			return true;
		};
	}

	// displays tips when users give bad input
	function updateTips( object, message ) {

		var tipbox = object.closest( "div" ).find( ".validateTips" );

		tipbox.show();

		tipbox.text( message ).addClass( "ui-state-highlight" );

		setTimeout( function() {

			tipbox.removeClass( "ui-state-highlight", 1500 );

		}, 500 );
	}
});
