// Run the actual standalone HTML scripts with real Canvas and a small event host.
// This is script/render integration evidence, not browser compatibility evidence.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const runtime=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
const {createCanvas,Image}=require(runtime?require.resolve('@napi-rs/canvas',{paths:[runtime]}):'@napi-rs/canvas');
const ROOT=path.resolve(__dirname,'..');
const output=process.env.VELVET_WHEEL_OUTPUT_DIR?path.resolve(process.env.VELVET_WHEEL_OUTPUT_DIR):path.resolve(ROOT,'../sector_deliverables');
const html=fs.readFileSync(path.join(output,'Velvet_all_outcomes.html'),'utf8');
const scripts=Array.from(html.matchAll(/<script>([\s\S]*?)<\/script>/g),m=>m[1]);
const wheel=createCanvas(1086,1448),ctx=wheel.getContext('2d');
const hint={textContent:''},listeners={},selectListeners={};
const selector={value:'Royal',disabled:false,addEventListener:(name,fn)=>selectListeners[name]=fn};
wheel.addEventListener=(name,fn)=>listeners[name]=fn;
wheel.getBoundingClientRect=()=>({left:0,top:0,width:543,height:724});
let now=0,queue=[],drawn=[];
const originalFillText=ctx.fillText.bind(ctx);
ctx.fillText=(text,...args)=>{drawn.push(text);return originalFillText(text,...args)};
class CanvasImage extends Image{set src(value){super.src=Buffer.from(value.split(',')[1],'base64')}}
const sandbox={console,Image:CanvasImage,performance:{now:()=>now},requestAnimationFrame:fn=>{queue.push(fn);return queue.length},document:{getElementById:id=>({wheel,hint,outcome:selector})[id]}};
sandbox.window=sandbox;const context=vm.createContext(sandbox);
const frame=t=>{now=t;const pending=queue;queue=[];for(const fn of pending)fn(now)};
const click=()=>listeners.click({clientX:271.5,clientY:624});
// Source centers measured in the supplied master: clockwise, 0° = right.
const sourceAngles={Classic:240,Elite:300,Royal:0,Epic:60,Mythic:120,Eternal:180};
const core=()=>Buffer.from(ctx.getImageData(536,673,14,14).data);
const pointer=()=>Buffer.from(ctx.getImageData(538,229,10,10).data);
// Housing alpha is 253/255 in these gem patches. Its residual compositing can
// change channels by at most two levels as the source sector changes underneath.
// A displaced ruby/facet would exceed this bound substantially.
function fixedPatch(actual,reference,message){
  let max=0;for(let i=0;i<actual.length;i++)max=Math.max(max,Math.abs(actual[i]-reference[i]));
  assert(max<=2,message+' (maximum channel change '+max+')');return max;
}
async function main(){
  for(const code of scripts)vm.runInContext(code,context);
  const deadline=Date.now()+5000;while(!sandbox.prototypeReady&&Date.now()<deadline)await new Promise(ok=>setTimeout(ok,10));
  assert(sandbox.prototypeReady,'All embedded layer images must load');
  const records=[];let hubReference,pointerReference;
  for(const [name,sourceAngle]of Object.entries(sourceAngles)){
    selector.value=name;selectListeners.change();drawn=[];
    const start=now;click();assert(selector.disabled);assert.equal(queue.length,1);
    click();assert.equal(queue.length,1,'Double click must not fork animation');
    frame(start+1900);assert.equal(hint.textContent,'Колесо вращается…');
    frame(start+10450);assert(hint.textContent.startsWith(name+' ·'));assert(!selector.disabled);
    assert(drawn.includes('Твой исход — '+name),'Header must use the selected outcome');
    assert(drawn.includes(name),'Button must use the selected outcome');
    const state=sandbox.renderOutcomeAt(name,9);
    const endRadians=sourceAngle*Math.PI/180+state.angle;
    assert(Math.abs(Math.cos(endRadians))<1e-9&&Math.sin(endRadians)<-.999999,'Selected sector center must land at the top pointer');
    const h=core(),p=pointer();
    if(hubReference){fixedPatch(h,hubReference,'Ruby core must stay fixed across outcomes');fixedPatch(p,pointerReference,'Pointer ruby must stay fixed across outcomes')}
    else{hubReference=h;pointerReference=p}
    const still=sandbox.renderOutcomeAt(name,10.4);assert.equal(state.angle,still.angle,'Result must hold after the stop');
    click();assert.equal(queue.length,1);frame(now+10450);assert(hint.textContent.startsWith(name+' ·'));
    records.push({outcome:name,rotationDegrees:Math.round(state.angle*180/Math.PI),topSector:name,headerAndButton:'PASS',start:'PASS',replay:'PASS',fixedRubyAndPointer:'PASS'});
  }
  for(const key of ['Enter',' ']){
    let prevented=false;listeners.keydown({key,preventDefault:()=>prevented=true});assert(prevented);assert.equal(queue.length,1);frame(now+10450);
  }
  assert.throws(()=>sandbox.renderOutcomeAt('Invalid',0),/Unknown wheel outcome/);
  const result={scriptIntegration:'PASS',outcomes:records,inlineAssets:'PASS',doubleClickGuard:'PASS',keyboard:'PASS',invalidOutcomeRejected:'PASS',browserCompatibility:'NOT_VERIFIED: previous local Chromium and cloud file URL restrictions remain',tools:['Canvas','FFmpeg','Node.js']};
  fs.writeFileSync(path.join(__dirname,'script_verification.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
}
main().catch(e=>{console.error(e);process.exit(1)});
