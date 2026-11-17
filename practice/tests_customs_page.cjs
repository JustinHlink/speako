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
    lesson: {id: 2, title:'Passing Customs', grammar:'Short answers', turn_limit:5, target_words:['passport','bag'], presentation:{speaker:'OFFICER',partner:'The customs officer',goal:'Answer questions about your visit.',context_title:'Your visit',context_items:['Ten days','One bag']}}, targets: {}, user: {username: 'learner', role: 'Learner'},
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

(async()=>{
 const page=await loadPage({...ATTEMPT,lesson_id:2,pending:null,opening:'Can I see your passport, please?'},'ok');
 assert.equal(page.elements['conversation-heading'].textContent,'The customs officer');
 assert.equal(page.elements['context-title'].textContent,'Your visit');
 assert.equal(page.elements['context-items'].children.length,2);
 assert.equal(page.elements.messages.children[0].children[0].textContent,'OFFICER');
 assert.equal(page.elements['lesson-title'].textContent,'Passing Customs');
 assert.equal(page.elements.record.disabled,false);
 console.log('Customs page: officer label, context, lesson title and recording controls passed.');
})().catch(error=>{console.error(error);process.exit(1)});
