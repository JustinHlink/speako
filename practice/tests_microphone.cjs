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

async function loadPage({attempt = null, permission = 'granted', getUserMedia} = {}) {
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
    fetch: async url => {
      calls.push(url);
      const body = url === '/api/status/'
        ? {lesson:{id:1, target_words:[]}, targets:{}, api_ready:true, setup_message:'', user:{username:'learner'}, attempt, progress:attempt?.progress ?? null}
        : {attempt:IN_PROGRESS};
      return {ok:true, status:200, json: async () => body};
    },
  };
  browser.window = browser;
  vm.createContext(browser);
  vm.runInContext(source('protocol.js'), browser);
  vm.runInContext(source('app.js'), browser);
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

function assertDeniedPrompt(page) {
  assert.equal(page.el('error').hidden, false);
  assert.match(page.el('error').textContent, /Microphone access is blocked/);
  assert.match(page.el('error').textContent, /Enable it in your browser/);
  assert.equal(page.el('state').textContent, 'Microphone unavailable');
}

function micError(name) {
  return loadPage({attempt:IN_PROGRESS, getUserMedia: async () => { throw Object.assign(new Error('raw browser text'), {name}); }});
}

const tests = {
  async 'denied permission blocks starting a lesson and shows the prompt'() {
    const page = await loadPage({permission:'denied'});
    assert.equal(page.el('error').hidden, true);
    await page.click('start');
    assertDeniedPrompt(page);
    assert.ok(!page.calls.includes('/api/start/'));
  },
  async 'denied permission shows the prompt when continuing a lesson'() {
    assertDeniedPrompt(await loadPage({attempt:IN_PROGRESS, permission:'denied'}));
  },
  async 'allowed permission starts a lesson with no prompt'() {
    const page = await loadPage();
    await page.click('start');
    assert.ok(page.calls.includes('/api/start/'));
    assert.equal(page.el('error').hidden, true);
  },
  async 'continuing a lesson with allowed permission shows no prompt'() {
    const page = await loadPage({attempt:IN_PROGRESS});
    assert.equal(page.el('error').hidden, true);
    assert.equal(page.el('state').textContent, 'Ready for your answer');
  },
  async 'a browser without the microphone permission query can still start'() {
    const page = await loadPage({permission:'unsupported'});
    await page.click('start');
    assert.ok(page.calls.includes('/api/start/'));
    assert.equal(page.el('error').hidden, true);
  },
  async 'denial while recording shows the prompt and never starts listening'() {
    const page = await micError('NotAllowedError');
    await page.click('record');
    assertDeniedPrompt(page);
    assert.equal(page.el('record-duration').textContent, IDLE_TIMER);
    assert.equal(page.recorder, null);
  },
  async 'other microphone failures explain themselves on any platform'() {
    const expected = {SecurityError:/HTTPS or on localhost/, NotFoundError:/No microphone was found/,
      NotReadableError:/could not be started/, AbortError:/could not be started/};
    for (const [name, message] of Object.entries(expected)) {
      const page = await micError(name);
      await page.click('record');
      assert.match(page.el('error').textContent, message);
      assert.doesNotMatch(page.el('error').textContent, /Windows|raw browser text/);
    }
  },
  async 'Listening and the timer appear together and stay until Stop'() {
    const page = await loadPage({attempt:IN_PROGRESS});
    await page.click('record');
    assert.match(page.el('state').textContent, /^Listening/);
    assert.equal(page.el('record-duration').textContent, '0.0 / 30 s');
    assert.equal(page.el('stop').disabled, false);
    page.tick(1000);
    assert.equal(page.el('record-duration').textContent, '1.0 / 30 s');
    page.tick(10500);
    assert.equal(page.el('record-duration').textContent, '11.5 / 30 s');
    assert.match(page.el('state').textContent, /^Listening/);
    assert.equal(page.recorder.state, 'recording');
  },
  async 'Stop ends listening, resets the timer and releases the microphone'() {
    const page = await loadPage({attempt:IN_PROGRESS});
    await page.click('record');
    page.tick(2000);
    await page.click('stop');
    assert.equal(page.recorder.state, 'inactive');
    assert.doesNotMatch(page.el('state').textContent, /^Listening/);
    assert.equal(page.el('record-duration').textContent, IDLE_TIMER);
    assert.equal(page.tracksStopped, 1);
    page.tick(5000);
    assert.equal(page.el('record-duration').textContent, IDLE_TIMER);
  },
  async 'recording stops by itself at the 30 second limit'() {
    const page = await loadPage({attempt:IN_PROGRESS});
    await page.click('record');
    page.tick(29900);
    assert.equal(page.recorder.state, 'recording');
    page.tick(100);
    await page.settle();
    assert.equal(page.recorder.state, 'inactive');
    assert.equal(page.el('record-duration').textContent, IDLE_TIMER);
    assert.equal(page.tracksStopped, 1);
  },
  async 'the level meter follows the input volume'() {
    const quiet = await loadPage({attempt:IN_PROGRESS});
    await quiet.click('record');
    assert.equal(quiet.el('meter-fill').style.width, '0%');
    const loud = await loadPage({attempt:IN_PROGRESS});
    loud.level = 160;
    await loud.click('record');
    assert.notEqual(parseFloat(loud.el('meter-fill').style.width), 0);
  },
};

(async () => {
  for (const [name, test] of Object.entries(tests)) {
    try { await test(); } catch (error) { error.message = `${name}: ${error.message}`; throw error; }
  }
  console.log(`Microphone checks passed (${Object.keys(tests).length}).`);
})().catch(error => { console.error(error.message); process.exit(1); });
