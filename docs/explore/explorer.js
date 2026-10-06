/* Static GTFS viewer. All schedule calculations happen in the Python exporter. */
"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const canvas = $("map"), ctx = canvas.getContext("2d");
  const background = document.createElement("canvas");
  const intensityModel = window.CitylinerIntensity;
  const names = {tram:"Tram",subway:"Metro",rail:"Rail",bus:"Bus",ferry_water:"Ferry",funicular_cable_gondola:"Cable",other:"Other"};
  const state = {catalog:[],manifest:null,geometry:null,frames:[],values:[],display:null,transition:false,index:0,referenceIndex:0,view:"rhythm",modes:new Set(),palette:"default",playing:false,generation:0,paths:[],matrix:null,dayCache:new Map()};
  let animation = 0, playEpoch = 0, playStart = 0, playFrom = null, hoverFrame = 0, artworkUrl = null;
  const initial = new URLSearchParams(location.hash.slice(1));

  async function read(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Could not load ${new URL(url,location.href).pathname} (${response.status})`);
    if (url.endsWith(".gz")) {
      if (!window.DecompressionStream) throw new Error("This viewer needs a browser supporting gzip DecompressionStream. Please use a recent browser.");
      return JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream("gzip"))).text());
    }
    return response.json();
  }
  function notice(message) { $("action-status").textContent = message; }
  function busy(value) {
    $("loading").hidden = !value;
    for (const id of ["time","play","share","download","palette","date","view"]) $(id).disabled = value;
    $("modes").querySelectorAll("button").forEach(b=>b.disabled=value);
  }
  function error(exc) {
    pause(); busy(false); $("loading").hidden=true; $("error").hidden=false;
    $("error-message").textContent = exc.message || String(exc);
    for (const id of ["time","play","share","download"]) $(id).disabled=true;
  }
  function option(value,label) { const o=document.createElement("option");o.value=value;o.textContent=label;return o; }
  function dateLabel(value) { return new Date(value+"T12:00:00Z").toLocaleDateString("en",{weekday:"short",month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}); }
  function versionUrl(entry, params) {
    const latest = new URL(entry.manifest,location.href);
    const bundle = params.get("bundle");
    return bundle && /^[a-f0-9]{16}$/.test(bundle) ? new URL(`../${bundle}/manifest.json`,latest).href : latest.href;
  }
  async function loadCity(params = new URLSearchParams()) {
    const token = ++state.generation;
    state.frames=[];state.values=[];state.display=null;
    state.detailId=null;$("section-detail").textContent="Hover or tap a line to see its routes and departures.";
    pause();busy(true);$("loading").textContent="Loading the network…";$("error").hidden=true;$("empty").hidden=true;
    const entry = state.catalog.find(c=>c.city===$("city").value);
    if (!entry) throw new Error("No published city selected");
    try {
      let url=versionUrl(entry,params), manifest;
      try { manifest=await read(url); } catch(exc) {
        if (!params.has("bundle")) throw exc;
        url=new URL(entry.manifest,location.href).href;manifest=await read(url);
        notice("That archive version is unavailable. Showing the published version.");
      }
      if(manifest.schemaVersion!==1||manifest.frameEncoding!=="sparse-deltas-v1") throw new Error("Unsupported export bundle version");
      const base=new URL(".",url).href;
      const geometry=await read(new URL(manifest.geometry,base).href);
      if(token!==state.generation)return;
      state.manifest=manifest;state.geometry=geometry;state.base=base;state.dayCache.clear();
      state.palette=Object.hasOwn(manifest.palettes,params.get("palette"))?params.get("palette"):manifest.palette;
      const hasPeaks=geometry.sections.every(s=>Number.isFinite(s.peakDepartures));
      $("view").querySelectorAll("option").forEach(o=>o.disabled=o.value!=="departures"&&!hasPeaks);
      state.view=hasPeaks?(["rhythm","change","departures"].includes(params.get("view"))?params.get("view"):"rhythm"):"departures";
      $("view").value=state.view;
      const requested=params.has("modes")?params.get("modes").split(","):manifest.modes;
      state.modes=new Set(requested.filter(m=>manifest.modes.includes(m)));
      $("city-title").textContent=manifest.title;
      $("archive").textContent=`Schedule week · ${manifest.dates[0].date} — ${manifest.dates.at(-1).date}`;
      $("source").textContent=`${manifest.source}. Feed coverage ${manifest.feedCoverage.join(" — ")}. Times in ${manifest.timezone}.`;
      const credits=[...(manifest.attributions||[])];
      if(manifest.provenance)credits.push({name:`GTFS downloaded ${manifest.provenance.retrievedAt} · ${manifest.provenance.license}`,url:manifest.provenance.url});
      if(manifest.waterSource)credits.push({name:`Water: ${manifest.waterSource.name} · ${manifest.waterSource.license} · data ${manifest.waterSource.dataTimestamp}`,url:manifest.waterSource.url});
      $("attributions").replaceChildren(...credits.map(credit=>{const li=document.createElement("li");let url;try{url=new URL(credit.url);}catch{}if(url&&["https:","http:"].includes(url.protocol)){const a=document.createElement("a");a.href=url.href;a.textContent=credit.name;li.append(a);}else li.textContent=credit.name;return li;}));
      $("warnings").replaceChildren(...manifest.warnings.map(w=>{const li=document.createElement("li");li.textContent=w;return li;}));
      $("date").replaceChildren(...manifest.dates.map(d=>option(d.date,dateLabel(d.date))));
      if(manifest.dates.some(d=>d.date===params.get("date")))$("date").value=params.get("date");
      $("palette").replaceChildren(...Object.keys(manifest.palettes).map(p=>option(p,p.charAt(0).toUpperCase()+p.slice(1))));
      $("palette").value=state.palette;
      $("modes").replaceChildren(...manifest.modes.map(mode=>{
        const button=document.createElement("button");button.type="button";button.textContent=names[mode]||mode;button.dataset.mode=mode;
        button.setAttribute("aria-pressed",String(state.modes.has(mode)));
        button.addEventListener("click",()=>{state.modes.has(mode)?state.modes.delete(mode):state.modes.add(mode);button.setAttribute("aria-pressed",String(state.modes.has(mode)));drawBackground();render();saveUrl();});
        return button;
      }));
      state.paths=geometry.sections.map(section=>{
        const path=new Path2D();const flat=section.paths.flat();
        for(const points of section.paths){points.forEach(([x,y],i)=>i?path.lineTo(x,y):path.moveTo(x,y));}
        return {path,box:[Math.min(...flat.map(p=>p[0])),Math.min(...flat.map(p=>p[1])),Math.max(...flat.map(p=>p[0])),Math.max(...flat.map(p=>p[1]))]};
      });
      resize();await loadDay(params,token);
    }catch(exc){if(token===state.generation)error(exc);}
  }
  async function loadDay(params=new URLSearchParams(), token=state.generation) {
    pause();busy(true);$("error").hidden=true;$("loading").textContent="Loading the selected day…";
    const day=$("date").value;
    try{
      const key=state.manifest.bundle+day;
      if(!state.dayCache.has(key)){
        const entry=state.manifest.dates.find(d=>d.date===day);
        const data=await read(new URL(entry.file,state.base).href);
        if(token!==state.generation||day!==$("date").value)return;
        const current=new Float32Array(state.geometry.sections.length);
        const values=data.frames.map(frame=>{for(const [id,value]of frame.changes)current[id]=value;return current.slice();});
        state.dayCache.set(key,{frames:data.frames,values});
        if(state.dayCache.size>3)state.dayCache.delete(state.dayCache.keys().next().value);
      }
      if(token!==state.generation||day!==$("date").value)return;
      const data=state.dayCache.get(key);state.frames=data.frames;state.values=data.values;
      let index=state.frames.findIndex(f=>f.label.startsWith("08:00"));
      state.referenceIndex=Math.max(0,index);
      const requested=Number(params.get("time"));
      if(params.has("time")){const found=state.frames.findIndex(f=>f.start===requested);if(found>=0)index=found;}
      state.index=Math.max(0,index);$("time").max=state.frames.length-1;$("day-end").textContent=state.frames.at(-1).label.slice(0,5);
      state.display=state.values[state.index].slice();
      busy(false);render();saveUrl();
    }catch(exc){if(token===state.generation)error(exc);}
  }
  function resize(){
    const ratio=Math.min(devicePixelRatio||1,2),rect=canvas.getBoundingClientRect();
    if(rect.width<1||rect.height<1)return;
    canvas.width=Math.round(rect.width*ratio);canvas.height=Math.round(rect.height*ratio);
    background.width=canvas.width;background.height=canvas.height;
    if(!state.manifest)return;
    const [x0,y0,x1,y1]=state.manifest.bounds;
    const scale=Math.min(canvas.width/(x1-x0),canvas.height/(y1-y0))*.94;
    state.matrix={scale,x:canvas.width/2-(x0+x1)/2*scale,y:canvas.height/2-(y0+y1)/2*scale,ratio};
    drawBackground();render();
  }
  function transform(context){const m=state.matrix;context.setTransform(m.scale,0,0,m.scale,m.x,m.y);}
  function drawBackground(){
    if(!state.matrix||!state.geometry)return;
    const b=background.getContext("2d");b.setTransform(1,0,0,1,0,0);b.fillStyle="#080c13";b.fillRect(0,0,background.width,background.height);transform(b);
    b.fillStyle="#111e33";
    for(const polygon of state.geometry.water){const path=new Path2D();for(const ring of polygon){ring.forEach(([x,y],i)=>i?path.lineTo(x,y):path.moveTo(x,y));path.closePath();}b.fill(path,"evenodd");}
    // Opaque, dark context prevents stacked variants from becoming a static glow.
    b.strokeStyle="#17202b";b.globalAlpha=1;b.lineWidth=state.matrix.ratio*.45/state.matrix.scale;
    for(const section of state.geometry.sections)if(state.modes.has(section.mode))b.stroke(state.paths[section.id].path);
    b.globalAlpha=1;
  }
  function render(mix=0){
    if(!state.matrix||!state.frames.length||!state.values[state.index]||!background.width||!background.height)return;
    const started=performance.now();ctx.setTransform(1,0,0,1,0,0);ctx.drawImage(background,0,0);transform(ctx);
    const counts=state.display||state.values[state.index],palette=state.manifest.palettes[state.palette],maximum=state.manifest.intensityMaximum;
    const reference=state.values[state.referenceIndex];let active=0,visible=0;
    // Lighten opaque, intensity-colored strokes instead of adding their alpha.
    // Multiple overlapping shape variants cannot falsely brighten a corridor.
    ctx.globalCompositeOperation="lighten";
    for(const section of state.geometry.sections){const count=counts[section.id];if(!state.modes.has(section.mode))continue;
      if(count>0)active++;
      const {intensity,delta}=intensityModel.visual(count,section.peakDepartures,maximum,state.view,reference[section.id]);
      if(intensity<=0)continue;visible++;
      const color=state.view==="change"?(delta>0?"#b4eccd":"#e99090"):palette[section.mode];
      ctx.globalAlpha=1;ctx.strokeStyle=intensityModel.color(color,intensity);ctx.lineWidth=(.45+2.7*intensity)*state.matrix.ratio/state.matrix.scale;
      ctx.stroke(state.paths[section.id].path);
    }
    ctx.globalCompositeOperation="source-over";ctx.globalAlpha=1;ctx.setTransform(1,0,0,1,0,0);
    const frame=state.frames[state.index];$("time").value=state.index;
    $("window").textContent=`${frame.label} — ${frame.endLabel}${frame.endDate!==$("date").value?" (+1 day)":""}${state.playing?" · blending":""}`;
    $("empty").textContent=state.view==="change"&&visible===0&&active>0?"No change from 08:00 for the selected modes.":"No scheduled service in this window for the selected modes.";
    $("empty").hidden=state.view==="change"?visible!==0:active!==0;
    $("view-explanation").textContent=(state.view==="rhythm"?"Daily rhythm · frequent service near its weekly peak shines brighter; rare service stays subdued.":state.view==="change"?"Change from 08:00 · mint = more service; coral = less; pale overlaps = mixed changes. Unchanged sections remain faint.":"Departures · brighter = more departures. One logarithmic scale stays fixed across the week.")+" Playback blends 15-minute samples; paused counts are exact after the fade.";
    $("palette").disabled=state.view==="change";
    canvas.setAttribute("aria-label",`${state.manifest.title}, ${$("date").value}, ${frame.label} to ${frame.endLabel}. ${active} sections have service. View: ${$("view").selectedOptions[0].textContent}.`);
    canvas.dataset.renderMs=(performance.now()-started).toFixed(2);
    canvas.dataset.interpolated=String(state.playing||state.transition);
    canvas.dataset.sampleMix=Number(mix).toFixed(4);
    showDetail();
  }
  function params(){
    return new URLSearchParams({city:state.manifest.city,bundle:state.manifest.bundle,date:$("date").value,time:state.frames[state.index].start,modes:[...state.modes].sort().join(","),palette:state.palette,view:state.view});
  }
  function saveUrl(){if(state.manifest&&state.frames.length)history.replaceState(null,"","#"+params());}
  function pause(){state.playing=false;state.transition=false;cancelAnimationFrame(animation);$("play").textContent="Play day";$("play").setAttribute("aria-label","Play the selected day");$("window").setAttribute("aria-live","polite");$("section-detail").setAttribute("aria-live","polite");}
  function settle(index){
    if(!state.values[index]||!state.display)return;
    const from=state.display.slice(),to=state.values[index],started=performance.now();
    state.index=index;state.transition=true;$("window").setAttribute("aria-live","off");$("section-detail").setAttribute("aria-live","off");
    render();saveUrl();
    function fade(now){
      const t=Math.min(1,(now-started)/220),eased=t*t*(3-2*t);
      intensityModel.blend(from,to,eased,state.display);state.transition=t<1;render(state.transition?eased:0);
      if(t<1)animation=requestAnimationFrame(fade);
      else{$("window").setAttribute("aria-live","polite");$("section-detail").setAttribute("aria-live","polite");}
    }
    animation=requestAnimationFrame(fade);
  }
  function tick(now){
    if(!state.playing)return;
    const duration=30000/state.frames.length;
    const position=(playStart+(now-playEpoch)/duration)%state.frames.length,index=Math.floor(position),changed=index!==state.index;
    state.index=index;
    intensityModel.blend(state.values[index],state.values[(index+1)%state.frames.length],position-index,state.display);
    const entry=Math.min(1,(now-playEpoch)/220);
    if(entry<1)intensityModel.blend(playFrom,state.display,entry*entry*(3-2*entry),state.display);
    render(position-index);if(changed)saveUrl();
    animation=requestAnimationFrame(tick);
  }
  function detail(event){
    if(!state.frames.length||!state.matrix)return;
    const rect=canvas.getBoundingClientRect(),m=state.matrix;
    const x=((event.clientX-rect.left)*m.ratio-m.x)/m.scale,y=((event.clientY-rect.top)*m.ratio-m.y)/m.scale,tolerance=7*m.ratio/m.scale;
    let best=null,bestDistance=tolerance,bestScore=-1,counts=state.display||state.values[state.index];
    for(const section of state.geometry.sections){if(!state.modes.has(section.mode))continue;const box=state.paths[section.id].box;if(x<box[0]-tolerance||x>box[2]+tolerance||y<box[1]-tolerance||y>box[3]+tolerance)continue;
      const score=intensityModel.visual(counts[section.id],section.peakDepartures,state.manifest.intensityMaximum,state.view,state.values[state.referenceIndex][section.id]).intensity;
      for(const path of section.paths)for(let i=1;i<path.length;i++){
        const a=path[i-1],b=path[i],dx=b[0]-a[0],dy=b[1]-a[1],den=dx*dx+dy*dy;
        const t=den?Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/den)):0;
        const distance=Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy);
        if(distance<bestDistance-.01||(Math.abs(distance-bestDistance)<.01&&score>bestScore)){best=section;bestDistance=distance;bestScore=score;}
      }
    }
    state.detailId=best?best.id:null;showDetail();
  }
  function showDetail(){
    const best=state.detailId==null?null:state.geometry.sections[state.detailId],counts=state.display||state.values[state.index];
    if(!best||!counts||!state.modes.has(best.mode)){$("section-detail").textContent="Hover or tap a line to see its routes and departures.";return;}
    const count=counts[best.id],delta=count-state.values[state.referenceIndex][best.id];
    const comparison=state.view==="rhythm"?` · ${best.peakDepartures>0?Math.round(count/best.peakDepartures*100):0}% of its weekly peak`:state.view==="change"?` · ${delta>=0?"+":""}${Number(delta.toFixed(2))} vs 08:00`:"";
    $("section-detail").textContent=`${best.routes.map(r=>state.geometry.routes[r].name).join(" · ")} · ${names[best.mode]} · ${state.playing||state.transition?"≈ ":""}${Number(count.toFixed(2))} ${best.estimated?"scheduled / expected":"scheduled"} departures in this hour${comparison}${state.playing||state.transition?" · blended display":""}${best.interpolated?" · includes interpolated stop timing":""}`;
  }
  $("city").addEventListener("change",()=>loadCity());
  $("date").addEventListener("change",()=>loadDay());
  $("time").addEventListener("input",()=>{pause();settle(Number($("time").value));});
  $("palette").addEventListener("change",()=>{state.palette=$("palette").value;render();saveUrl();});
  $("view").addEventListener("change",()=>{state.view=$("view").value;render();saveUrl();});
  $("play").addEventListener("click",()=>{if(state.playing){pause();settle(state.index);return;}pause();playFrom=state.display.slice();state.playing=true;playStart=state.index;playEpoch=performance.now();$("window").setAttribute("aria-live","off");$("section-detail").setAttribute("aria-live","off");$("play").textContent="Pause";$("play").setAttribute("aria-label","Pause playback");animation=requestAnimationFrame(tick);});
  canvas.addEventListener("pointermove",event=>{cancelAnimationFrame(hoverFrame);hoverFrame=requestAnimationFrame(()=>detail(event));});
  canvas.addEventListener("click",detail);
  $("share").addEventListener("click",async()=>{saveUrl();try{await navigator.clipboard.writeText(location.href);notice("View link copied.");}catch{notice("Copy the view link from your browser address bar.");}});
  $("download").addEventListener("click",()=>{
    pause();state.display.set(state.values[state.index]);render();saveUrl();
    const filename=`cityliner-${state.manifest.city}-${$("date").value}.png`;
    const out=document.createElement("canvas");out.width=canvas.width;const c=out.getContext("2d");
    const paragraphs=[`Cityliner by Roman Prokofyev · ${$("date").value} · ${$("window").textContent}`,$("view-explanation").textContent,"Scheduled service; frequency-based services show expected departures.",state.manifest.source];
    for(const credit of state.manifest.attributions||[])paragraphs.push(`${credit.name}${credit.url?" · "+credit.url:""}`);
    if(state.manifest.provenance)paragraphs.push(`GTFS downloaded ${state.manifest.provenance.retrievedAt} · ${state.manifest.provenance.license} · ${state.manifest.provenance.url}`);
    if(state.manifest.waterSource)paragraphs.push(`Water: ${state.manifest.waterSource.name} · ${state.manifest.waterSource.license} · data ${state.manifest.waterSource.dataTimestamp} · ${state.manifest.waterSource.url}`);
    const lines=[];c.font="14px sans-serif";
    for(const text of paragraphs){let line="";for(const word of text.split(" ")){if(c.measureText(line+word).width>out.width-48){lines.push(line);line="";}line+=word+" ";}lines.push(line);}
    out.height=canvas.height+50+lines.length*20;c.fillStyle="#080c13";c.fillRect(0,0,out.width,out.height);c.drawImage(canvas,0,0);
    c.fillStyle="#f0eee8";c.font="32px Georgia";c.fillText(state.manifest.title,24,44);
    c.fillStyle="#a5afbb";c.font="14px sans-serif";
    lines.forEach((line,i)=>c.fillText(line,24,canvas.height+30+i*20));
    out.toBlob(blob=>{if(!blob){notice("Could not create the artwork. Please try again.");return;}if(artworkUrl)URL.revokeObjectURL(artworkUrl);artworkUrl=URL.createObjectURL(blob);const a=$("artwork-link");a.href=artworkUrl;a.download=filename;a.hidden=false;a.click();notice("Artwork ready with source and date information. Use Download PNG if your download did not start.");});
  });
  $("retry").addEventListener("click",()=>state.catalog.length?loadCity(new URLSearchParams(location.hash.slice(1))):start());
  window.addEventListener("hashchange",()=>{const p=new URLSearchParams(location.hash.slice(1));if(state.catalog.some(c=>c.city===p.get("city")))$("city").value=p.get("city");loadCity(p);});
  new ResizeObserver(resize).observe(canvas);
  document.addEventListener("visibilitychange",()=>{if(document.hidden){pause();if(state.display&&state.values[state.index]){state.display.set(state.values[state.index]);render();}}});
  async function start(){try{busy(true);const catalog=await read("catalog.json");state.catalog=catalog.cities;if(!state.catalog.length)throw new Error("No city bundles have been published yet.");$("city").replaceChildren(...state.catalog.map(c=>option(c.city,c.title)));if(state.catalog.some(c=>c.city===initial.get("city")))$("city").value=initial.get("city");$("city").disabled=false;await loadCity(initial);}catch(exc){error(exc);}}
  start();
})();
