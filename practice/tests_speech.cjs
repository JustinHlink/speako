const assert = require('node:assert/strict');
require('./static/practice/speech.js');
const speech = globalThis.SpeakoSpeech;

let fetchCalls = 0;
globalThis.fetch = () => { fetchCalls += 1; };
const played = [];
const play = (text, rate) => played.push({text, rate});
const fakeSynth = speaking => ({speaking, cancelled: 0, cancel() { this.cancelled += 1; }});
const line = 'Would you like tea?';

assert.equal(speech.canRepeat('', false, false, false), false);
assert.equal(speech.canRepeat(line, false, false, false), true);
assert.equal(speech.canRepeat(line, true, false, false), false);
assert.equal(speech.canRepeat(line, false, true, false), false);
assert.equal(speech.canRepeat(line, false, false, true), false);

assert.equal(speech.repeatSlower('', fakeSynth(false), play), false);
assert.equal(played.length, 0);

const busySynth = fakeSynth(true);
assert.equal(speech.repeatSlower(line, busySynth, play), true);
assert.equal(busySynth.cancelled, 1);
assert.deepEqual(played[0], {text: line, rate: 0.75});
assert.ok(speech.slowRate < 1);

const quietSynth = fakeSynth(false);
speech.repeatSlower(line, quietSynth, play);
assert.equal(quietSynth.cancelled, 0);

speech.repeatSlower(line, undefined, play);
assert.equal(played.length, 3);
assert.equal(fetchCalls, 0);

console.log('Repeat slower checks passed.');