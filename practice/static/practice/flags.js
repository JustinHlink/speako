'use strict';
globalThis.SpeakoFlags = {
  attach(host, turn, submit) {
    if (!Number.isSafeInteger(turn.id) || turn.id <= 0) return;
    const button = document.createElement('button');
    button.className = 'text-button';
    button.textContent = turn.flagged ? 'Flag submitted' : 'Flag this reply';
    button.disabled = !!turn.flagged;
    const notice = document.createElement('span');
    notice.className = 'quiet';
    notice.setAttribute('role', 'status');
    button.onclick = async () => {
      if (button.disabled || turn.flagged) return;
      button.disabled = true;
      notice.textContent = 'Submitting…';
      try {
        await submit('/api/flag/submit/', {turn_id: turn.id});
        turn.flagged = true;
        notice.textContent = 'Sent for review. Your lesson progress is unchanged.';
      } catch (error) {
        if (error.code === 'CONFLICT') {
          turn.flagged = true;
          notice.textContent = 'This reply has already been flagged.';
        } else {
          notice.textContent = 'Flag could not be submitted. ' + error.message + ' You can retry.';
        }
      } finally {
        button.disabled = !!turn.flagged;
        button.textContent = turn.flagged ? 'Flag submitted' : 'Flag this reply';
      }
    };
    host.append(document.createElement('br'), button, notice);
  }
};
