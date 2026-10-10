let library=[],videos=[],activeCollection='',activeChannel='',selected=new Set(),jobs=[];const $=id=>document.getElementById(id);const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(url,body){const res=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await res.json();if(!data.ok)throw Error(data.error||'خطای نامشخص');return data}let toastTimer;function toast(message,error=false){const el=$('toast');el.textContent=message;el.className=`toast show ${error?'error':''}`;clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.className='toast',4200)}
async function loadLibrary(){try{library=(await api('/api/library')).channels;renderLibrary()}catch(e){toast(e.message,true)}}
function renderLibrary(){const q=$('librarySearch').value.trim().toLowerCase();$('library').innerHTML=library.filter(c=>!q||c.title.toLowerCase().includes(q)||c.playlists.some(p=>p.title.toLowerCase().includes(q))).map(c=>`<div class="channel-node"><div class="channel-title"><span class="channel-avatar">${esc(c.title[0]||'Y')}</span><span>${esc(c.title)}</span></div>${c.playlists.filter(p=>!q||p.title.toLowerCase().includes(q)).map(p=>`<div class="playlist-node ${p.playlist_id===activeCollection?'active':''}" onclick="openCollection('${esc(p.playlist_id)}','${esc(c.channel_key)}')"><span class="playlist-icon">${p.kind==='uploads'?'◉':'≡'}</span><span class="playlist-name" title="${esc(p.title)}">${esc(p.title)}</span>${p.pinned?'★':''}<span class="count">${p.cached_count||p.reported_count||'?'}</span></div>`).join('')}</div>`).join('')||'<div class="queue-empty">هنوز کانالی ندارید.</div>'}
async function addChannel(){const url=$('channelUrl').value.trim();if(!url)return toast('لینک کانال را وارد کنید.',true);try{toast('در حال شناسایی و Sync کانال…');await api('/api/library/add-channel',{url});$('channelUrl').value='';await loadLibrary();toast('کانال با موفقیت به Library افزوده شد.')}catch(e){toast(e.message,true)}}
async function refreshCookies(){try{toast('در حال دریافت کوکی از Chrome…');const d=await api('/api/refresh-cookies',{});setCookie(d);toast('کوکی معتبر ذخیره شد.')}catch(e){toast(e.message,true)}}async function loadCookie(){try{setCookie(await api('/api/cookie-status'))}catch{}}function setCookie(d){const e=$('cookiePill');e.textContent=d.ready?'● فایل کوکی ذخیره است':'● کوکی ذخیره نشده است';e.className=`status-pill ${d.ready?'good':'muted'}`}
async function openCollection(id,channel){activeCollection=id;activeChannel=channel;selected.clear();renderLibrary();$('syncButton').disabled=false;$('currentMeta').textContent='در حال دریافت فهرست ویدیوها…';try{const d=await api('/api/library/collection-videos',{playlist_id:id});videos=d.videos||[];$('currentTitle').textContent=d.playlist.title;$('collectionEyebrow').textContent=d.playlist.kind==='uploads'?'ALL CHANNEL VIDEOS':'PLAYLIST';$('currentMeta').textContent=`${fa(videos.length)} ویدیو · آخرین Sync: ${d.playlist.last_synced?.replace('T',' ')||'—'}`;renderVideos()}catch(e){toast(e.message,true)}}async function syncCurrent(){if(!activeCollection)return;try{toast('در حال Sync Playlist…');await openCollection(activeCollection,activeChannel);const d=await api('/api/library/collection-videos',{playlist_id:activeCollection,refresh:true});videos=d.videos||[];renderVideos();await loadLibrary();toast('Playlist به‌روز شد.')}catch(e){toast(e.message,true)}}
function filtered(){const q=$('videoSearch').value.trim().toLowerCase();return videos.filter(v=>!q||(v.title||'').toLowerCase().includes(q)||(v.channel||'').toLowerCase().includes(q)||(v.video_id||'').toLowerCase().includes(q))}function renderVideos(){const list=filtered();$('emptyState').style.display=videos.length?'none':'block';$('videoList').innerHTML=list.map(v=>`<article class="video-card ${selected.has(v.video_id)?'selected':''}" onclick="toggleVideo('${esc(v.video_id)}')"><input type="checkbox" ${selected.has(v.video_id)?'checked':''} onclick="event.stopPropagation();toggleVideo('${esc(v.video_id)}')"><img class="thumbnail" src="${esc(v.thumbnail||'')}" loading="lazy" onerror="this.style.opacity='.25'"><div><div class="video-title" title="${esc(v.title)}">${esc(v.title)}</div><div class="video-meta"><span>${esc(v.channel||'YouTube')}</span><span>·</span><span>${esc(v.duration_text||'—')}</span><span>·</span><span>${esc(v.video_id)}</span></div><div class="chips">${v.local_exists?'<span class="chip good">فایل سالم روی مک</span>':''}${v.downloaded_before&&!v.local_exists?'<span class="chip">قبلاً دانلود شده</span>':''}${v.telegram_sent?'<span class="chip blue">ارسال Telegram</span>':''}</div></div><span class="video-index">#${String(v.position).padStart(3,'0')}</span></article>`).join('');updateSelection()}
function toggleVideo(id){selected.has(id)?selected.delete(id):selected.add(id);renderVideos()}function selectVisible(on){filtered().forEach(v=>on?selected.add(v.video_id):selected.delete(v.video_id));renderVideos()}function selectNotDownloaded(){selected=new Set(filtered().filter(v=>!v.local_exists).map(v=>v.video_id));renderVideos()}function selectRange(){let a=+$('rangeFrom').value,b=+$('rangeTo').value;if(!a||!b)return toast('ابتدا ابتدا و انتهای بازه را وارد کنید.',true);if(a>b)[a,b]=[b,a];videos.filter(v=>v.position>=a&&v.position<=b).forEach(v=>selected.add(v.video_id));renderVideos()}function updateSelection(){$('selectionSummary').textContent=`${fa(selected.size)} ویدیو انتخاب شده`;$('queueCount').textContent=fa(selected.size)}
function toggleTelegram(){$('telegramOptions').classList.toggle('visible',$('sendTelegram').checked)}async function detectChat(){try{const d=await api('/api/detect-chat',{});$('chatId').value=d.chat_id;toast(`Chat ID «${d.name}» پیدا شد.`)}catch(e){toast(e.message,true)}}async function enqueueSelected(){const items=videos.filter(v=>selected.has(v.video_id)).map(v=>({...v,playlist_id:activeCollection,video_url:v.url}));if(!items.length)return toast('حداقل یک ویدیو را انتخاب کنید.',true);if($('sendTelegram').checked&&!$('chatId').value.trim())return toast('برای Telegram، Chat ID لازم است.',true);try{const d=await api('/api/enqueue',{items,quality:$('quality').value,send_telegram:$('sendTelegram').checked,chat_id:$('chatId').value.trim(),keep_file:$('keepFile').checked});toast(`${fa(d.added)} ویدیو به صف افزوده شد.`);selected.clear();renderVideos();poll()}catch(e){toast(e.message,true)}}
const fa=n=>Number(n||0).toLocaleString('fa-IR');function status(s){return({queued:'در صف',downloading:'دانلود',processing:'پردازش',validating:'اعتبارسنجی',uploading:'ارسال',done:'تمام',failed:'خطا',canceled:'لغو'}[s]||s)}async function poll(){try{jobs=(await api('/api/status')).jobs||[];$('queue').innerHTML=jobs.slice().reverse().map(j=>`<div class="job"><div class="job-top"><span class="job-title">#${String(j.position).padStart(3,'0')} · ${esc(j.title)}</span><span class="job-status ${esc(j.status)}">${status(j.status)}</span></div><div class="progress"><i style="width:${Math.min(100,Math.max(0,j.progress||0))}%"></i></div><div class="job-bottom"><span>${j.progress?Number(j.progress).toFixed(0)+'%':esc(j.message||'')}</span><span>${esc(j.speed||'')}${j.eta?' · ETA '+esc(j.eta):''}</span></div>${j.error?`<div class="job-bottom" style="color:#ffa8ba">${esc(j.error)}</div>`:''}</div>`).join('')||'<div class="queue-empty">صف دانلود خالی است.</div>'}catch{}}async function cancelCurrent(){try{toast((await api('/api/cancel-current',{})).message);poll()}catch(e){toast(e.message,true)}}async function clearFinished(){try{await api('/api/clear-finished',{});poll()}catch(e){toast(e.message,true)}}async function openDownloads(){try{await api('/api/open-downloads',{})}catch(e){toast(e.message,true)}}loadLibrary();loadCookie();poll();setInterval(poll,1000);

