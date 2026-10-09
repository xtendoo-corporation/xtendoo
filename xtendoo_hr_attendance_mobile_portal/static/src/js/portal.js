/* Mobile punch portal. Plain JS, no dependencies.
 * Geolocation is requested ONLY when the employee presses the punch button
 * (one single getCurrentPosition call, never watchPosition). */
(function () {
    "use strict";

    function t(key) {
        var el = document.querySelector('#mp-i18n [data-key="' + key + '"]');
        return el ? el.textContent : "";
    }

    function initPunch() {
        var root = document.getElementById("mp-home");
        if (!root) {
            return;
        }
        var button = document.getElementById("mp-punch");
        var message = document.getElementById("mp-message");
        var status = document.getElementById("mp-status");
        var last = document.getElementById("mp-last");
        var csrf = root.dataset.csrf;
        var checkedIn = root.dataset.checkedIn === "1";

        function say(text, kind) {
            message.textContent = text;
            message.className = "mp-message" + (kind ? " mp-" + kind : "");
        }

        function render() {
            button.textContent = t(checkedIn ? "label-out" : "label-in");
            button.className = "mp-btn mp-btn-big " + (checkedIn ? "mp-btn-out" : "mp-btn-in");
            status.textContent = t(checkedIn ? "status-in" : "status-out");
            status.className = "mp-status " + (checkedIn ? "mp-in" : "mp-out");
        }

        function getPosition() {
            // Resolves {status, coords}. Never rejects.
            return new Promise(function (resolve) {
                if (!navigator.geolocation) {
                    resolve({status: "unsupported"});
                    return;
                }
                navigator.geolocation.getCurrentPosition(
                    function (pos) {
                        resolve({status: "ok", coords: pos.coords});
                    },
                    function (err) {
                        var status = "unavailable";
                        if (err && err.code === 1) {
                            status = "denied";
                        } else if (err && err.code === 3) {
                            status = "timeout";
                        }
                        resolve({status: status});
                    },
                    {enableHighAccuracy: true, timeout: 15000, maximumAge: 0}
                );
            });
        }

        button.addEventListener("click", function () {
            if (button.disabled) {
                return;
            }
            button.disabled = true;
            say(t("locating"), "info");
            var action = checkedIn ? "check_out" : "check_in";
            getPosition().then(function (geo) {
                var body = new URLSearchParams();
                body.set("csrf_token", csrf);
                body.set("action", action);
                body.set("geo_status", geo.status);
                if (geo.status === "ok") {
                    body.set("latitude", geo.coords.latitude);
                    body.set("longitude", geo.coords.longitude);
                    body.set("accuracy", geo.coords.accuracy);
                }
                return fetch("/fichaje/marcar", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {"Content-Type": "application/x-www-form-urlencoded"},
                    body: body.toString(),
                }).then(function (response) {
                    return response.json().then(function (data) {
                        return {data: data, geo: geo};
                    });
                });
            }).then(function (result) {
                var data = result.data;
                if (!data.ok) {
                    say(data.error === "unauthorized" ? t("error") : (data.error || t("error")), "error");
                    return;
                }
                checkedIn = data.checked_in;
                last.textContent = data.last_label || "—";
                render();
                var text = t(checkedIn ? "in" : "out");
                if (!data.geo) {
                    // Be explicit: it was recorded, but without location.
                    text += ". " + t(result.geo.status === "denied" ? "denied" : "unavailable");
                    say(text, "warning");
                } else {
                    say(text, "success");
                }
            }).catch(function () {
                say(t("error"), "error");
            }).then(function () {
                button.disabled = false;
            });
        });
    }

    function initInstall() {
        var box = document.getElementById("mp-install");
        if (!box) {
            return;
        }
        var standalone = window.matchMedia("(display-mode: standalone)").matches
            || window.navigator.standalone === true;
        if (standalone) {
            return;
        }
        box.hidden = false;
        var btn = document.getElementById("mp-install-btn");
        var deferred = null;
        // Only offered when the browser decides to fire the event.
        window.addEventListener("beforeinstallprompt", function (event) {
            event.preventDefault();
            deferred = event;
            btn.hidden = false;
        });
        btn.addEventListener("click", function () {
            if (deferred) {
                deferred.prompt();
                deferred = null;
                btn.hidden = true;
            }
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        initPunch();
        initInstall();
    });
})();
