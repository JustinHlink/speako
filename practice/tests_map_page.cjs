const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const OPENING = 'Hello! Welcome. What would you like today?';
const LATEST = 'Would you like hot tea?';
const ATTEMPT = {
  attempt_id: 'attempt-1', lesson_id: 1, status: 'In progress', opening: OPENING, turn_limit: 5, summary: null,
  turns: [
    {number: 1, learner: 'I would like a menu.', reply: 'Here is the menu.', correction: null},
    {number: 2, learner: 'I want tea.', reply: LATEST, correction: null},
  ],
  pending: {id: 'pending-3', text: 'Yes please.'},
};

function element() {
  return {
    style: {}, children: [], disabled: false, hidden: false, textContent: '', className: '', value: '',
    append(...nodes) { this.children.push(...nodes); },
    replaceChildren(...nodes) { this.children = nodes; },
  };
}

async function loadPage(attempt, mapMode = 'network') {
  const elements = {};
  const requests = [];
  const spoken = [];
  const speechSynthesis = {speaking: false, getVoices: () => [], speak: u => spoken.push(u), cancel() {}};
  const status = {
    lesson: {id: 1, target_words: ['menu', 'tea']}, targets: {}, user: {username: 'learner', role: 'Learner'},
    api_ready: true, setup_message: '', usage: null, attempt,
  };
  const context = vm.createContext({
    console, speechSynthesis, AbortController, FormData: class {}, navigator: {permissions: {query: async () => ({state:'granted'})}},
    window: {speechSynthesis, addEventListener() {}},
    document: {
      cookie: '',
      getElementById: id => (elements[id] ??= element()),
      createElement: () => element(),
      createTextNode: text => ({text}),
    },
    SpeechSynthesisUtterance: function (text) { this.text = text; },
    localStorage: {getItem: () => null, setItem() {}, removeItem() {}},
    performance: {now: () => 0},
    setTimeout: (fn, ms) => {if(ms === 8000 && mapMode === 'timeout') setImmediate(fn);return 0;},
    clearTimeout() {},
    fetch: async (url, options = {}) => {
      requests.push(url);
      if (url === '/api/lessons/') {
        if (mapMode === 'timeout') return new Promise((resolve,reject) => options.signal.addEventListener('abort',()=>reject(new Error('Aborted'))));
        if (mapMode === 'hang') return new Promise(() => {});
        if (mapMode === 'network') throw new Error('Network down');
        if (mapMode === '401' || mapMode === '403') return {ok:false,status:Number(mapMode)};
        if (mapMode === 'http') return {ok:false};
        if (mapMode === 'json') return {ok:true,json:async()=>{throw new Error('Bad JSON');}};
        return {ok:true,json:async()=>({lessons:[]})};
      }
      if (url === '/api/reply/') return {ok:true,json:async()=>({attempt:{...attempt,pending:null,turns:[...attempt.turns,{learner:'Yes please.',reply:'Here is your water.',correction:null}]}})};
      return {ok:true,json:async()=>status};
    },
  });
  for (const file of ['protocol.js', 'speech.js', 'map.js', 'app.js']) {
    const source = fs.readFileSync(path.join(__dirname, 'static', 'practice', file), 'utf8');
    vm.runInContext(source, context, {filename: file});
  }
  await new Promise(resolve => setImmediate(resolve));
  const session = () => vm.runInContext('session', context);
  return {elements, requests, spoken, session, setMapMode(value){mapMode=value;}};
}

(async () => {
  for (const mode of ['network','http','json','timeout','hang']) {
    const page = await loadPage({...ATTEMPT,pending:null},mode);
    assert.equal(page.elements.progress.textContent,'Exchange 2 / 5',mode);
    assert.equal(page.elements.record.disabled,false,mode);
    assert.equal(page.elements.error?.hidden ?? true,true,mode);
    if(mode !== 'hang') {
      assert.equal(page.elements['map-status'].hidden,false);
      assert.equal(page.elements['map-retry'].hidden,false);
      page.setMapMode('ok');
      await page.elements['map-retry'].onclick();
      assert.equal(page.elements['map-status'].hidden,true);
      assert.equal(page.elements['map-retry'].hidden,true);
    }
    const pending = await loadPage(ATTEMPT,mode);
    const confirmation = pending.elements.confirm.onclick();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(pending.spoken.length,1,mode);
    assert.equal(pending.spoken[0].text,'Here is your water.');
    pending.spoken[0].onend();
    await confirmation;
    assert.equal(pending.session().pending,'');
    assert.equal(pending.session().turns.length,3);
    assert.equal(pending.elements.record.disabled,false);
    assert.equal(pending.elements.error?.hidden ?? true,true);
    assert.ok(!pending.elements.state.textContent.includes('failed'));
  }
  for (const mode of ['401','403']) {
    const page = await loadPage(null,mode);
    assert.match(page.elements['map-status'].textContent,/Sign in/);
    assert.equal(page.elements['map-retry'].hidden,true);
    assert.equal(page.elements['map-status'].hidden,false);
  }
  console.log('Map failure isolation checks passed (network, HTTP, JSON, hanging request, retry, startup and saved reply).');
})().catch(error => {console.error(error);process.exit(1);});

