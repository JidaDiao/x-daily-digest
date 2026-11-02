/* 叼报 PWA 导航：仅在主屏幕独立窗口（无地址栏）里启用。悬浮返回键 + 下拉刷新。无外部依赖。 */
(function () {
  var standalone = window.navigator.standalone === true || (window.matchMedia && matchMedia("(display-mode: standalone)").matches);
  if (!standalone || window.__pwaNav) return;
  window.__pwaNav = 1;
  var isHome = location.pathname === "/" || location.pathname === "/index.html";

  function css() {
    var s = document.createElement("style");
    s.textContent =
      ".pn-bar{position:-webkit-sticky;position:sticky;top:0;z-index:2147483000;box-sizing:border-box;width:100%;height:calc(env(safe-area-inset-top,0px) + 44px);padding:env(safe-area-inset-top,0px) 8px 0;display:flex;align-items:center;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px)}" +
      ".pn-bar.dark{background:rgba(18,20,28,.82);border-bottom:1px solid rgba(255,255,255,.08)}.pn-bar.light{background:rgba(250,250,248,.86);border-bottom:1px solid rgba(0,0,0,.08)}" +
      ".pn-back{height:34px;padding:0 12px 0 6px;display:flex;align-items:center;gap:2px;border:0;border-radius:999px;background:transparent;font:600 15px/1 -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;-webkit-tap-highlight-color:transparent}" +
      ".pn-bar.dark .pn-back{color:#fff}.pn-bar.light .pn-back{color:#1d1d1f}.pn-back:active{opacity:.5}.pn-back svg{width:18px;height:18px;stroke:currentColor}" +
".pn-ptr{position:fixed;z-index:2147483000;left:50%;top:calc(env(safe-area-inset-top,0px) + 6px);width:36px;height:36px;margin-left:-18px;border-radius:50%;background:#fff;box-shadow:0 4px 16px rgba(0,0,0,.2);display:flex;align-items:center;justify-content:center;opacity:0;transform:translateY(-60px);pointer-events:none}" +
      ".pn-ptr svg{width:18px;height:18px;stroke:#2c76a0;fill:none;stroke-width:2.4;stroke-linecap:round}" +
      ".pn-ptr.spin svg{animation:pn-spin .7s linear infinite}@keyframes pn-spin{to{transform:rotate(360deg)}}";
    document.head.appendChild(s);
  }

  function isDark() {
    function lum(el) {
      var c = getComputedStyle(el).backgroundColor, m = c && c.match(/[\d.]+/g);
      if (!m || m.length < 3 || (m.length > 3 && parseFloat(m[3]) === 0)) return null;
      return (0.299 * m[0] + 0.587 * m[1] + 0.114 * m[2]) / 255;
    }
    var l = lum(document.body); if (l === null) l = lum(document.documentElement);
    return l !== null ? l < 0.5 : !!(window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function back() {
    var same = false;
    try { same = document.referrer && new URL(document.referrer).origin === location.origin; } catch (e) {}
    if (same && history.length > 1) history.back(); else location.href = "/";
  }

  function init() {
    css();
    if (!isHome) {
      var bar = document.createElement("div");
      bar.className = "pn-bar " + (isDark() ? "dark" : "light");
      var b = document.createElement("button");
      b.className = "pn-back"; b.type = "button"; b.setAttribute("aria-label", "返回");
      b.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>返回';
      b.addEventListener("click", back);
      bar.appendChild(b);
      document.body.insertBefore(bar, document.body.firstChild);
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
