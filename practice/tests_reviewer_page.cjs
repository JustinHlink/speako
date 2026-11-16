const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');
function element(){return {children:[],textContent:'',className:'',hidden:false,disabled:false,style:{},append(...items){for(const item of items){item.parent=this;this.children.push(item);}},replaceChildren(...items){this.children=[];this.append(...items);},remove(){this.parent.children=this.parent.children.filter(x=>x!==this);},querySelectorAll(){let result=[];for(const child of this.children){if(child.tag==='button')result.push(child);result.push(...(child.querySelectorAll?.() || []));}return result;}};}
const flag={id:1,turn_id:2,attempt_id:'attempt-1',scenario:'Restaurant',turn_number:2,grammar_goal:'Requests',target_words:['water'],opening:'Hello',history:[{learner_text:'Earlier',ai_reply:'Welcome'}],turns:[{id:1,turn_number:1,learner_text:'Earlier',ai_reply:'Welcome',is_flagged:false},{id:2,turn_number:2,learner_text:'<script>unsafe</script>',ai_reply:'Water?',is_flagged:true,correction:{explanation:'Use like',example:'I like water'}}],learner_text:'<script>unsafe</script>',ai_reply:'Water?',flagged_at:'2026-11-13T00:00:00Z',correction:{explanation:'Use like',example:'I like water'}};
async function page(){const nodes={};let queue=[flag],failLoad=false,decisionStatus=200,writes=0;const location={};const events={};const context=vm.createContext({addEventListener:(name,fn)=>events[name]=fn,console,AbortController,setTimeout:()=>0,clearTimeout(){},location,document:{cookie:'csrftoken=token',getElementById:id=>nodes[id]??=element(),createElement:tag=>Object.assign(element(),{tag}),createTextNode:text=>({text})},fetch:async(url,options)=>{
 if(url==='/api/flag/list/'){if(failLoad)throw Error('Network down');return {ok:true,json:async()=>({flags:queue})};}
 if(url==='/api/flag/review/'){writes++;assert.equal(options.headers['X-CSRFToken'],'token');if(decisionStatus===200){queue=[];return {ok:true,json:async()=>({})};}if(decisionStatus===409)queue=[];return {ok:false,status:decisionStatus,json:async()=>({error:{code:'CONFLICT',message:'Failed'}})};}
 return {ok:true};}});
 vm.runInContext(fs.readFileSync(__dirname+'/static/practice/reviewer.js','utf8'),context);await new Promise(setImmediate);
 return {nodes,location,events,get writes(){return writes},failLoad(){failLoad=true},decision(status){decisionStatus=status},queue(value){queue=value}};}
(async()=>{
 const p=await page();assert.equal(p.nodes['review-queue'].children.length,1);
 const card=p.nodes['review-queue'].children[0];
 assert.equal(card.querySelectorAll().length,0);
 const texts=node=>[node.textContent || node.text || '',...(node.children || []).flatMap(texts)];
 assert.ok(texts(card).includes('<script>unsafe</script>'));
 assert.equal(card.innerHTML,undefined);
 const allNodes=node=>[node,...(node.children || []).flatMap(allNodes)];
 const textBlocks=allNodes(card).filter(n=>String(n.className).includes('review-text-content'));
 assert.equal(textBlocks.length,2);
 assert.ok(!textBlocks[0].className.includes('fade-text'));
 assert.ok(!textBlocks[1].className.includes('fade-text'));

 card.onclick();
 const detail=p.nodes['review-queue'].children[0];
 assert.ok(texts(detail).includes('Earlier'));
 assert.ok(texts(detail).includes('Use like'));
 assert.ok(texts(detail).includes('<script>unsafe</script>'));
 const allDivs=node=>[node,...(node.children || []).flatMap(allDivs)];
 assert.ok(allDivs(detail).some(n=>String(n.className).includes('flagged-turn')));
 const buttons=detail.querySelectorAll();
 assert.equal(buttons.length,3); // [Back, Mark acceptable, Mark incorrect]

 await buttons[2].onclick();
 assert.equal(p.writes,1);assert.equal(p.nodes['review-queue'].children.length,0);assert.match(p.nodes['review-status'].textContent,/Decision saved: Incorrect/);

 const q=await page();q.decision(500);q.nodes['review-queue'].children[0].onclick();await q.nodes['review-queue'].children[0].querySelectorAll()[1].onclick();assert.equal(q.nodes['review-queue'].children.length,1);assert.equal(q.nodes['review-queue'].children[0].querySelectorAll()[1].disabled,false);assert.match(q.nodes['review-error'].textContent,/Failed/);
 q.failLoad();await q.nodes['review-refresh'].onclick();assert.equal(q.nodes['review-queue'].children.length,0);assert.match(q.nodes['review-error'].textContent,/Network/);

 const conflict=await page();conflict.decision(409);conflict.nodes['review-queue'].children[0].onclick();await conflict.nodes['review-queue'].children[0].querySelectorAll()[1].onclick();assert.equal(conflict.nodes['review-queue'].children.length,0);assert.match(conflict.nodes['review-error'].textContent,/already/);

 const forbidden=await page();forbidden.decision(403);forbidden.nodes['review-queue'].children[0].onclick();await forbidden.nodes['review-queue'].children[0].querySelectorAll()[1].onclick();assert.equal(forbidden.nodes['review-queue'].children.length,0);assert.match(forbidden.nodes['review-error'].textContent,/reviewer account/);forbidden.events.popstate();assert.equal(forbidden.nodes['review-queue'].children.length,0,'History navigation cannot restore unauthorized cached records');

 const empty=await page();empty.queue([]);await empty.nodes['review-refresh'].onclick();assert.match(empty.nodes['review-status'].textContent,/No text awaiting review/);
 console.log('Reviewer page: interactive card, attempt conversation scroll, flagged highlight, save, empty queue, failed save/retry, network refresh, concurrent review and permission loss passed.');
})().catch(error=>{console.error(error);process.exit(1)});
