/* DiaoDaily 叼报 · news-signal.js — 日报条目轻互动（👍 👎 ⭐ 已读 + 可选短评）→ POST /api/signal
 * 嵌入：<script src="news-signal.js" defer data-date="2026-10-26" data-source="news"></script>
 * 条目标记：<article data-sig-id="x:1849xxxxxxxx" data-sig-url="https://x.com/u/status/..." data-sig-title="标题"
 *                    data-sig-author="u" data-sig-topic="AI" data-sig-tags="topic:ai,format:thread"> … </article>
 * 脚本自动在每个 [data-sig-id] 末尾插入一行按钮（或放进其内的 [data-sig-bar] 容器）。不加载任何图片/外部资源。
 * 同站（daily.jidadiao.fun）走相对路径；github.io 走 https://daily.jidadiao.fun/api/signal（CORS 白名单）。
 * 去重：localStorage 记住每条状态，同一动作不重复上报；👍/👎 互斥（切换时先报相反动作）；⭐再点 = unfav。
 * 👍/👎 后弹出可选一行短评（可不写）；有字再发 action=comment（meta.note≤200，meta.vote=like|dislike）。
 * 已读：条目在视口停留 ≥2s 自动报 read（每条一次），点原文链接报 open。离线/失败排队，下次打开页面重试。 */
