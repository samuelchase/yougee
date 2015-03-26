var appSubscribe = function () {

    var checkemail = /^((([a-z]|\d|[!#\$%&"\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+(\.([a-z]|\d|[!#\$%&"\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+)*)|((\x22)((((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(([\x01-\x08\x0b\x0c\x0e-\x1f\x7f]|\x21|[\x23-\x5b]|[\x5d-\x7e]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(\\([\x01-\x09\x0b\x0c\x0d-\x7f]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))))*(((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(\x22)))@((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))$/i;

    var breaker = "<br>";

    function bindEvents() {
        $(".subscribe").on("click", function (e) {
            e.preventDefault();
            sendRequest();
        });
    }

    // Render response
    function message(output) {

        $(".response").slideUp(200, "easeInOutExpo");

        var messageBox = "<div class=\"alert alert-dismissable\"><button type=\"button\" class=\"close\" data-dismiss=\"alert\" aria-hidden=\"true\">×</button>" + output + "</div>";

        $(".response").html(messageBox).slideDown(200, "easeInOutExpo");

    }

    function sendRequest() {
        console.log('sending request')
        var email = $("input[name=email]").val(),
            check = $("input[name=check]").val(),
            output = "",
            error = false,
            btn = $("button.subscribe");

        btn.button("loading").parent().addClass("active");

        if (email === "" || email === " ") {
            error = true;
            output += "Please enter your email address" + breaker;
        } else if (!checkemail.test(email)) {
            error = true;
            output += "Invalid email" + breaker;
        }

        if (check.length > 0) {
            error = true;
            output += "Failed to send message" + breaker;
        }

        if (error === false) {
            $.ajax({
                url: $("#subscribeform").attr("action"),
                type: "POST",
                data: $("#subscribeform").serialize(),
                timeout: 8000
            }).done(function (response) {
                output = response;
                $("#subscribeform input").val("");
                if (output == 'email exists') {
                    message('We will let you know as soon as the app arrives!');
                } else {
                    var waiting = parseInt(response)
                    message('Thanks for joining the Yougee community. Stay tuned!');
                }
                
            }).fail(function (response) {

                if (response.responseText !== "" && response.responseText !== " ") {
                    output = response.responseText;
                } else {
                    output = "Please check your internet connection and try again.";
                }

                if (response.statusText === "timeout") {
                    output = "Please check your internet connection and try again.";
                }

                message(output);

                return false;
            })
                .always(function () {
                    btn.button("reset").parent().removeClass("active");
                });
            return false;
        } else {
            if (output === "") {
                output = "Please check your internet connection and try again.";
            }

            message(output);
            btn.button("reset").parent().removeClass("active");
            return false;
        }
    }

    return {
        init: function () {
            bindEvents();
        }
    };
}();

$(function () {
    "use strict";
    appSubscribe.init();
});