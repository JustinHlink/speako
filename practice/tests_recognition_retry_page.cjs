const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = name => fs.readFileSync(path.join(__dirname, 'static/practice', name), 'utf8');
const IN_PROGRESS = {attempt_id:'a', status:'In progress', turn_limit:5, turns:[], pending:null, opening:'Hello!',
  summary:null, progress:{status:'In progress', last_completed_attempt_id:null}};
const IDLE_TIMER = 'Up to 30 seconds';

function element() {
  return {textContent:'', hidden:false, disabled:false, className:'', value:'', style:{}, scrollTop:0, scrollHeight:0,
    append() {}, replaceChildren() {}, scrollIntoView() {}};
}

async function loadPage({attempt = null, permission = 'granted', getUserMedia, failRecognition = true} = {}) {
  const elements = {error:{...element(), hidden:true}, 'record-duration':{...element(), textContent:IDLE_TIMER}};
  const calls = [], timers = new Map();
  const page = {now: 1000, calls, recorder: null, tracksStopped: 0, level: 128};
  let nextTimer = 1;
  class FakeRecorder {
    static isTypeSupported() { return true; }
    constructor() { this.state = 'inactive'; this.mimeType = 'audio/webm'; page.recorder = this; }
    start() { this.state = 'recording'; }
    stop() { this.state = 'inactive'; this.onstop(); }
  }
  class FakeAudioContext {
    async resume() {}
    async close() {}
    createMediaStreamSource() { return {connect() {}}; }
    createAnalyser() { return {fftSize:256, getByteTimeDomainData: data => data.fill(page.level)}; }
  }
  const browser = {
    console, Blob, FormData, URL, AbortController,
    document: {
      cookie: '',
      getElementById: id => (elements[id] ??= element()),
      createElement: element,
      createTextNode: text => text,
    },
    localStorage: {getItem: () => null, setItem() {}, removeItem() {}},
    location: {reload() {}},
    performance: {now: () => page.now},
    navigator: {
      permissions: {query: async () => {
        if (permission === 'unsupported') throw new TypeError('microphone is not a permission name');
        return {state: permission};
      }},
      mediaDevices: {getUserMedia: getUserMedia || (async () => ({getTracks: () => [{stop() { page.tracksStopped += 1; }}]}))},
    },
    MediaRecorder: FakeRecorder,
    AudioContext: FakeAudioContext,
    SpeechSynthesisUtterance: class {},
    speechSynthesis: {getVoices: () => [], cancel() {}, speak(utterance) { utterance.onstart?.(); utterance.onend?.(); }},
    requestAnimationFrame() {},
    setTimeout: () => 0,
    clearTimeout() {},
    setInterval(callback) { timers.set(nextTimer, callback); return nextTimer++; },
    clearInterval(id) { timers.delete(id); },
    addEventListener() {},
    confirm: () => true,
    fetch: async (url, options) => {
      calls.push(url);
      if(url === '/api/transcribe/'){
        page.lastAudio=options.body.get('audio');
        if(failRecognition) return {ok:false,json:async()=>({error:'Transient recognition error'})};
        return {ok:true,json:async()=>({attempt:{...IN_PROGRESS,pending:{id:'retry-pending',text:'water please'}}})};
      }
      const body = url === '/api/status/'
        ? {lesson:{id:1, target_words:[]}, targets:{}, api_ready:true, setup_message:'', user:{username:'learner'}, attempt, progress:attempt?.progress ?? null}
        : {attempt:IN_PROGRESS};
      return {ok:true, status:200, json: async () => body};
    },
  };
  browser.window = browser;
  vm.createContext(browser);
  vm.runInContext(source('protocol.js'), browser);
  vm.runInContext(source('speech.js'), browser);
  vm.runInContext(source('app.js'), browser);
  page.run = expression => vm.runInContext(expression,browser);
  page.setRecognitionSuccess = () => {failRecognition=false;};
  page.el = id => browser.document.getElementById(id);
  page.settle = async () => { for (let i = 0; i < 20; i += 1) await new Promise(setImmediate); };
  page.click = async id => { await page.el(id).onclick(); await page.settle(); };
  page.tick = ms => {
    for (let elapsed = 0; elapsed < ms; elapsed += 100) {
      page.now += 100;
      for (const callback of [...timers.values()]) callback();
    }
  };
  await page.settle();
  return page;
}

(async()=>{
 const page=await loadPage({attempt:IN_PROGRESS});
 page.run("retainedRecording={blob:new Blob(['voice'],{type:'audio/webm'}),attemptId:'a'};controls();");
 await page.click('retry-recognition');
 assert.equal(page.el('retry-recognition').hidden,false);
 assert.equal(page.el('record').disabled,false);
 assert.equal(page.run('session.turns.length'),0);
 assert.equal(page.run('session.pending'),'');
 assert.equal(page.lastAudio.size,5);
 page.setRecognitionSuccess();
 await page.click('retry-recognition');
 assert.equal(page.el('retry-recognition').hidden,true);
 assert.equal(page.run('session.pending'),'water please');
 assert.equal(page.run('session.turns.length'),0);
 assert.equal(page.calls.filter(url=>url==='/api/transcribe/').length,2);
 assert.equal(page.calls.filter(url=>url==='/api/reply/').length,0);
 page.run("session.pending='';retainedRecording={blob:new Blob(['old']),attemptId:'another-attempt'};controls();");
 const before=page.calls.length;
 await page.click('retry-recognition');
 assert.equal(page.calls.length,before);
 assert.equal(page.el('retry-recognition').hidden,true);
 console.log('Retained recording retry checks passed.');
})().catch(error=>{console.error(error);process.exit(1);});
