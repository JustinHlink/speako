const assert = require('node:assert/strict');
require('./static/practice/protocol.js');
const protocol = globalThis.SpeakoProtocol;
assert.equal(protocol.attempt(null), null);
const attempt = protocol.attempt({
  attempt_id:'attempt-a', status:'In progress', turn_limit:7, turns:[],
  pending:{id:'transcript-b', text:'I would likes tea.'}
});
assert.equal(attempt.status, 'in_progress');
assert.equal(attempt.pending, 'I would likes tea.');
assert.equal(attempt.turn_limit, 7);
assert.deepEqual(protocol.confirmation(attempt),
  {attempt_id:'attempt-a', pending_id:'transcript-b'});
assert.equal(protocol.attempt({attempt_id:'a', status:'Completed', pending:null}).pending, '');
assert.equal(protocol.error({code:'STALE',message:'Record again.'}), 'Record again.');
assert.equal(protocol.error('Unavailable'), 'Unavailable');
console.log('Browser protocol checks passed.');