(function () {
  "use strict";
  var S = document.currentScript || {}, ds = (S.dataset || {});
  var DATE = ds.date || (location.pathname.match(/(\d{4}-\d{2}-\d{2})/) || [])[1] || "";
  var SRC = ds.source === "design" ? "design" : "news";
  var API = ds.endpoint || (location.host === "daily.jidadiao.fun" ? "/api/signal" : "https://daily.jidadiao.fun/api/signal");
  var KEY = "dd-sig:" + DATE, QK = "dd-sig-queue";
  function ld(k, d) { try { return JSON.parse(localStorage.getItem(k)) || d; } catch (e) { return d; } }
  function sv(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  var state = ld(KEY, {});
  function payload(el, action) {
    var d = el.dataset, tags = (d.sigTags || "").split(/[,，\s]+/).filter(Boolean).slice(0, 20);
    var o = { source_type: SRC, action: action, item_id: d.sigId, title: (d.sigTitle || "").slice(0, 300),
              tags: tags, meta: { date: DATE, page: location.pathname.slice(-80) } };
    if (/^https?:\/\//.test(d.sigUrl || "")) o.item_url = d.sigUrl;
    if (d.sigAuthor) o.author = d.sigAuthor.slice(0, 120);
    if (d.sigTopic) o.topic = d.sigTopic.slice(0, 80);
    return o;
  }
  function post(o) {
    // text/plain = CORS simple request (no preflight); server parses JSON body regardless.
    return fetch(API, { method: "POST", mode: "cors", credentials: "omit", keepalive: true,
      headers: { "Content-Type": "text/plain;charset=UTF-8" }, body: JSON.stringify(o) })
      .then(function (r) {
        if (r.status >= 200 && r.status < 300) return r.status;
        var err = new Error("http " + r.status); err.status = r.status; throw err;
      });
  }
  var MAX_TRY = 5, MAX_TRY_403 = 3, MAX_Q = 50;
  function enqueue(o, err) {
    var st = err && err.status, n = (o._try || 0) + 1, lim = st === 403 ? MAX_TRY_403 : MAX_TRY;
    if (st && st >= 400 && st < 500 && st !== 403 && st !== 408 && st !== 429) {
      try { console.warn("[news-signal] dropped (HTTP " + st + ")", o.item_id); } catch (e) {} return;
    }
    if (n >= lim) { try { console.warn("[news-signal] dropped after " + n + " tries (" + (st || "network") + ")", o.item_id); } catch (e) {} return; }
    o._try = n; var q = ld(QK, []); q.push(o); sv(QK, q.slice(-MAX_Q));
  }
  function send(o) {
    var t = o._try; delete o._try;
    return post(o).catch(function (err) { o._try = t; enqueue(o, err); });
  }
  function flush() { var q = ld(QK, []); if (!q.length) return; sv(QK, []); q.forEach(send); }
  function mark(id, k, v) { var s = state[id] || (state[id] = {}); s[k] = v; sv(KEY, state); }
  var BTN = [["like", "👍", "喜欢"], ["dislike", "👎", "不感兴趣"], ["fav", "⭐", "收藏"]];
  function paint(bar, id) {
    var s = state[id] || {};
    Array.prototype.forEach.call(bar.querySelectorAll("button[data-a]"), function (b) {
      var on = b.dataset.a === "fav" ? !!s.fav : s.vote === b.dataset.a;
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    var r = bar.querySelector(".dd-read"); if (r) r.textContent = s.read ? "已读" : "";
  }
  function closeNote(bar) {
    var n = bar.querySelector(".dd-note"); if (n) n.remove();
  }
  function askNote(el, bar, vote) {
    closeNote(bar);
    var wrap = document.createElement("div");
    wrap.className = "dd-note";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "可选短评");
    var inp = document.createElement("input");
    inp.type = "text"; inp.maxLength = 200; inp.placeholder = "为什么？（可不写）";
    inp.setAttribute("aria-label", "为什么（可不写）");
    inp.autocomplete = "off";
    var ok = document.createElement("button");
    ok.type = "button"; ok.textContent = "发送"; ok.title = "发送短评（空则跳过）";
    ok.setAttribute("aria-label", "发送短评");
    function submit() {
      var note = (inp.value || "").trim().slice(0, 200);
      if (note) {
        var o = payload(el, "comment");
        o.meta = o.meta || {};
        o.meta.note = note;
        o.meta.vote = vote;
        o.note = note;
        send(o);
        mark(el.dataset.sigId, "noted", 1);
      }
      closeNote(bar);
    }
    ok.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); submit(); });
    inp.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") { ev.preventDefault(); submit(); }
      else if (ev.key === "Escape") { ev.preventDefault(); closeNote(bar); }
    });
    wrap.addEventListener("click", function (ev) { ev.stopPropagation(); });
    wrap.appendChild(inp); wrap.appendChild(ok);
    bar.appendChild(wrap);
    /* 不自动聚焦：iOS 会放大页面并弹键盘，用户点输入框才输入 */
  }
  function click(el, bar, a) {
    var id = el.dataset.sigId, s = state[id] || {};
    if (a === "fav") { send(payload(el, s.fav ? "unfav" : "fav")); mark(id, "fav", !s.fav); paint(bar, id); }
    else if (s.vote === a) { /* 已投同票：不重复上报 */ }
    else { send(payload(el, a)); mark(id, "vote", a); paint(bar, id); askNote(el, bar, a); }
  }
  function css() {
    if (document.getElementById("dd-sig-css")) return;
    var st = document.createElement("style"); st.id = "dd-sig-css";
    st.textContent = ".dd-sig{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:8px;font:13px/1.2 system-ui,sans-serif;position:relative;z-index:2}" +
      ".dd-sig button[data-a]{all:unset;cursor:pointer;min-width:44px;min-height:44px;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;" +
      "border:1px solid currentColor;border-radius:999px;opacity:.55;padding:0 10px;font-size:16px;touch-action:manipulation;-webkit-tap-highlight-color:transparent}" +
      ".dd-sig button[data-a][aria-pressed=true]{opacity:1;font-weight:700}.dd-sig button:focus-visible{outline:2px solid currentColor}" +
      ".dd-sig .dd-read{opacity:.5;font-size:12px;margin-left:4px}" +
      ".dd-sig .dd-note{display:flex;flex:1 1 100%;gap:6px;align-items:center;margin-top:2px;max-width:100%}" +
      ".dd-sig .dd-note input{flex:1 1 auto;min-width:0;min-height:44px;box-sizing:border-box;padding:8px 10px;border:1px solid currentColor;border-radius:8px;" +
      "background:transparent;color:inherit;font:16px/1.3 system-ui,sans-serif}" +
      ".dd-sig .dd-note button{all:unset;cursor:pointer;min-width:44px;min-height:44px;padding:0 12px;border:1px solid currentColor;border-radius:8px;opacity:.8;" +
      "display:inline-flex;align-items:center;justify-content:center;touch-action:manipulation;flex:0 0 auto}" +
      "@media (max-width:480px){.dd-sig{gap:8px}}";
    document.head.appendChild(st);
  }
  function init() {
    css(); flush();
    var els = document.querySelectorAll("[data-sig-id]");
    var io = "IntersectionObserver" in window ? new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        var el = e.target;
        if (e.isIntersecting) el._t = setTimeout(function () {
          var id = el.dataset.sigId;
          if (!(state[id] || {}).read) { send(payload(el, "read")); mark(id, "read", 1); paint(el._bar, id); }
          io.unobserve(el);
        }, 2000); else clearTimeout(el._t);
      });
    }, { threshold: 0.6 }) : null;
    Array.prototype.forEach.call(els, function (el) {
      var id = el.dataset.sigId; if (!/^[A-Za-z0-9][A-Za-z0-9._:\/@#+\-]{0,199}$/.test(id)) return;
      var bar = el.querySelector("[data-sig-bar]") || el.appendChild(document.createElement("div"));
      bar.classList.add("dd-sig"); bar.setAttribute("role", "group"); bar.setAttribute("aria-label", "反馈");
      BTN.forEach(function (x) {
        var b = document.createElement("button"); b.type = "button"; b.dataset.a = x[0]; b.textContent = x[1]; b.title = x[2];
        b.setAttribute("aria-label", x[2]);
        b.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); click(el, bar, x[0]); });
        bar.appendChild(b);
      });
      var r = document.createElement("span"); r.className = "dd-read"; bar.appendChild(r);
      el._bar = bar; paint(bar, id);
      Array.prototype.forEach.call(el.querySelectorAll("a[href^='http']"), function (a) {
        a.addEventListener("click", function () { if (!(state[id] || {}).open) { send(payload(el, "open")); mark(id, "open", 1); } });
      });
      if (io) io.observe(el);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
