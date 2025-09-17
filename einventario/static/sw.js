const CACHE = "einventario-v1";
const OFFLINE = ["/", "/static/manifest.json"];

self.addEventListener("install", (e)=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(OFFLINE)));
});

self.addEventListener("fetch", (e)=>{
  const req=e.request;
  if(req.method!=="GET"){ return; }
  e.respondWith(
    caches.match(req).then(cache=> cache || fetch(req).then(r=>{
      const copy=r.clone(); caches.open(CACHE).then(c=>c.put(req, copy)); return r;
    }).catch(()=>caches.match("/")) )
  );
});
