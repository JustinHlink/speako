const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');
function element(){return {children:[],disabled:false,textContent:'',append(...items){this.children.push(...items);},setAttribute(){}};}
const context=vm.createContext({document:{createElement:element}});
vm.runInContext(fs.readFileSync(__dirname+'/static/practice/flags.js','utf8'),context);
function mount(turn,submit){const host=element();context.SpeakoFlags.attach(host,turn,submit);return {host,button:host.children[1],notice:host.children[2]};}
(async()=>{
 let calls=0,release;const turn={id:12,flagged:false};
 const page=mount(turn,async(url,data)=>{calls++;assert.equal(url,'/api/flag/submit/');assert.equal(data.turn_id,12);await new Promise(r=>release=r);});
 const pending=page.button.onclick();assert.equal(page.button.disabled,true);await page.button.onclick();assert.equal(calls,1);release();await pending;
 assert.equal(page.button.disabled,true);assert.equal(turn.flagged,true);assert.match(page.notice.textContent,/progress is unchanged/);
 const restored=mount(turn,()=>{throw Error('must not submit');});assert.equal(restored.button.disabled,true);await restored.button.onclick();
 let attempts=0;const retry=mount({id:13},async()=>{if(++attempts===1)throw Error('Network down');});await retry.button.onclick();assert.equal(retry.button.disabled,false);assert.match(retry.notice.textContent,/retry/);await retry.button.onclick();assert.equal(retry.button.disabled,true);
 const duplicate=mount({id:14},async()=>{throw Object.assign(Error('Duplicate'),{code:'CONFLICT'});});await duplicate.button.onclick();assert.equal(duplicate.button.disabled,true);assert.match(duplicate.notice.textContent,/already/);
 assert.equal(mount({},()=>{}).host.children.length,0);
 console.log('Flag page: success, repeat clicks, reload, network retry, conflict and missing ID passed.');
})().catch(error=>{console.error(error);process.exit(1);});
