'use strict';
globalThis.SpeakoProtocol = {
  attempt(value) {
    if (!value) return null;
    return {...value, id:value.attempt_id, status:value.status.toLowerCase().replaceAll(' ', '_'),
      pending_id:value.pending?.id || '', pending:value.pending?.text || ''};
  },
  error(value) {
    return typeof value === 'string' ? value : value?.message || 'This step failed. Retry.';
  },
  confirmation(session) {
    return {attempt_id:session.id, pending_id:session.pending_id};
  }
};