async function jobAction(id, action, direction) {
  try { await api(`/api/jobs/${id}/${action}`, direction === undefined ? {} : {direction}); await poll(); }
  catch (e) { toast(e.message, true); }
}
poll = async function() {
  try {
    jobs = (await api('/api/status')).jobs || [];
    $('queue').innerHTML = jobs.slice().reverse().map(j => {
      const canMove = j.status === 'queued';
      const terminal = ['done','failed','canceled'].includes(j.status);
      return `<div class="job">
        <div class="job-top"><span class="job-title">#${String(j.position).padStart(3,'0')} · ${esc(j.title)}</span><span class="job-status ${esc(j.status)}">${status(j.status)}</span></div>
        <div class="progress"><i style="width:${Math.min(100,Math.max(0,j.progress||0))}%"></i></div>
        <div class="job-bottom"><span>${j.progress?Number(j.progress).toFixed(0)+'%':esc(j.message||'')}</span><span>${esc(j.speed||'')}${j.eta?' · ETA '+esc(j.eta):''}</span></div>
        ${j.error?`<div class="job-error">${esc(j.error)}</div>`:''}
        <div class="job-controls">
          ${canMove?`<button onclick="jobAction('${j.job_id}','move',-1)" title="بالا">↑</button><button onclick="jobAction('${j.job_id}','move',1)" title="پایین">↓</button>`:''}
          ${['queued','downloading','processing','validating','uploading'].includes(j.status)?`<button class="warn" onclick="jobAction('${j.job_id}','cancel')">لغو</button>`:''}
          ${terminal?`<button onclick="jobAction('${j.job_id}','retry')">تلاش دوباره</button><button class="danger" onclick="jobAction('${j.job_id}','delete')">حذف</button>`:''}
        </div>
      </div>`;
    }).join('') || '<div class="queue-empty">صف دانلود خالی است.</div>';
  } catch {}
}

