'use strict';
const $ = id => document.getElementById(id);
const labels = {page_ready:'Page ready', microphone:'Mic ready', transcription:'Recognition', ai_reply:'AI response', playback:'Playback start', summary:'Summary', confirmation:'Your review time', recording:'Your speaking time', system_total:'System wait'};
const targets = {page_ready:1500,microphone:1000,transcription:5000,ai_reply:5000,playback:1000,summary:500,system_total:11000};
let session = null, ready = false, busy = false, speaking = false, recorder = null, stream = null, audioContext = null, analyser = null;
let chunks = [], recordStarted = 0, recordTimer = null, micRequested = 0, reviewStarted = 0, recognitionWait = 0, lastReply = '', hadVoice = false;
let lessonId = null, progress = null, reopenedSummary = null;
let retainedRecording = null;
let measurements = [];
try { measurements = JSON.parse(localStorage.getItem('speako-timing') || '[]'); if (!Array.isArray(measurements)) measurements = []; } catch { measurements = []; }
const seconds = ms => `${(ms / 1000).toFixed(2)} s`;
function measure(step, ms, result = 'success', serverMs = null) {
  const target = targets[step] ?? null;
  const item = {time:new Date().toISOString(),session:session?.id ?? null,step,ms:Math.round(ms),target_ms:target,result,server_ms:serverMs};
  measurements.push(item); measurements = measurements.slice(-1000);
  try { localStorage.setItem('speako-timing',JSON.stringify(measurements)); } catch {}
  const tag = $(`time-${step}`);
  if (tag) { tag.textContent = `${labels[step]} · ${seconds(ms)} / ${target == null ? 'human time, no limit' : `target ≤ ${seconds(target)}`}${result==='success'?'':` · ${result}`}`; tag.className = 'timing ' + (result==='failed'?'failed':target != null && ms>target?'slow':'fast'); }
  renderMeasurements();
}
function renderMeasurements() {
  const table = $('measurements'); table.replaceChildren();
  for (const item of measurements.slice(-25).reverse()) {
    const row = document.createElement('tr');
    [labels[item.step] || item.step, seconds(item.ms), item.target_ms == null ? 'Human time' : `≤ ${seconds(item.target_ms)}`, item.result==='failed'?'Failed':item.target_ms!=null && item.ms>item.target_ms?'Above target':item.result].forEach(value=>{const cell=document.createElement('td');cell.textContent=value;row.append(cell);});
    table.append(row);
  }
}
function usage(data) {
  if (!data) return;
  $('guard').textContent=`$${(data.guard_usd+data.external_spend_usd).toFixed(2)} / $${data.budget_usd.toFixed(2)}`;
  $('attempts').textContent=data.attempts;
  $('tokens').textContent=(data.prompt_tokens+data.output_tokens).toLocaleString();
  $('billing-note').textContent=data.billing_note+' $0.02 minimum guard per attempt, including failures. Do not enable provider billing.';
}
function error(message='') { $('error').textContent=message; $('error').hidden=!message; }
function csrf() {return document.cookie.split('; ').find(v=>v.startsWith('csrftoken='))?.split('=')[1] || '';}
async function request(url, data={}) {
  const controller = new AbortController(); const timeout=setTimeout(()=>controller.abort(),35000);
  try {
    const form=data instanceof FormData;
    const response=await fetch(url,{method:'POST',headers:form?{'X-CSRFToken':csrf()}:{'X-CSRFToken':csrf(),'Content-Type':'application/json'},body:form?data:JSON.stringify(data),signal:controller.signal});
    const result=await response.json(); usage(result.usage);
    if (!response.ok) { const e=new Error(SpeakoProtocol.error(result.error));e.serverMs=result.server_ms;throw e; }
    return result;
  } catch (e) { if(e.name==='AbortError') throw new Error('The request timed out. Refresh to check whether it completed before retrying.');throw e; }
  finally {clearTimeout(timeout);}
}
function state(message,kind='ready') {$('state').textContent=message;$('state-dot').className='state-dot '+kind;}
function controls() {
  const active=session?.status==='in_progress'; const pending=!!session?.pending; const recording=recorder?.state==='recording';
  $('start').disabled=busy || speaking || recording;
  $('start').textContent=active?'Restart practice':session?'Start new practice →':'Start practice →';
  $('record').disabled=!active || !ready || pending || busy || speaking || recording;
  $('stop').disabled=!recording;
  const canRetry=active && !pending && retainedRecording?.attemptId===session?.id;
  $('retry-recognition').hidden=!canRetry;
  $('retry-recognition').disabled=!canRetry || busy || speaking || recording;
  $('confirm').disabled=!pending || busy || speaking;
  $('discard').disabled=!pending || busy || speaking;
  $('repeat').disabled=!SpeakoSpeech.canRepeat(lastReply, busy, speaking, recording);
  $('exit').disabled=!active || busy || speaking || recording;
  $('lesson-progress').hidden=!progress;$('lesson-progress').textContent=progress?.status || '';
  const lastCompleted=progress?.last_completed_attempt_id;$('view-summary').hidden=!lastCompleted || session?.id===lastCompleted;$('view-summary').disabled=busy || speaking || recording;
  $('progress').textContent=session ? session.status==='completed'?'Lesson complete':session.status==='exited'?'Exited early':`Exchange ${session.turns.length} / ${session.turn_limit}` : 'Ready to begin';
}
function message(text,who) {const div=document.createElement('div');div.className='message '+who;const label=document.createElement('span');label.className='speaker';label.textContent=who==='learner'?'YOU':'WAITER';div.append(label,document.createTextNode(text));$('messages').append(div);}
function correction(c) {const div=document.createElement('div');div.className='correction';const title=document.createElement('strong');title.textContent='A little language help';div.append(title,document.createTextNode(c.explanation),document.createElement('br'),document.createTextNode(`Try: ${c.example}`));$('messages').append(div);}
function wordList(parent,words) {for(const word of words){const span=document.createElement('span');span.textContent=word;parent.append(span);}}
function summary() {
  const completed=session?.status==='completed',data=completed?session.summary:reopenedSummary;
  const panel=$('summary');panel.replaceChildren();panel.hidden=!completed && !data;if(panel.hidden)return;
  if(!data){panel.textContent='Lesson complete. No summary was saved for this attempt.';return;}
  const top=document.createElement('div');top.className='row';const heading=document.createElement('h2');heading.textContent='Nice work. Here is your recap.';const timer=document.createElement('div');timer.id='time-summary';timer.className='timing';timer.textContent='Summary · — / target ≤ 0.5 s';top.append(heading,timer);panel.append(top);
  for(const [label,list] of [['Target words you used',data.used],['Words to try next time',data.unused]]){const h=document.createElement('h3');h.textContent=label;panel.append(h);const div=document.createElement('div');div.className='word-list';if(list.length)wordList(div,list);else div.textContent='None';panel.append(div);}
  const h=document.createElement('h3');h.textContent='Corrections from this lesson';panel.append(h);
  if(!data.corrections.length){const p=document.createElement('p');p.textContent='No corrections were made during this lesson.';panel.append(p);}
  for(const c of data.corrections){const p=document.createElement('p');p.textContent=`You said: ${c.original}\n${c.explanation}\nTry: ${c.example}`;p.style.whiteSpace='pre-wrap';panel.append(p);}
}
async function loadMap() {
  if (globalThis.SpeakoMap) await SpeakoMap.load(async lesson => {
    if(busy || speaking || recorder?.state==='recording') {error('Finish the current step first.');return;}
    if(session?.status==='in_progress' && session.lesson_id!==lesson.id) {error('Exit the current lesson before choosing another.');return;}
    lessonId=lesson.id;
    progress={status:lesson.status_on_map,last_completed_attempt_id:lesson.last_completed_attempt_id};
    if(session && session.lesson_id!==lessonId){session=null;lastReply='';$('messages').replaceChildren();}
    reopenedSummary=null;
    $('lesson-title').textContent=lesson.scenario;
    $('goal').textContent=lesson.grammar_goal;
    $('lesson-grammar').textContent=lesson.grammar_goal;
    $('lesson-turn-limit').textContent=lesson.turn_limit+' exchanges';
    $('vocabulary').replaceChildren();wordList($('vocabulary'),lesson.target_words);
    error();render();
  });
}

