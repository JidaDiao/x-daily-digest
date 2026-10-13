/* Design feedback auto-sync. Include: <script src="design-feedback.js" data-date="YYYY-MM-DD"></script>
   Markup per design: <div class="design" data-site="Resend" data-url="https://resend.com">
     <span class="df-stars"></span> <button class="df-fav"></button></div>
   Stars/fav buttons are auto-rendered if containers are empty. */
(function(){
  var ENDPOINT="https://design-feedback.jidadia010.workers.dev";
  var s=document.currentScript, DATE=(s&&s.dataset.date)||(location.pathname.match(/\d{4}-\d{2}-\d{2}/)||[""])[0];
  var KEY="design-feedback:"+DATE, state={}; try{state=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
  var timers={};
  function save(){try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}}
  function send(site,url){clearTimeout(timers[site]);timers[site]=setTimeout(function(){
    var st=state[site]||{};
    fetch(ENDPOINT,{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({date:DATE,site:site,url:url||"",rating:st.rating||null,fav:!!st.fav}),keepalive:true})
    .then(function(r){st.synced=r.ok;save()}).catch(function(){});
  },1500);}
  function render(el){
    var site=el.dataset.site,url=el.dataset.url,st=state[site]=state[site]||{};
    var stars=el.querySelector(".df-stars"),fav=el.querySelector(".df-fav");
    if(stars){stars.innerHTML="";for(let i=1;i<=5;i++){var b=document.createElement("button");b.type="button";
      b.textContent=i<=(st.rating||0)?"★":"☆";b.title=i+" 星";b.style.cssText="border:0;background:none;cursor:pointer;font-size:20px;color:#f5a623";
      b.onclick=function(){st.rating=st.rating===i?null:i;save();render(el);send(site,url)};stars.appendChild(b);}}
    if(fav){fav.type="button";fav.textContent=st.fav?"♥ 已收藏":"♡ 收藏";
      fav.onclick=function(){st.fav=!st.fav;save();render(el);send(site,url)};}
  }
  function init(){document.querySelectorAll("[data-site]").forEach(render)}
  document.readyState==="loading"?document.addEventListener("DOMContentLoaded",init):init();
})();
