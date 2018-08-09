
$( function() {

	login = $( "dialog-form" ).dialog({
		autoOpen: true,
		modal: false,
		closeOnEscape: false,
		draggable: false,
		resizable: false,
		buttons: {
			"Log in": form.submit()
		}
	});

	var form = login.find( "form" ).on( "submit", function( event ) {

		event.preventDefault();

		var valid = validateLogin();

		if ( valid ) {

			var formdata = form.serialize();

			$.post( "/login", formdata, function( response ) {

				if ( response === "failure" ) {

					updateTips( form, "The username or password you entered was incorrect." );
				}
				else if ( response === "toomanyusers" ) {

					updateTips( form, "There are too many current users for you to log on." );
				}
				else {

					$( "html" ).html( response );
				};
			});
		};
	});

	function validateLogin() {

		var valid = true;

		valid = valid && checkRegexp( form.find( "#username" ), /.{30}/, "Username must be less than 30 characters." );
		valid = valid && checkRegexp( form.find( "#password" ), /.{30}/, "Password must be less than 30 characters." );

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