function render() {
  if(session?.progress)progress=session.progress;
  if(session){$('messages').replaceChildren();message(session.opening,'ai');for(const turn of session.turns){message(turn.learner,'learner');if(turn.correction)correction(turn.correction);message(turn.reply,'ai');}lastReply=session.turns.at(-1)?.reply || session.opening;}
  $('transcript').hidden=!session?.pending;$('transcript-text').textContent=session?.pending || '';
  summary();controls();$('messages').scrollTop=$('messages').scrollHeight;
}
function play(text,rate=1,onStart=null) {
  if(!('speechSynthesis' in window)){error('Audio playback is unavailable in this browser. You can still read the waiter’s reply.');return Promise.resolve();}
  speaking=true;controls();state('Waiter speaking…','processing');const begun=performance.now();
  return new Promise(resolve=>{
    const utterance=new SpeechSynthesisUtterance(text);utterance.lang='en-US';utterance.rate=rate;
    const english=speechSynthesis.getVoices().find(v=>v.lang==='en-US') || speechSynthesis.getVoices().find(v=>v.lang.startsWith('en'));
    if(english)utterance.voice=english;
    let started=false,done=false;
    const finish=()=>{if(done)return;done=true;clearTimeout(watchdog);speaking=false;state(session?.status==='completed'?'Lesson complete':session?.pending?'Check your transcript':'Ready for your answer');controls();resolve();};
    const watchdog=setTimeout(()=>{speechSynthesis.cancel();if(!started)measure('playback',performance.now()-begun,'failed');error('Playback did not finish. Use Repeat slower or read the reply.');finish();},20000);
    utterance.onstart=()=>{started=true;measure('playback',performance.now()-begun);if(onStart)onStart(performance.now()-begun);};
    utterance.onend=finish;utterance.onerror=()=>{measure('playback',performance.now()-begun,'failed');error('Playback failed. Read the reply or try Repeat slower.');finish();};
    speechSynthesis.speak(utterance);
  });
}
function releaseMic(){if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}if(audioContext){audioContext.close().catch(()=>{});audioContext=null;}analyser=null;$('meter-fill').style.width='0';clearInterval(recordTimer);$('record-duration').textContent='Up to 30 seconds';}
function meter(){if(recorder?.state!=='recording'||!analyser)return;const data=new Uint8Array(analyser.fftSize);analyser.getByteTimeDomainData(data);let sum=0;for(const n of data)sum+=((n-128)/128)**2;const rms=Math.sqrt(sum/data.length);if(rms>.008)hadVoice=true;$('meter-fill').style.width=`${Math.min(100,rms*700)}%`;requestAnimationFrame(meter);}
const micDeniedMessage='Microphone access is blocked, so you cannot answer yet. Enable it in your browser’s site settings (next to the address bar) and in your system privacy settings (macOS: System Settings > Privacy & Security > Microphone; Windows: Settings > Privacy & security > Microphone), then try again.';
async function micDenied(){try{return (await navigator.permissions.query({name:'microphone'})).state==='denied';}catch{return false;}}
function microphoneError(e) {
  if(e.name==='NotAllowedError') return micDeniedMessage;
  if(e.name==='SecurityError') return 'This page cannot use the microphone. Open Speako over HTTPS or on localhost in a current browser, then try again.';
  if(e.name==='NotFoundError') return 'No microphone was found. Connect one, select it as your system input device, and try again.';
  if(e.name==='NotReadableError' || e.name==='AbortError') return 'The microphone could not be started. Check your input device, close other apps using it, and try again.';
  return e.message || 'Recording could not start. Check your microphone and try again.';
}
async function record(){
  error();busy=true;controls();micRequested=performance.now();state('Preparing microphone…','processing');
  try {
    if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)throw new Error('Audio recording is unavailable. Open this local page in a current Chrome or Edge browser.');
    stream=await navigator.mediaDevices.getUserMedia({audio:true});measure('microphone',performance.now()-micRequested);
    const mime=['audio/webm;codecs=opus','audio/webm','audio/mp4','audio/ogg;codecs=opus'].find(t=>MediaRecorder.isTypeSupported(t));
    recorder=mime?new MediaRecorder(stream,{mimeType:mime}):new MediaRecorder(stream);chunks=[];hadVoice=false;
    try{audioContext=new (window.AudioContext||window.webkitAudioContext)();await audioContext.resume();analyser=audioContext.createAnalyser();analyser.fftSize=256;audioContext.createMediaStreamSource(stream).connect(analyser);}catch{analyser=null;hadVoice=true;}
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};recorder.onstop=processRecording;
    retainedRecording=null;recorder.start();recordStarted=performance.now();busy=false;state('Listening — speak now','recording');$('record-duration').textContent='0.0 / 30 s';controls();meter();
    recordTimer=setInterval(()=>{const secondsElapsed=(performance.now()-recordStarted)/1000;$('record-duration').textContent=`${secondsElapsed.toFixed(1)} / 30 s`;if(secondsElapsed>=30)stop();},100);
  }catch(e){measure('microphone',performance.now()-micRequested,'failed');releaseMic();busy=false;state('Microphone unavailable');error(microphoneError(e));controls();}
}
function stop(){if(recorder?.state==='recording'){measure('recording',performance.now()-recordStarted);recorder.stop();$('stop').disabled=true;busy=true;controls();}}
async function processRecording(){
  const mime=recorder.mimeType.split(';')[0];const blob=new Blob(chunks,{type:mime});releaseMic();busy=true;controls();
  if(!hadVoice || blob.size<100){busy=false;state('Ready for your answer');error('No voice activity was detected. Nothing was sent for evaluation. Please record again.');controls();return;}
  retainedRecording={blob, attemptId:session.id};
  await recognizeRetainedRecording();
  chunks=[];
}
async function recognizeRetainedRecording(){
  if(!retainedRecording || retainedRecording.attemptId!==session?.id || session?.pending || session?.status!=='in_progress')return;
  error();busy=true;controls();state('Recognizing your words…','processing');
  const begun=performance.now();const form=new FormData();
  form.append('audio',retainedRecording.blob,'answer');form.append('attempt_id',retainedRecording.attemptId);
  try{const result=await request('/api/transcribe/',form);recognitionWait=performance.now()-begun;session=SpeakoProtocol.attempt(result.attempt);retainedRecording=null;render();measure('transcription',recognitionWait,'success',result.server_ms);reviewStarted=performance.now();state('Check the recognized text before continuing');}
  catch(e){measure('transcription',performance.now()-begun,'failed',e.serverMs);error(e.message);state('Recognition failed — retry this recording or record again');}
  finally{busy=false;controls();}
}
$('retry-recognition').onclick=recognizeRetainedRecording;
$('start').onclick=async()=>{if(await micDenied()){state('Microphone unavailable');error(micDeniedMessage);return;}if(session?.status==='in_progress'&&!window.confirm('Restart this unfinished lesson? No summary will be created.'))return;error();busy=true;controls();try{const result=await request('/api/start/',{lesson_id:lessonId});session=SpeakoProtocol.attempt(result.attempt);retainedRecording=null;reopenedSummary=null;recognitionWait=0;render();busy=false;await play(lastReply);}catch(e){error(e.message);}finally{busy=false;controls();}};
$('record').onclick=record;$('stop').onclick=stop;
$('view-summary').onclick=async()=>{error();try{const response=await fetch(`/api/attempts/${progress.last_completed_attempt_id}/summary/`);const result=await response.json();if(!response.ok)throw new Error(SpeakoProtocol.error(result.error));reopenedSummary=result.summary;render();$('summary').scrollIntoView({block:'nearest'});}catch(e){error(e.message);}};
$('discard').onclick=async()=>{error();busy=true;controls();try{const result=await request('/api/discard/',SpeakoProtocol.confirmation(session));measure('confirmation',performance.now()-reviewStarted,'discarded');session=SpeakoProtocol.attempt(result.attempt);recognitionWait=0;render();state('Old transcript discarded. Record again.');}catch(e){error(e.message);}finally{busy=false;controls();}};
$('confirm').onclick=async()=>{
  error();measure('confirmation',performance.now()-reviewStarted);busy=true;controls();state('Your waiter is thinking…','processing');const begun=performance.now();
  try{const result=await request('/api/reply/',SpeakoProtocol.confirmation(session));const replyWait=performance.now()-begun;session=SpeakoProtocol.attempt(result.attempt);render();measure('ai_reply',replyWait,'success',result.server_ms);if(result.summary_ms!=null)measure('summary',result.summary_ms);void loadMap();
    busy=false;await play(lastReply,1,playbackMs=>measure('system_total',recognitionWait+replyWait+playbackMs));
  }catch(e){measure('ai_reply',performance.now()-begun,'failed',e.serverMs);error(e.message);state('AI response failed — retry Continue');}finally{busy=false;controls();}
};
$('repeat').onclick=()=>{error();SpeakoSpeech.repeatSlower(lastReply, window.speechSynthesis, play);};
$('exit').onclick=async()=>{if(!window.confirm('Exit this unfinished lesson? No summary will be created.'))return;error();busy=true;controls();try{const result=await request('/api/exit/',{attempt_id:session.id});session=SpeakoProtocol.attempt(result.attempt);render();state('Lesson exited. No summary was created.');void loadMap();}catch(e){error(e.message);}finally{busy=false;controls();}};
$('export').onclick=async()=>{try{const response=await fetch('/api/metrics/');if(!response.ok)throw new Error('Unable to load server measurements.');const ledger=await response.json();const blob=new Blob([JSON.stringify({prototype:'v0.1.2',exported_at:new Date().toISOString(),note:'Suggested timing targets; human time excluded from system wait. Local budget guard is not a provider invoice.',targets_ms:targets,browser_measurements:measurements,...ledger},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`speako-test-${Date.now()}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}catch(e){error(e.message);}};
$('sign-in-form').onsubmit=async event=>{event.preventDefault();error();try{await request('/api/auth/login/',{username:$('username').value,password:$('password').value});$('password').value='';location.reload();}catch(e){error(e.message);}};
$('sign-out').onclick=async()=>{try{const response=await fetch('/api/auth/logout/',{method:'POST',headers:{'X-CSRFToken':csrf()}});if(!response.ok)throw new Error('Sign out failed.');session=null;localStorage.removeItem('speako-timing');location.reload();}catch(e){error(e.message);}};
window.addEventListener('beforeunload',()=>{releaseMic();if('speechSynthesis' in window)speechSynthesis.cancel();});
(async()=>{try{const response=await fetch('/api/status/');if(!response.ok)throw new Error('Could not load Speako.');const data=await response.json();Object.assign(targets,data.targets);lessonId=data.lesson.id;$('account-name').textContent=data.user ? 'Signed in as '+data.user.username : 'Sign in to practice';$('sign-out').hidden=!data.user;$('sign-in-form').hidden=!!data.user;ready=data.api_ready;session=SpeakoProtocol.attempt(data.attempt);progress=data.progress;usage(data.usage);wordList($('vocabulary'),data.lesson.target_words);if(globalThis.SpeakoMap){$('lesson-title').textContent=data.lesson.title;$('lesson-turn-limit').textContent=data.lesson.turn_limit+' exchanges';$('lesson-grammar').textContent=data.lesson.grammar;void loadMap();}$('setup').hidden=ready;$('setup').textContent=data.setup_message;render();if(session?.pending){reviewStarted=performance.now();state('Review your pending transcript');}else if(session?.status==='completed')state(session.summary?'Your saved summary is available':'Lesson complete');else if(session?.status==='in_progress'){if(await micDenied()){state('Microphone unavailable');error(micDeniedMessage);}else state('Ready for your answer');}measure('page_ready',performance.now());renderMeasurements();}catch(e){error(e.message);}})();
