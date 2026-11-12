// Click-to-play YouTube trailer.
// Nothing is loaded from YouTube until the visitor presses play: the page shows a local
// thumbnail, and only a click swaps in YouTube's privacy-enhanced player
// (youtube-nocookie.com). Without JavaScript the thumbnail is a normal link to YouTube.
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  function play(link) {
    var id = link.getAttribute("data-youtube");
    if (!id || !/^[A-Za-z0-9_-]{6,20}$/.test(id)) return false;
    var frame = document.createElement("iframe");
    frame.src = "https://www.youtube-nocookie.com/embed/" + id +
      "?autoplay=1&rel=0&playsinline=1&modestbranding=1";
    frame.title = link.getAttribute("data-title") || "Trailer";
    frame.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    frame.allowFullscreen = true;
    // The page sends no referrer, but YouTube's player needs to know which site it is on.
    frame.referrerPolicy = "strict-origin-when-cross-origin";
    var box = document.createElement("div");
    box.className = "trailer-frame";
    box.appendChild(frame);
    link.parentNode.replaceChild(box, link);
    frame.focus();
    return true;
  }

  document.addEventListener("click", function (e) {
    var link = e.target.closest && e.target.closest("a[data-youtube]");
    if (!link) return;
    // Let Ctrl/Cmd/Shift/middle clicks open YouTube as usual.
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (play(link)) e.preventDefault();
  });
})();
