'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const queue = $('review-queue');
  const CARDS_PER_ROW = 3;
  if(queue?.style){
    if(queue.style.setProperty)queue.style.setProperty('--review-columns', CARDS_PER_ROW);
    else queue.style['--review-columns'] = CARDS_PER_ROW;
  }

  let loading=false, saving=false;
  let currentFlags = [];
  let selectedFlagId = null;

  function syncSelectedFromUrl(){
    try{
      const search = globalThis.location?.search || '';
      if(!search)return;
      const params = new URLSearchParams(search);
      const id = params.get('flag_id');
      selectedFlagId = id ? Number(id) : null;
    }catch(_){selectedFlagId = null;}
  }
  function updateUrlFlag(id){
    try{
      if(globalThis.history?.pushState){
        const url = id ? `/review/?flag_id=${id}` : '/review/';
        globalThis.history.pushState({flag_id: id}, '', url);
      }
    }catch(_){}
  }

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
  function lock(value){saving=value;$('review-refresh').disabled=value;for(const button of queue.querySelectorAll('button'))button.disabled=value;}

  function buildTurnsList(flag){
    if(Array.isArray(flag.turns) && flag.turns.length)return flag.turns;
    const list=[];
    let num=1;
    for(const item of flag.history || []){
      list.push({
        turn_number: item.turn_number || num++,
        learner_text: item.learner_text,
        ai_reply: item.ai_reply,
        is_flagged: false,
        correction: null
      });
    }
    list.push({
      id: flag.turn_id,
      turn_number: flag.turn_number || num,
      learner_text: flag.learner_text,
      ai_reply: flag.ai_reply,
      is_flagged: true,
      correction: flag.correction || null
    });
    return list;
  }

  function selectFlag(flag){
    if(loading || saving)return;
    selectedFlagId = flag.id;
    updateUrlFlag(flag.id);
    notice();
    renderView();
  }

  function card(flag){
    const article=document.createElement('article');
    article.className='lesson-card review-card';
    article.tabIndex=0;
    article.setAttribute?.('role','button');

    // Header: Scenario, Turn & Flagged Time
    const header=document.createElement('div');
    header.className='review-card-header';
    const heading=document.createElement('h2');
    heading.textContent=flag.scenario+' · Turn '+flag.turn_number;
    const timeEl=document.createElement('div');
    timeEl.className='review-card-time';
    timeEl.textContent='Flagged at: '+new Date(flag.flagged_at).toLocaleString();
    header.append(heading,timeEl);
    article.append(header);

    // Body: Learner text bubble & AI reply bubble with fade-out
    const body=document.createElement('div');
    body.className='review-card-body';

    // Learner text
    const learnerBubble=document.createElement('div');
    learnerBubble.className='review-bubble learner';
    const learnerLabel=document.createElement('span');
    learnerLabel.className='review-bubble-label';
    learnerLabel.textContent='Learner text';
    const lRaw=flag.learner_text || '';
    const learnerText=document.createElement('div');
    learnerText.className='review-text-content'+(lRaw.length>42?' fade-text':'');
    learnerText.append(document.createTextNode(lRaw));
    learnerBubble.append(learnerLabel,learnerText);

    // AI reply
    const aiBubble=document.createElement('div');
    aiBubble.className='review-bubble ai';
    const aiLabel=document.createElement('span');
    aiLabel.className='review-bubble-label';
    aiLabel.textContent='AI reply';
    const aRaw=flag.ai_reply || '';
    const aiText=document.createElement('div');
    aiText.className='review-text-content'+(aRaw.length>42?' fade-text':'');
    aiText.append(document.createTextNode(aRaw));
    aiBubble.append(aiLabel,aiText);

    body.append(learnerBubble,aiBubble);
    article.append(body);

    const hint=document.createElement('div');
    hint.className='review-card-hint';
    hint.textContent='Click to inspect attempt & review →';
    article.append(hint);

    article.onclick=()=>selectFlag(flag);
    article.onkeydown=event=>{
      if(event.key==='Enter' || event.key===' '){
        event.preventDefault?.();
        selectFlag(flag);
      }
    };
    return article;
  }

  function detailView(flag){
    const container=document.createElement('article');
    container.className='attempt-detail-view';

    // Top bar with title & Back button
    const topBar=document.createElement('div');
    topBar.className='attempt-detail-top';
    const heading=document.createElement('h2');
    heading.style.margin='0';
    heading.textContent=flag.scenario+' · Attempt Conversation (Flagged Turn '+flag.turn_number+')';

    const backBtn=document.createElement('button');
    backBtn.className='secondary';
    backBtn.textContent='← Back to queue';
    backBtn.onclick=()=>{
      if(saving || loading)return;
      selectedFlagId=null;
      updateUrlFlag(null);
      notice();
      renderView();
    };
    topBar.append(heading,backBtn);
    container.append(topBar);

    // Attempt & Lesson Context Metadata
    const metaGrid=document.createElement('div');
    metaGrid.className='attempt-meta-grid';
    function addMeta(label,val){
      if(!val)return;
      const item=document.createElement('span');
      const strong=document.createElement('strong');
      strong.textContent=label+': ';
      item.append(strong,document.createTextNode(val));
      metaGrid.append(item);
    }
    if(flag.attempt_id)addMeta('Attempt ID',flag.attempt_id);
    addMeta('Flagged at',new Date(flag.flagged_at).toLocaleString());
    addMeta('Grammar goal',flag.grammar_goal);
    addMeta('Target vocabulary',(flag.target_words || []).join(', '));
    container.append(metaGrid);

    // Vertical scrollable conversation list for the entire attempt
    const scrollList=document.createElement('div');
    scrollList.className='attempt-scroll-list';

    if(flag.opening){
      const openingRow=document.createElement('div');
      openingRow.className='turn-row opening-row';
      const opHeader=document.createElement('div');
      opHeader.className='turn-row-header';
      opHeader.textContent='Opening line (AI Partner)';
      const opMsg=document.createElement('div');
      opMsg.className='turn-msg ai';
      opMsg.append(document.createTextNode(flag.opening));
      openingRow.append(opHeader,opMsg);
      scrollList.append(openingRow);
    }

    const turns=buildTurnsList(flag);
    for(const t of turns){
      const isFlagged=Boolean(t.is_flagged || (t.id && flag.turn_id && t.id===flag.turn_id) || t.turn_number===flag.turn_number);
      const turnRow=document.createElement('div');
      turnRow.className='turn-row'+(isFlagged?' flagged-turn':'');

      const rowHeader=document.createElement('div');
      rowHeader.className='turn-row-header';
      const turnTitle=document.createElement('span');
      turnTitle.textContent='Turn '+t.turn_number;
      rowHeader.append(turnTitle);
      if(isFlagged){
        const badge=document.createElement('span');
        badge.className='flagged-badge';
        badge.textContent='FLAGGED TURN';
        rowHeader.append(badge);
      }
      turnRow.append(rowHeader);

      const pair=document.createElement('div');
      pair.className='turn-dialogue-pair';

      const lMsg=document.createElement('div');
      lMsg.className='turn-msg learner';
      const lStrong=document.createElement('strong');
      lStrong.textContent='Learner: ';
      lMsg.append(lStrong,document.createTextNode(t.learner_text || ''));

      const aMsg=document.createElement('div');
      aMsg.className='turn-msg ai';
      const aStrong=document.createElement('strong');
      aStrong.textContent='AI Partner: ';
      aMsg.append(aStrong,document.createTextNode(t.ai_reply || ''));

      pair.append(lMsg,aMsg);

      const corrObj = t.correction !== undefined ? t.correction : (isFlagged ? flag.correction : null);
      if(corrObj){
        const cMsg=document.createElement('div');
        cMsg.className='correction';
        cMsg.style.margin='4px 0 0';
        const cStrong=document.createElement('strong');
        cStrong.textContent='Correction: ';
        cMsg.append(cStrong,document.createTextNode(corrObj.explanation));
        if(corrObj.example){
          cMsg.append(document.createTextNode(' (Example: '+corrObj.example+')'));
        }
        pair.append(cMsg);
      }

      turnRow.append(pair);
      scrollList.append(turnRow);
    }

    container.append(scrollList);

    // Accept / Incorrect actions on the detail page
    const actionsRow=document.createElement('div');
    actionsRow.className='review-detail-actions';
    for(const decision of ['Acceptable','Incorrect']){
      const button=document.createElement('button');
      button.className=decision==='Acceptable'?'secondary':'primary';
      button.textContent='Mark '+decision.toLowerCase();
      button.onclick=async()=>{
        if(saving || loading)return;
        lock(true);notice();$('review-status').textContent='Saving decision…';
        let refresh=false;
        try{
          await api('/api/flag/review/',{flag_id:flag.id,status:decision});
          currentFlags=currentFlags.filter(f=>f.id!==flag.id);
          selectedFlagId=null;
          updateUrlFlag(null);
          renderView();
          $('review-status').textContent='Decision saved: '+decision+'.'+(!currentFlags.length?' No text awaiting review.':'');
        }
        catch(error){
          if(error.status===409){
            notice('This item has already been reviewed. The queue has been refreshed.');
            selectedFlagId=null;
            updateUrlFlag(null);
            refresh=true;
          }
          else {
            notice(error.message);
            $('review-status').textContent='Decision was not confirmed. Refresh the queue before retrying if the connection failed.';
            if(error.status===401 || error.status===403){
              currentFlags=[];
              selectedFlagId=null;
              queue.replaceChildren();
            }
          }
        } finally {lock(false);}
        if(refresh)await load(false);
      };
      actionsRow.append(button);
    }
    container.append(actionsRow);
    return container;
  }

  function syncFadeClasses(){
    const collect=node=>[node,...Array.from(node?.children || []).flatMap(collect)];
    for(const el of collect(queue)){
      if(typeof el.className==='string' && el.className.includes('review-text-content')){
        if(typeof el.scrollHeight==='number' && el.scrollHeight>0){
          el.className=el.scrollHeight>24?'review-text-content fade-text':'review-text-content';
        }
      }
    }
  }

  function renderView(){
    queue.replaceChildren();
    if(selectedFlagId!==null){
      const target=currentFlags.find(f=>f.id===selectedFlagId);
      if(target){
        queue.append(detailView(target));
        $('review-status').textContent='Inspecting attempt conversation for Turn '+target.turn_number+'.';
        return;
      }
      selectedFlagId=null;
      updateUrlFlag(null);
    }
    for(const flag of currentFlags)queue.append(card(flag));
    syncFadeClasses();
    $('review-status').textContent=currentFlags.length?currentFlags.length+' unresolved response(s).':'No text awaiting review.';
  }

  async function load(clearNotice=true){
    if(loading || saving)return;
    loading=true;$('review-refresh').disabled=true;if(clearNotice)notice();$('review-status').textContent='Loading queue…';
    queue.replaceChildren();
    try{
      const result=await api('/api/flag/list/');
      if(!Array.isArray(result.flags))throw new Error('Invalid review queue.');
      currentFlags=result.flags;
      syncSelectedFromUrl();
      renderView();
    }
    catch(error){
      currentFlags=[];
      notice(error.message);
      $('review-status').textContent='Queue unavailable. You can retry with Refresh queue.';
    }
    finally{loading=false;$('review-refresh').disabled=false;}
  }

  if(globalThis.addEventListener){
    globalThis.addEventListener('popstate',()=>{
      if(loading || saving)return;
      syncSelectedFromUrl();
      renderView();
    });
    globalThis.addEventListener('resize',syncFadeClasses);
  }

  $('review-refresh').onclick=()=>{selectedFlagId=null;updateUrlFlag(null);return load();};
  $('review-sign-out').onclick=async()=>{
    if(saving)return;
    try{const response=await fetch('/api/auth/logout/',{method:'POST',headers:{'X-CSRFToken':csrf()}});if(!response.ok)throw new Error('Sign out failed.');queue.replaceChildren();location.href='/';}catch(error){notice(error.message);}
  };
  void load();
})();
