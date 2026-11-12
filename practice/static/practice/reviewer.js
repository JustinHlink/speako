'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const queue = $('review-queue');
  let loading=false, saving=false;
  const csrf=()=>document.cookie.split('; ').find(v=>v.startsWith('csrftoken='))?.split('=')[1] || '';
  function notice(text='') {$('review-error').textContent=text;$('review-error').hidden=!text;}
  async function api(url, data) {
    const started=Date.now();let succeeded=false;
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),12000);
    try {
      const response=await fetch(url,{method:data?'POST':'GET',headers:data?{'Content-Type':'application/json','X-CSRFToken':csrf()}:{},body:data?JSON.stringify(data):undefined,signal:controller.signal});
      const result=await response.json();
      if(!response.ok){const error=new Error(response.status===401?'Your session expired. Sign in again from the home page.':response.status===403?'A reviewer account is required.':result.error?.message || 'Request failed.');error.code=result.error?.code;error.status=response.status;throw error;}
      succeeded=true;return result;
    } catch(error) {if(error.name==='AbortError')throw new Error('The request timed out. Refresh the queue to check its current state.');throw error;}
    finally {clearTimeout(timer);const elapsed=Date.now()-started;const tag=$('review-timing');tag.textContent=(data?'Save decision':'Load queue')+' · '+(elapsed/1000).toFixed(2)+' s / target ≤ 1 s';tag.className='timing '+(succeeded?(elapsed>1000?'slow':'fast'):'failed');tag.hidden=false;}
  }
  function text(host,label,value){const p=document.createElement('p');const title=document.createElement('strong');title.textContent=label+': ';p.append(title,document.createTextNode(value));host.append(p);}
  function lock(value){saving=value;$('review-refresh').disabled=value;for(const button of queue.querySelectorAll('button'))button.disabled=value;}
  function card(flag){
    const article=document.createElement('article');article.className='lesson-card';article.style.marginBottom='20px';
    const heading=document.createElement('h2');heading.textContent=flag.scenario+' · Turn '+flag.turn_number;article.append(heading);
    text(article,'Flagged at',new Date(flag.flagged_at).toLocaleString());
    text(article,'Grammar goal',flag.grammar_goal);text(article,'Target vocabulary',(flag.target_words || []).join(', '));
    text(article,'Opening',flag.opening);
    for(const item of flag.history || []){text(article,'Earlier learner answer',item.learner_text);text(article,'Earlier AI reply',item.ai_reply);}
    text(article,'Flagged learner answer',flag.learner_text);text(article,'Flagged AI reply',flag.ai_reply);
    if(flag.correction){text(article,'Correction',flag.correction.explanation);text(article,'Corrected example',flag.correction.example);}
    else text(article,'Correction','No correction was attached to this turn.');
    const row=document.createElement('div');row.className='row';
    for(const decision of ['Acceptable','Incorrect']){
      const button=document.createElement('button');button.className=decision==='Acceptable'?'secondary':'primary';button.textContent='Mark '+decision.toLowerCase();
      button.onclick=async()=>{
        if(saving || loading)return;
        lock(true);notice();$('review-status').textContent='Saving decision…';
        let refresh=false;
        try{await api('/api/flag/review/',{flag_id:flag.id,status:decision});article.remove();$('review-status').textContent='Decision saved: '+decision+'.'+(!queue.children.length?' No unresolved flags.':'');}
        catch(error){
          if(error.status===409){notice('This item has already been reviewed. The queue has been refreshed.');refresh=true;}
          else {notice(error.message);$('review-status').textContent='Decision was not confirmed. Refresh the queue before retrying if the connection failed.';if(error.status===401 || error.status===403)queue.replaceChildren();}
        } finally {lock(false);}
        if(refresh)await load(false);
      };
      row.append(button);
    }
    article.append(row);return article;
  }
  async function load(clearNotice=true){
    if(loading || saving)return;
    loading=true;$('review-refresh').disabled=true;if(clearNotice)notice();$('review-status').textContent='Loading queue…';
    // Remove stale decisions while a refreshed queue is being fetched.
    queue.replaceChildren();
    try{const result=await api('/api/flag/list/');if(!Array.isArray(result.flags))throw new Error('Invalid review queue.');for(const flag of result.flags)queue.append(card(flag));$('review-status').textContent=result.flags.length?result.flags.length+' unresolved response(s).':'No unresolved flags.';}
    catch(error){notice(error.message);$('review-status').textContent='Queue unavailable. You can retry with Refresh queue.';}
    finally{loading=false;$('review-refresh').disabled=false;}
  }
  $('review-refresh').onclick=()=>load();
  $('review-sign-out').onclick=async()=>{
    if(saving)return;
    try{const response=await fetch('/api/auth/logout/',{method:'POST',headers:{'X-CSRFToken':csrf()}});if(!response.ok)throw new Error('Sign out failed.');queue.replaceChildren();location.href='/';}catch(error){notice(error.message);}
  };
  void load();
})();
