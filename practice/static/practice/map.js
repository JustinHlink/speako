'use strict';
globalThis.SpeakoMap = {
  async load(onSelect) {
    const host = document.getElementById('lesson-list');
    const notice = document.getElementById('map-status');
    const retry = document.getElementById('map-retry');
    retry.onclick = () => this.load(onSelect);
    retry.disabled = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch('/api/lessons/', {signal: controller.signal});
      if (response.status === 401 || response.status === 403) {
        host.replaceChildren();
        notice.textContent = response.status === 401
          ? 'Sign in above to choose a lesson.'
          : 'Sign in with a learner account to choose a lesson.';
        notice.hidden = false;
        retry.hidden = true;
        return;
      }
      if (!response.ok) throw new Error('Lessons could not be loaded.');
      const {lessons} = await response.json();
      if (!Array.isArray(lessons)) throw new Error('Invalid lesson list.');
      host.replaceChildren();
      for (const lesson of lessons) {
        const button = document.createElement('button');
        button.className = 'secondary lesson-option';
        button.textContent = lesson.scenario + ' · ' + lesson.status_on_map;
        button.onclick = async () => {
          button.disabled = true;
          try {
            const detail = await fetch('/api/lessons/' + lesson.id + '/');
            const data = await detail.json();
            if (!detail.ok) throw new Error(SpeakoProtocol.error(data.error));
            await onSelect({...data.lesson, status_on_map:lesson.status_on_map});
          } catch (error) {
            const banner = document.getElementById('error');
            banner.textContent = error.message;
            banner.hidden = false;
          } finally { button.disabled = false; }
        };
        host.append(button);
      }
      if (!lessons.length) host.textContent = 'No lessons are available yet.';
      notice.hidden = true;
      retry.hidden = true;
    } catch {
      notice.textContent = 'Lessons could not be loaded. You can still continue your current lesson.';
      notice.hidden = false;
      retry.hidden = false;
    } finally {
      clearTimeout(timeout);
      retry.disabled = false;
    }
  }
};
