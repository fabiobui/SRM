/* Pannello guida: apertura/chiusura, indice generato dalle sezioni, evidenziazione
   della sezione visibile. Ogni .guide-section dichiara data-title e data-icon. */
(function () {
    "use strict";

    function init(root) {
        var drawer = root.querySelector(".guide-drawer");
        var nav = root.querySelector(".guide-nav");
        var content = root.querySelector(".guide-content");
        if (!drawer || !nav || !content) return;

        var sections = Array.prototype.slice.call(content.querySelectorAll(".guide-section"));
        var buttons = {};

        sections.forEach(function (sec) {
            var btn = document.createElement("button");
            btn.type = "button";
            btn.innerHTML = '<i class="fas ' + (sec.dataset.icon || "fa-circle") + '"></i><span></span>';
            btn.lastChild.textContent = sec.dataset.title || sec.id;
            btn.addEventListener("click", function () { goTo(sec.id); });
            nav.appendChild(btn);
            buttons[sec.id] = btn;
        });

        function setActive(id) {
            Object.keys(buttons).forEach(function (k) {
                buttons[k].classList.toggle("is-active", k === id);
            });
        }

        function goTo(id) {
            var el = content.querySelector("#" + id);
            if (!el) return;
            content.scrollTo({ top: el.offsetTop - content.offsetTop - 8, behavior: "smooth" });
            setActive(id);
        }

        content.addEventListener("scroll", function () {
            var current = sections[0] && sections[0].id;
            var top = content.scrollTop + content.offsetTop + 40;
            sections.forEach(function (sec) { if (sec.offsetTop <= top) current = sec.id; });
            if (content.scrollTop + content.clientHeight >= content.scrollHeight - 4 && sections.length) {
                current = sections[sections.length - 1].id;
            }
            setActive(current);
        });

        function open(id) {
            root.classList.add("guide-open");
            document.body.classList.add("guide-lock");
            drawer.setAttribute("aria-hidden", "false");
            if (id) { setTimeout(function () { goTo(id); }, 50); }
            else { content.scrollTop = 0; setActive(sections[0] && sections[0].id); }
            var close = drawer.querySelector(".guide-close");
            if (close) close.focus();
        }

        function close() {
            root.classList.remove("guide-open");
            document.body.classList.remove("guide-lock");
            drawer.setAttribute("aria-hidden", "true");
        }

        root.querySelectorAll("[data-guide-open]").forEach(function (el) {
            el.addEventListener("click", function () { open(el.getAttribute("data-guide-open") || null); });
        });
        root.querySelectorAll("[data-guide-close]").forEach(function (el) {
            el.addEventListener("click", close);
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && root.classList.contains("guide-open")) close();
        });
    }

    function boot() {
        document.querySelectorAll("[data-guide-root]").forEach(init);
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();
