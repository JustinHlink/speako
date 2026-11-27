const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function element() {
  return {
    children: [],
    textContent: '',
    className: '',
    hidden: false,
    disabled: false,
    value: '',
    style: {},
    append(...items) {
      for (const item of items) {
        if (item && typeof item === 'object') item.parent = this;
        this.children.push(item);
      }
    },
    replaceChildren(...items) {
      this.children = [];
      this.append(...items);
    },
    querySelectorAll() {
      let result = [];
      for (const child of this.children) {
        if (child?.tag === 'button') result.push(child);
        if (child?.querySelectorAll) result.push(...child.querySelectorAll());
      }
      return result;
    }
  };
}

const SAMPLE_LESSONS = [
  {id: 1, scenario: 'Ordering at a Restaurant', grammar_goal: 'Polite requests', turn_limit: 5, status_on_map: 'Completed'},
  {id: 2, scenario: 'Passing Customs', grammar_goal: 'Short answers', turn_limit: 5, status_on_map: 'In progress'},
  {id: 3, scenario: 'Hotel Check-in', grammar_goal: 'Asking questions', turn_limit: 5, status_on_map: 'Not started'}
];

async function createMapPage({lessonsStatus = 200, lessons = SAMPLE_LESSONS, loginRole = 'Learner', failNetwork = false} = {}) {
  const nodes = {};
  const location = {href: '/map/'};
  const context = vm.createContext({
    console,
    AbortController,
    setTimeout: () => 0,
    clearTimeout() {},
    location,
    document: {
      cookie: 'csrftoken=test-csrf',
      getElementById: id => (nodes[id] ??= element()),
      createElement: tag => Object.assign(element(), {tag}),
      createTextNode: text => ({text})
    },
    fetch: async (url) => {
      if (url === '/api/auth/login/') {
        lessonsStatus = 200;
        return {
          ok: true,
          status: 200,
          json: async () => ({user: {id: 1, username: nodes.username?.value || 'learner1', role: loginRole}})
        };
      }
      if (url === '/api/auth/logout/') {
        lessonsStatus = 401;
        return {ok: true, status: 204, json: async () => ({})};
      }
      if (url === '/api/lessons/') {
        if (failNetwork) throw new Error('Network error');
        if (lessonsStatus !== 200) return {ok: false, status: lessonsStatus, json: async () => ({})};
        return {ok: true, status: 200, json: async () => ({lessons})};
      }
      if (url.startsWith('/api/lessons/')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({lesson: {id: 1, scenario: 'Ordering at a Restaurant', target_words: ['water', 'menu'], last_completed_attempt_id: 'att-1'}})
        };
      }
      if (url === '/api/attempts/att-1/summary/') {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            summary: {used: ['water'], unused: ['menu'], corrections: [{original: 'I wants water', explanation: 'Use want', example: 'I want water'}]},
            attempt: {
              attempt_id: 'att-1',
              turns: [
                {number: 1, learner: 'Hello', reply: 'Welcome', review_incorrect: false, flag_status: null},
                {number: 2, learner: 'Water please', reply: 'Wrong AI output', review_incorrect: true, flag_status: 'Incorrect'}
              ]
            }
          })
        };
      }
      return {ok: true, status: 200, json: async () => ({})};
    }
  });

  const code = fs.readFileSync(path.join(__dirname, 'static', 'practice', 'map_page.js'), 'utf8');
  vm.runInContext(code, context);
  await new Promise(setImmediate);
  await new Promise(setImmediate);
  return {nodes, el: id => (nodes[id] ??= element()), location, setNetworkFail(v) { failNetwork = v; }, setLessonsStatus(s) { lessonsStatus = s; }};
}

(async () => {
  // 1. Unauthenticated 401 state and login flow on map page
  const unauth = await createMapPage({lessonsStatus: 401});
  assert.match(unauth.nodes['map-status'].textContent, /Sign in above/);
  assert.equal(unauth.nodes['map-grid'].children.length, 0);
  assert.equal(unauth.nodes['map-grid'].hidden, true);
  assert.equal(unauth.nodes['map-lessons-header'].hidden, true);

  unauth.el('username').value = 'learner1';
  unauth.el('password').value = 'pass1234';
  await unauth.nodes['sign-in-form'].onsubmit({preventDefault() {}});
  await new Promise(setImmediate);
  assert.equal(unauth.nodes['account-name'].textContent, 'Signed in as learner1');
  assert.equal(unauth.nodes['sign-in-form'].hidden, true);
  assert.equal(unauth.nodes['sign-out'].hidden, false);
  assert.equal(unauth.nodes['map-grid'].hidden, false);
  assert.equal(unauth.nodes['map-lessons-header'].hidden, false);
  assert.equal(unauth.nodes['map-grid'].children.length, 3);
  assert.equal(unauth.nodes['stat-total'].textContent, '3');
  assert.equal(unauth.nodes['stat-completed'].textContent, '1');
  assert.equal(unauth.nodes['stat-in-progress'].textContent, '1');
  assert.equal(unauth.nodes['stat-not-started'].textContent, '1');

  // 2. Selecting a lesson navigates to /?lesson_id=<id>
  const firstCardButtons = unauth.nodes['map-grid'].children[0].querySelectorAll();
  assert.equal(firstCardButtons.length, 2); // [Practice again ->, View last summary]
  await firstCardButtons[1].onclick();
  assert.equal(unauth.nodes['map-summary-panel'].hidden, false);
  const allRecapNodes = node => [node, ...(node.children || []).flatMap(allRecapNodes)];
  const incorrectNodes = allRecapNodes(unauth.nodes['map-summary-panel']).filter(n => String(n.className).includes('reviewer-incorrect'));
  assert.equal(incorrectNodes.length, 1);
  const allTexts = node => [node.textContent || node.text || '', ...(node.children || []).flatMap(allTexts)];
  assert.ok(allTexts(incorrectNodes[0]).some(t => t.includes('Marked Incorrect by Reviewer')));

  firstCardButtons[0].onclick();
  assert.equal(unauth.location.href, '/?lesson_id=1');

  // 3. Reviewer login from map page redirects to /review/
  const revPage = await createMapPage({lessonsStatus: 401, loginRole: 'Reviewer'});
  await revPage.nodes['sign-in-form'].onsubmit({preventDefault() {}});
  assert.equal(revPage.location.href, '/review/');

  // 4. Sign out clears map cards and restores sign-in prompt
  await unauth.nodes['sign-out'].onclick();
  assert.equal(unauth.nodes['map-grid'].children.length, 0);
  assert.equal(unauth.nodes['map-grid'].hidden, true);
  assert.equal(unauth.nodes['map-lessons-header'].hidden, true);
  assert.equal(unauth.nodes['sign-in-form'].hidden, false);
  assert.match(unauth.nodes['map-status'].textContent, /Sign in above/);

  // 5. Network failure shows retry button and recovers on retry
  const netPage = await createMapPage({failNetwork: true});
  assert.equal(netPage.nodes['map-retry'].hidden, false);
  netPage.setNetworkFail(false);
  await netPage.nodes['map-retry'].onclick();
  assert.equal(netPage.nodes['map-grid'].children.length, 3);

  console.log('Learning map page: login component, role redirect, stats, lesson cards, summary view, sign-out and retry passed.');
})().catch(err => {
  console.error(err);
  process.exit(1);
});