let expandedChannels = new Set();
const previousStatusText = status;
status = s => s === 'paused' ? 'توقف موقت' : previousStatusText(s);
function toggleChannel(key) { expandedChannels.has(key) ? expandedChannels.delete(key) : expandedChannels.add(key); renderLibrary(); }
renderLibrary = function() {
  const q = $('librarySearch').value.trim().toLowerCase();
  $('library').innerHTML = library.filter(c => !q || c.title.toLowerCase().includes(q) || c.playlists.some(p => p.title.toLowerCase().includes(q))).map(c => {
    const open = q || expandedChannels.has(c.channel_key);
    const entries = c.playlists.filter(p => !q || p.title.toLowerCase().includes(q));
    return `<div class="channel-node ${open?'expanded':''}">
      <button class="channel-title channel-toggle" onclick="toggleChannel('${esc(c.channel_key)}')"><span class="channel-caret">›</span><span class="channel-avatar">${esc(c.title[0]||'Y')}</span><span class="channel-label">${esc(c.title)}</span><span class="count">${fa(entries.length)}</span></button>
      <div class="playlist-children">${entries.map(p => `<div class="playlist-node ${p.playlist_id===activeCollection?'active':''}" onclick="openCollection('${esc(p.playlist_id)}','${esc(c.channel_key)}')"><span class="playlist-icon">${p.kind==='uploads'?'◉':'≡'}</span><span class="playlist-name" title="${esc(p.title)}">${esc(p.title)}</span>${p.pinned?'★':''}<span class="count">${p.cached_count||p.reported_count||'?'}</span></div>`).join('')}</div>
    </div>`;
  }).join('') || '<div class="queue-empty">هنوز کانالی ندارید.</div>';
}
const openCollectionOriginal = openCollection;
openCollection = async function(id, channel) { expandedChannels.add(channel); return openCollectionOriginal(id, channel); }
poll = async function() {
  try {
    jobs = (await api('/api/status')).jobs || [];
    $('queue').innerHTML = jobs.slice().reverse().map(j => {
      const active = ['downloading','processing','validating','uploading'].includes(j.status);
      const canMove = j.status === 'queued'; const terminal = ['done','failed','canceled'].includes(j.status);
      return `<div class="job ${j.status==='paused'?'paused':''}">
        <div class="job-top"><span class="job-title">#${String(j.position).padStart(3,'0')} · ${esc(j.title)}</span><span class="job-status ${esc(j.status)}">${status(j.status)}</span></div>
        <div class="progress"><i style="width:${Math.min(100,Math.max(0,j.progress||0))}%"></i></div>
        <div class="job-bottom"><span>${j.progress?Number(j.progress).toFixed(0)+'%':esc(j.message||'')}</span><span>${esc(j.speed||'')}${j.eta?' · ETA '+esc(j.eta):''}</span></div>
        ${j.error?`<div class="job-error">${esc(j.error)}</div>`:''}
        <div class="job-controls">
          ${canMove?`<button onclick="jobAction('${j.job_id}','move',-1)" title="بالا">↑</button><button onclick="jobAction('${j.job_id}','move',1)" title="پایین">↓</button>`:''}
          ${active?`<button onclick="jobAction('${j.job_id}','pause')">Ⅱ توقف موقت</button><button class="warn" onclick="jobAction('${j.job_id}','cancel')">لغو</button>`:''}
          ${j.status==='paused'?`<button class="resume" onclick="jobAction('${j.job_id}','resume')">▶ ادامه</button><button class="warn" onclick="jobAction('${j.job_id}','cancel')">لغو</button>`:''}
          ${terminal?`<button onclick="jobAction('${j.job_id}','retry')">تلاش دوباره</button><button class="danger" onclick="jobAction('${j.job_id}','delete')">حذف</button>`:''}
        </div>
      </div>`;
    }).join('') || '<div class="queue-empty">صف دانلود خالی است.</div>';
  } catch {}
}
