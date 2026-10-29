(function(){var m=location.pathname.match(/^\/(x|design)\/(\d{4}-\d{2}-\d{2})\.html$/);if(!m)return;
var b=JSON.stringify({date:m[2],kind:m[1]});try{if(navigator.sendBeacon&&navigator.sendBeacon("/api/read",new Blob([b],{type:"application/json"})))return}catch(e){}
fetch("/api/read",{method:"POST",headers:{"Content-Type":"application/json"},body:b,keepalive:true}).catch(function(){})})();
