/* Design feedback auto-sync. Include: <script src="design-feedback.js" data-date="YYYY-MM-DD"></script>
   Markup per design: <div class="design" data-site="Resend" data-url="https://resend.com">
     <span class="df-stars"></span> <button class="df-fav"></button></div>
   Stars/fav buttons are auto-rendered if containers are empty.
   Cross-device: on load, reads issues titled design-feedback-<date> (state=all, label feedback)
   from the public GitHub API (no auth, 60 req/h/IP), takes the JSON line at the end of each issue body
   plus every JSON comment, keeps the newest per site by ts, and merges with localStorage (newer ts wins).
   If GitHub fails or is rate-limited, localStorage alone is used. */
(function(){
  var ENDPOINT="https://design-feedback.jidadia010.workers.dev";
  var REPO="JidaDiao/x-daily-digest", API="https://api.github.com/repos/"+REPO;
  var s=document.currentScript, DATE=(s&&s.dataset.date)||(location.pathname.match(/\d{4}-\d{2}-\d{2}/)||[""])[0];
  var KEY="design-feedback:"+DATE, CACHE="design-feedback-remote:"+DATE, state={};
  try{state=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
  var timers={}, els=[];
  function save(){try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}}
  function tsv(x){var t=x&&x.ts?Date.parse(x.ts):0;return isNaN(t)?0:t}
  function send(site,url){clearTimeout(timers[site]);timers[site]=setTimeout(function(){
    var st=state[site]||{};
    fetch(ENDPOINT,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({date:DATE,site:site,url:url||"",rating:st.rating||null,fav:!!st.fav}),keepalive:true})
    .then(function(r){st.synced=r.ok;save()}).catch(function(){});
  },1500);}
  function touch(st){st.ts=new Date().toISOString();st.synced=false}
  function render(el){
    var site=el.dataset.site,url=el.dataset.url,st=state[site]=state[site]||{};
    var stars=el.querySelector(".df-stars"),fav=el.querySelector(".df-fav");
    if(stars){stars.innerHTML="";for(let i=1;i<=5;i++){var b=document.createElement("button");b.type="button";
      b.textContent=i<=(st.rating||0)?"★":"☆";b.title=i+" 星";b.setAttribute("aria-pressed",i<=(st.rating||0));
      b.style.cssText="border:0;background:none;cursor:pointer;font-size:20px;color:#f5a623";
      b.onclick=function(){st.rating=st.rating===i?null:i;touch(st);save();render(el);send(site,url)};stars.appendChild(b);}}
    if(fav){fav.type="button";fav.textContent=st.fav?"♥ 已收藏":"♡ 收藏";fav.setAttribute("aria-pressed",!!st.fav);
      fav.onclick=function(){st.fav=!st.fav;touch(st);save();render(el);send(site,url)};}
  }
  function parseLines(text,out){
    String(text||"").split(/\r?\n/).forEach(function(l){l=l.trim();if(l.charAt(0)!=="{")return;
      try{var o=JSON.parse(l);if(!o||!o.site||o.site==="test"||(o.date&&o.date!==DATE))return;
        if(!out[o.site]||tsv(o)>=tsv(out[o.site]))out[o.site]=o}catch(e){}});
  }
  function getJSON(u){return fetch(u,{headers:{Accept:"application/vnd.github+json"}}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json()})}
  function merge(remote){
    var changed=false;
    Object.keys(remote).forEach(function(site){var r=remote[site],l=state[site];
      if(!l||tsv(r)>tsv(l)){state[site]={rating:r.rating||null,fav:!!r.fav,ts:r.ts,synced:true};changed=true}});
    if(changed){save();els.forEach(render)}
  }
  function pull(){
    var title="design-feedback-"+DATE;
    getJSON(API+"/issues?labels=feedback&state=all&per_page=100").then(function(list){
      var issues=list.filter(function(i){return i.title===title&&!i.pull_request});
      var out={};issues.forEach(function(i){var b=String(i.body||"").trim().split(/\r?\n/);parseLines(b[b.length-1],out)});
      return Promise.all(issues.filter(function(i){return i.comments>0}).map(function(i){
        return getJSON(API+"/issues/"+i.number+"/comments?per_page=100").then(function(cs){cs.forEach(function(c){parseLines(c.body,out)})})
      })).then(function(){return out});
    }).then(function(out){try{localStorage.setItem(CACHE,JSON.stringify({at:Date.now(),data:out}))}catch(e){}merge(out)})
    .catch(function(){try{var c=JSON.parse(localStorage.getItem(CACHE));if(c&&c.data)merge(c.data)}catch(e){}});
  }
  function init(){els=[].slice.call(document.querySelectorAll("[data-site]"));els.forEach(render);pull()}
  document.readyState==="loading"?document.addEventListener("DOMContentLoaded",init):init();
})();
