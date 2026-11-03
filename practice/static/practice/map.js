'use strict';
globalThis.SpeakoMap = {
  async load(onSelect) {
    const host = document.getElementById('lesson-list');
    host.replaceChildren();
    const response = await fetch('/api/lessons/');
    if (!response.ok) return;
    const {lessons} = await response.json();
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
  }
};
