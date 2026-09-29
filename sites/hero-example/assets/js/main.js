/* pagesmith default scripts - navigation and theme helpers. */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        // Theme toggle: cycles auto -> dark -> light.
        var toggle = document.querySelector(".theme-toggle");
        if (!toggle) {
            return;
        }
        toggle.addEventListener("click", function () {
            var root = document.documentElement;
            var current = root.getAttribute("data-theme");
            if (current === "dark") {
                root.setAttribute("data-theme", "light");
                localStorage.setItem("theme", "light");
            } else if (current === "light") {
                root.removeAttribute("data-theme");
                localStorage.setItem("theme", "auto");
            } else {
                root.setAttribute("data-theme", "dark");
                localStorage.setItem("theme", "dark");
            }
        });
    });
})();
