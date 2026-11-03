'use strict';
globalThis.SpeakoSpeech = {
  slowRate: 0.75,
  canRepeat(lastReply, busy, speaking, recording) {
    return Boolean(lastReply) && !busy && !speaking && !recording;
  },
  repeatSlower(text, synth, play) {
    if (!text) return false;
    if (synth?.speaking) synth.cancel();
    play(text, globalThis.SpeakoSpeech.slowRate);
    return true;
  },
};