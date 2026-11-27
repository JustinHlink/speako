'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const grid = $('map-grid');
  const statusEl = $('map-status');
  const errorEl = $('map-error');
  const retryBtn = $('map-retry');
  const refreshBtn = $('map-refresh');
  const overview = $('map-overview');
  const summaryPanel = $('map-summary-panel');
  let loading = false;

  const csrf = () => document.cookie.split('; ').find(v => v.startsWith('csrftoken='))?.split('=')[1] || '';

  function showError(msg = '') {
    if (!errorEl) return;
    errorEl.textContent = msg;
    errorEl.hidden = !msg;
  }

  function statusClass(status) {
    if (status === 'Completed') return 'completed';
    if (status === 'In progress') return 'in-progress';
    return 'not-started';
  }

  function actionLabel(status) {
    if (status === 'In progress') return 'Continue lesson →';
    if (status === 'Completed') return 'Practice again →';
    return 'Start lesson →';
  }

  function updateStats(lessons) {
    if (!overview) return;
    if (!lessons.length) {
      overview.hidden = true;
      return;
    }
    const completed = lessons.filter(l => l.status_on_map === 'Completed').length;
    const inProgress = lessons.filter(l => l.status_on_map === 'In progress').length;
    const notStarted = lessons.length - completed - inProgress;
    if ($('stat-total')) $('stat-total').textContent = String(lessons.length);
    if ($('stat-completed')) $('stat-completed').textContent = String(completed);
    if ($('stat-in-progress')) $('stat-in-progress').textContent = String(inProgress);
    if ($('stat-not-started')) $('stat-not-started').textContent = String(notStarted);
    overview.hidden = false;
  }

  function renderSummary(scenario, data, attempt) {
    if (!summaryPanel) return;
    summaryPanel.replaceChildren();
    if (!data) {
      summaryPanel.hidden = true;
      return;
    }
    const top = document.createElement('div');
    top.className = 'row';
    const heading = document.createElement('h2');
    heading.textContent = `${scenario} · Last completed summary`;
    const closeBtn = document.createElement('button');
    closeBtn.className = 'secondary';
    closeBtn.textContent = 'Close summary';
    closeBtn.onclick = () => { summaryPanel.hidden = true; summaryPanel.replaceChildren(); };
    top.append(heading, closeBtn);
    summaryPanel.append(top);

    for (const [label, list] of [['Target words you used', data.used || []], ['Words to try next time', data.unused || []]]) {
      const h = document.createElement('h3');
      h.textContent = label;
      summaryPanel.append(h);
      const div = document.createElement('div');
      div.className = 'word-list';
      if (list.length) {
        for (const word of list) {
          const span = document.createElement('span');
          span.textContent = word;
          div.append(span);
        }
      } else {
        div.textContent = 'None';
      }
      summaryPanel.append(div);
    }

    const ch = document.createElement('h3');
    ch.textContent = 'Corrections from this lesson';
    summaryPanel.append(ch);
    const corrections = data.corrections || [];
    if (!corrections.length) {
      const p = document.createElement('p');
      p.textContent = 'No corrections were made during this lesson.';
      summaryPanel.append(p);
    } else {
      for (const c of corrections) {
        const p = document.createElement('p');
        p.textContent = `You said: ${c.original}\n${c.explanation}\nTry: ${c.example}`;
        p.style.whiteSpace = 'pre-wrap';
        summaryPanel.append(p);
      }
    }

    if (attempt && Array.isArray(attempt.turns) && attempt.turns.length) {
      const th = document.createElement('h3');
      th.textContent = 'Conversation review';
      summaryPanel.append(th);
      const turnList = document.createElement('div');
      turnList.className = 'recap-turn-list';
      for (const t of attempt.turns) {
        const isIncorrect = Boolean(t.review_incorrect || t.flag_status === 'Incorrect');
        const row = document.createElement('div');
        row.className = 'recap-turn-item' + (isIncorrect ? ' reviewer-incorrect' : '');
        const header = document.createElement('div');
        header.className = 'recap-turn-header';
        const title = document.createElement('span');
        title.textContent = `Turn ${t.number}`;
        header.append(title);
        if (isIncorrect) {
          const badge = document.createElement('span');
          badge.className = 'incorrect-review-badge';
          badge.textContent = '✗ Marked Incorrect by Reviewer';
          header.append(badge);
        }
        row.append(header);
        const lLine = document.createElement('p');
        lLine.style.margin = '4px 0';
        const lStrong = document.createElement('strong');
        lStrong.textContent = 'You: ';
        lLine.append(lStrong, document.createTextNode(t.learner || ''));
        const aLine = document.createElement('p');
        aLine.style.margin = '4px 0';
        const aStrong = document.createElement('strong');
        aStrong.textContent = 'AI Partner: ';
        aLine.append(aStrong, document.createTextNode(t.reply || ''));
        row.append(lLine, aLine);
        turnList.append(row);
      }
      summaryPanel.append(turnList);
    }
    summaryPanel.hidden = false;
  }

  function createLessonCard(lesson, index) {
    const card = document.createElement('article');
    card.className = 'map-lesson-card';

    const topSection = document.createElement('div');

    const topBar = document.createElement('div');
    topBar.className = 'map-card-top';
    const step = document.createElement('span');
    step.className = 'map-step-badge';
    step.textContent = `Lesson ${index + 1}`;

    const badge = document.createElement('span');
    badge.className = 'map-status-badge ' + statusClass(lesson.status_on_map);
    badge.textContent = lesson.status_on_map || 'Not started';
    topBar.append(step, badge);
    topSection.append(topBar);

    const title = document.createElement('h3');
    title.className = 'map-card-title';
    title.textContent = lesson.scenario;
    topSection.append(title);

    const goal = document.createElement('p');
    goal.className = 'map-card-goal';
    goal.textContent = lesson.grammar_goal;
    topSection.append(goal);

    const meta = document.createElement('div');
    meta.className = 'lesson-meta';
    const tag1 = document.createElement('span');
    tag1.textContent = 'Beginner English';
    const tag2 = document.createElement('span');
    tag2.textContent = `${lesson.turn_limit} exchanges`;
    meta.append(tag1, tag2);
    topSection.append(meta);

    const wordsBox = document.createElement('div');
    wordsBox.className = 'word-list';
    if (Array.isArray(lesson.target_words) && lesson.target_words.length) {
      for (const w of lesson.target_words) {
        const span = document.createElement('span');
        span.textContent = w;
        wordsBox.append(span);
      }
    }
    topSection.append(wordsBox);
    card.append(topSection);

    const actions = document.createElement('div');
    actions.className = 'map-card-actions';

    const goBtn = document.createElement('button');
    goBtn.className = 'primary';
    goBtn.textContent = actionLabel(lesson.status_on_map);
    goBtn.onclick = () => {
      globalThis.location.href = `/?lesson_id=${lesson.id}`;
    };
    actions.append(goBtn);

    if (lesson.status_on_map === 'Completed') {
      const sumBtn = document.createElement('button');
      sumBtn.className = 'secondary';
      sumBtn.textContent = 'View last summary';
      sumBtn.onclick = async () => {
        showError();
        sumBtn.disabled = true;
        try {
          let attemptId = lesson.last_completed_attempt_id;
          if (!attemptId) {
            const detailRes = await fetch(`/api/lessons/${lesson.id}/`);
            const detailData = await detailRes.json();
            if (!detailRes.ok) throw new Error(detailData.error?.message || 'Could not load lesson details.');
            attemptId = detailData.lesson?.last_completed_attempt_id;
          }
          if (!attemptId) throw new Error('No completed summary found for this lesson.');
          const sumRes = await fetch(`/api/attempts/${attemptId}/summary/`);
          const sumData = await sumRes.json();
          if (!sumRes.ok) throw new Error(sumData.error?.message || 'Could not load summary.');
          renderSummary(lesson.scenario, sumData.summary, sumData.attempt);
        } catch (err) {
          showError(err.message);
        } finally {
          sumBtn.disabled = false;
        }
      };
      actions.append(sumBtn);
    }

    card.append(actions);

    // Enrich card with target_words & last_completed_attempt_id asynchronously if not preloaded
    if (!Array.isArray(lesson.target_words)) {
      fetch(`/api/lessons/${lesson.id}/`).then(r => r.ok ? r.json() : null).then(data => {
        if (data?.lesson) {
          lesson.last_completed_attempt_id = data.lesson.last_completed_attempt_id;
          wordsBox.replaceChildren();
          for (const w of data.lesson.target_words || []) {
            const span = document.createElement('span');
            span.textContent = w;
            wordsBox.append(span);
          }
        }
      }).catch(() => {});
    }

    return card;
  }

  function updateAccountUI(user) {
    if ($('account-name')) {
      $('account-name').textContent = user ? `Signed in as ${user.username}` : 'Sign in to practice';
    }
    if ($('sign-in-form')) $('sign-in-form').hidden = !!user;
    if ($('sign-out')) $('sign-out').hidden = !user;
    if ($('review-link-row')) $('review-link-row').hidden = !(user && user.role === 'Reviewer');
  }

  async function loadMap() {
    if (loading) return;
    loading = true;
    showError();
    if (summaryPanel) { summaryPanel.hidden = true; summaryPanel.replaceChildren(); }
    if (retryBtn) { retryBtn.disabled = true; retryBtn.hidden = true; }
    if (refreshBtn) refreshBtn.disabled = true;
    if (statusEl) { statusEl.textContent = 'Loading learning map…'; statusEl.hidden = false; }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch('/api/lessons/', {signal: controller.signal});
      if (response.status === 401 || response.status === 403) {
        grid.replaceChildren();
        grid.hidden = true;
        if ($('map-lessons-header')) $('map-lessons-header').hidden = true;
        if (overview) overview.hidden = true;
        if (summaryPanel) summaryPanel.hidden = true;
        statusEl.textContent = response.status === 401
          ? 'Sign in above to choose a lesson.'
          : 'Sign in with a learner account to choose a lesson.';
        statusEl.hidden = false;
        return;
      }
      if (!response.ok) throw new Error('Lessons could not be loaded.');
      const data = await response.json();
      if (!Array.isArray(data.lessons)) throw new Error('Invalid lesson list.');

      grid.replaceChildren();
      grid.hidden = false;
      if ($('map-lessons-header')) $('map-lessons-header').hidden = false;
      updateStats(data.lessons);

      if (!data.lessons.length) {
        statusEl.textContent = 'No lessons are available yet.';
        statusEl.hidden = false;
        return;
      }

      for (let i = 0; i < data.lessons.length; i++) {
        grid.append(createLessonCard(data.lessons[i], i));
      }
      statusEl.textContent = `${data.lessons.length} scenario(s) available.`;
      statusEl.hidden = false;
    } catch {
      grid.replaceChildren();
      if (overview) overview.hidden = true;
      statusEl.textContent = 'Lessons could not be loaded. Please check your connection and try again.';
      statusEl.hidden = false;
      if (retryBtn) retryBtn.hidden = false;
    } finally {
      clearTimeout(timer);
      loading = false;
      if (retryBtn) retryBtn.disabled = false;
      if (refreshBtn) refreshBtn.disabled = false;
    }
  }

  if ($('sign-in-form')) {
    $('sign-in-form').onsubmit = async event => {
      event.preventDefault();
      showError();
      try {
        const response = await fetch('/api/auth/login/', {
          method: 'POST',
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf()},
          body: JSON.stringify({username: $('username').value, password: $('password').value})
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error?.message || 'Sign in failed.');
        $('password').value = '';
        if (result.user?.role === 'Reviewer') {
          globalThis.location.href = '/review/';
          return;
        }
        updateAccountUI(result.user);
        await loadMap();
      } catch (err) {
        showError(err.message);
      }
    };
  }

  if ($('sign-out')) {
    $('sign-out').onclick = async () => {
      showError();
      try {
        const response = await fetch('/api/auth/logout/', {
          method: 'POST',
          headers: {'X-CSRFToken': csrf()}
        });
        if (!response.ok) throw new Error('Sign out failed.');
        updateAccountUI(null);
        grid.replaceChildren();
        grid.hidden = true;
        if ($('map-lessons-header')) $('map-lessons-header').hidden = true;
        if (overview) overview.hidden = true;
        if (summaryPanel) { summaryPanel.hidden = true; summaryPanel.replaceChildren(); }
        if (statusEl) {
          statusEl.textContent = 'Sign in above to choose a lesson.';
          statusEl.hidden = false;
        }
      } catch (err) {
        showError(err.message);
      }
    };
  }

  if (retryBtn) retryBtn.onclick = () => loadMap();
  if (refreshBtn) refreshBtn.onclick = () => loadMap();

  void loadMap();
})();
