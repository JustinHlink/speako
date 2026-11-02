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

async function loadPage(attempt) {
  const elements = {};
  const requests = [];
  const spoken = [];
  const speechSynthesis = {speaking: false, getVoices: () => [], speak: u => spoken.push(u), cancel() {}};
  const status = {
    lesson: {id: 1, target_words: ['menu', 'tea']}, targets: {}, user: {username: 'learner', role: 'Learner'},
    api_ready: true, setup_message: '', usage: null, attempt,
  };
  const context = vm.createContext({
    console, speechSynthesis,
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
    setTimeout: () => 0,
    clearTimeout() {},
    fetch: async url => { requests.push(url); return {ok: true, json: async () => status}; },
  });
  for (const file of ['protocol.js', 'speech.js', 'app.js']) {
    const source = fs.readFileSync(path.join(__dirname, 'static', 'practice', file), 'utf8');
    vm.runInContext(source, context, {filename: file});
  }
  await new Promise(resolve => setImmediate(resolve));
  const session = () => vm.runInContext('session', context);
  return {elements, requests, spoken, session};
}

(async () => {
  const page = await loadPage(ATTEMPT);
  assert.equal(page.elements.repeat.disabled, false);
  assert.equal(page.elements.progress.textContent, 'Exchange 2 / 5');
  const requestsBefore = page.requests.length;

  page.elements.repeat.onclick();

  assert.equal(page.spoken.length, 1);
  assert.equal(page.spoken[0].text, LATEST);
  assert.equal(page.spoken[0].rate, 0.75);
  assert.equal(page.requests.length, requestsBefore);
  assert.equal(page.session().turns.length, 2);
  assert.equal(page.session().pending, 'Yes please.');
  assert.equal(page.session().pending_id, 'pending-3');
  assert.equal(page.elements.progress.textContent, 'Exchange 2 / 5');
  assert.equal(page.elements['transcript-text'].textContent, 'Yes please.');
  assert.equal(page.elements.repeat.disabled, true);

  page.spoken[0].onend();
  assert.equal(page.elements.repeat.disabled, false);

  const fresh = await loadPage({...ATTEMPT, turns: [], pending: null});
  fresh.elements.repeat.onclick();
  assert.equal(fresh.spoken[0].text, OPENING);

  const notStarted = await loadPage(null);
  assert.equal(notStarted.elements.repeat.disabled, true);
  notStarted.elements.repeat.onclick();
  assert.equal(notStarted.spoken.length, 0);
  assert.equal(notStarted.requests.length, 1);

  console.log('Repeat slower page checks passed.');
})().catch(error => { console.error(error); process.exit(1); });