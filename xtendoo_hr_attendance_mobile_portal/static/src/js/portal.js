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
        var toggle = document.getElementById("mp-loc-toggle");
        var hint = document.getElementById("mp-loc-hint");
        var STORE_KEY = "mp_share_location";
        var permission = "prompt";

        function loadPref() {
            try {
                return window.localStorage.getItem(STORE_KEY) !== "0";
            } catch (e) {
                return true;
            }
        }

        function savePref(value) {
            try {
                window.localStorage.setItem(STORE_KEY, value ? "1" : "0");
            } catch (e) { /* private mode: keep it for this page only */ }
        }

        function renderHint() {
            var key = "loc-off";
            if (toggle.checked) {
                key = permission === "denied" ? "loc-blocked"
                    : permission === "granted" ? "loc-granted" : "loc-on";
            }
            hint.textContent = t(key);
            hint.className = "mp-hint" + (toggle.checked && permission === "denied" ? " mp-warn" : "");
        }

        function askPermission() {
            // One single reading, triggered by the employee turning the switch
            // on, only to make the browser show its permission dialog. The
            // coordinates are discarded: nothing is stored or sent.
            if (!navigator.geolocation || permission === "granted") {
                return;
            }
            hint.textContent = t("loc-asking");
            navigator.geolocation.getCurrentPosition(
                function () {
                    permission = "granted";
                    renderHint();
                },
                function (err) {
                    if (err && err.code === 1) {
                        permission = "denied";
                    }
                    renderHint();
                },
                {enableHighAccuracy: false, timeout: 10000, maximumAge: 0}
            );
        }

        toggle.checked = loadPref();
        toggle.addEventListener("change", function () {
            savePref(toggle.checked);
            renderHint();
            if (toggle.checked) {
                askPermission();
            }
        });
        // Read-only query of the permission state; it never triggers a prompt.
        if (navigator.permissions && navigator.permissions.query) {
            navigator.permissions.query({name: "geolocation"}).then(function (status) {
                permission = status.state;
                status.onchange = function () {
                    permission = status.state;
                    renderHint();
                };
                renderHint();
            }).catch(function () {});
        }
        renderHint();
        var checkedIn = root.dataset.checkedIn === "1";

        function say(text, kind) {
            message.textContent = text;
            message.className = "mp-message" + (kind ? " mp-" + kind : "");
        }

        function render() {
            button.textContent = t(checkedIn ? "label-out" : "label-in");
            button.className = "mp-btn-round " + (checkedIn ? "mp-btn-out" : "mp-btn-in");
            status.textContent = t(checkedIn ? "status-in" : "status-out");
            status.className = "mp-pill " + (checkedIn ? "mp-in" : "mp-out");
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
            var share = toggle.checked;
            say(share ? t("locating") : "", "info");
            var action = checkedIn ? "check_out" : "check_in";
            // Sharing off: geolocation is not even requested.
            (share ? getPosition() : Promise.resolve({status: "declined"})).then(function (geo) {
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
                    var why = result.geo.status;
                    text += ". " + t(why === "denied" || why === "declined" ? why : "unavailable");
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
