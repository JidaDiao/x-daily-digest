/* 叼报 PWA 导航：仅在主屏幕独立窗口（无地址栏）里启用。悬浮返回键 + 下拉刷新。无外部依赖。 */
(function () {
  var standalone = window.navigator.standalone === true || (window.matchMedia && matchMedia("(display-mode: standalone)").matches);
  if (!standalone || window.__pwaNav) return;
  window.__pwaNav = 1;
  var isHome = location.pathname === "/" || location.pathname === "/index.html";

  function css() {
    var s = document.createElement("style");
    s.textContent =
      ".pn-back{position:fixed;z-index:2147483000;left:12px;top:calc(env(safe-area-inset-top,0px) + 8px);height:36px;padding:0 14px 0 10px;display:flex;align-items:center;gap:4px;border:0;border-radius:999px;background:rgba(29,29,31,.78);color:#fff;font:600 14px/1 -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);box-shadow:0 4px 14px rgba(0,0,0,.18);-webkit-tap-highlight-color:transparent;transition:transform .2s,opacity .25s}" +
      ".pn-back:active{transform:scale(.94)}.pn-back svg{width:16px;height:16px}" +
      ".pn-ptr{position:fixed;z-index:2147483000;left:50%;top:calc(env(safe-area-inset-top,0px) + 6px);width:36px;height:36px;margin-left:-18px;border-radius:50%;background:#fff;box-shadow:0 4px 16px rgba(0,0,0,.2);display:flex;align-items:center;justify-content:center;opacity:0;transform:translateY(-60px);pointer-events:none}" +
      ".pn-ptr svg{width:18px;height:18px;stroke:#2c76a0;fill:none;stroke-width:2.4;stroke-linecap:round}" +
      ".pn-ptr.spin svg{animation:pn-spin .7s linear infinite}@keyframes pn-spin{to{transform:rotate(360deg)}}";
    document.head.appendChild(s);
  }

  function back() {
    var same = false;
    try { same = document.referrer && new URL(document.referrer).origin === location.origin; } catch (e) {}
    if (same && history.length > 1) history.back(); else location.href = "/";
  }

  function init() {
    css();
    if (!isHome) {
      var b = document.createElement("button");
      b.className = "pn-back"; b.type = "button"; b.setAttribute("aria-label", "返回");
      b.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>返回';
      b.addEventListener("click", back);
      document.body.appendChild(b);
    }
    var ptr = document.createElement("div");
    ptr.className = "pn-ptr";
    ptr.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.5-5.8"/><path d="M20 4v5h-5"/></svg>';
    document.body.appendChild(ptr);

    var y0 = null, x0 = 0, dy = 0, TH = 72, busy = false;
    function top() { return (window.pageYOffset || document.documentElement.scrollTop || 0) <= 0; }
    function blocked(t) {
      for (var n = t; n && n !== document.body; n = n.parentNode) {
        if (n.nodeType !== 1) continue;
        var cs = getComputedStyle(n);
        if (cs.touchAction === "none" || n.tagName === "INPUT" || n.tagName === "TEXTAREA") return true;
        if ((cs.overflowX === "auto" || cs.overflowX === "scroll") && n.scrollWidth > n.clientWidth + 2) return true;
        if ((cs.overflowY === "auto" || cs.overflowY === "scroll") && n.scrollHeight > n.clientHeight + 2 && n.scrollTop > 0) return true;
      }
      return false;
    }
    function draw(p) {
      var k = Math.min(p / TH, 1);
      ptr.style.opacity = String(k);
      ptr.style.transform = "translateY(" + (-60 + k * 72) + "px) rotate(" + (k * 270) + "deg)";
    }
    addEventListener("touchstart", function (e) {
      if (busy || e.touches.length !== 1 || !top() || blocked(e.target)) { y0 = null; return; }
      y0 = e.touches[0].clientY; x0 = e.touches[0].clientX; dy = 0;
    }, { passive: true });
    addEventListener("touchmove", function (e) {
      if (y0 === null) return;
      var t = e.touches[0]; dy = t.clientY - y0;
      if (Math.abs(t.clientX - x0) > Math.abs(dy) || dy <= 0 || !top()) { if (dy <= 0) { y0 = null; draw(0); } return; }
      draw(dy * 0.55);
    }, { passive: true });
    addEventListener("touchend", function () {
      if (y0 === null) return;
      var go = dy * 0.55 >= TH * 0.9; y0 = null;
      if (go) {
        busy = true; ptr.classList.add("spin"); ptr.style.opacity = "1"; ptr.style.transform = "translateY(12px)";
        setTimeout(function () { location.reload(); }, 250);
      } else draw(0);
    }, { passive: true });
    addEventListener("pageshow", function (e) { if (e.persisted) location.reload(); });
  }
  if (document.body) init(); else addEventListener("DOMContentLoaded", init);
})();
