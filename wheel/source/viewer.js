const wheel=document.getElementById('wheel'),ctx=wheel.getContext('2d');
const hint=document.getElementById('hint'),selector=document.getElementById('outcome');
const assets={};let running=false,token=0,ready=false;
Promise.all(Object.entries(encoded).map(([key,url])=>new Promise((ok,no)=>{
  const im=new Image();im.onload=()=>{assets[key]=im;ok()};im.onerror=no;im.src=url;
}))).then(()=>{
  ready=true;VelvetWheel.render(ctx,assets,0,{outcome:selector.value,motionBlur:false});
  window.prototypeReady=true;
}).catch(()=>{hint.textContent='Не удалось загрузить слои';selector.disabled=true});
function resultHint(outcome){return outcome+' · Нажми на кнопку, чтобы повторить'}
function spin(){
  if(!ready||running)return;
  const outcome=VelvetWheel.outcomeConfig(selector.value).name;
  running=true;selector.disabled=true;hint.textContent='Колесо вращается…';
  const start=performance.now(),id=++token;
  function tick(now){
    if(id!==token)return;
    const t=(now-start)/1000;
    VelvetWheel.render(ctx,assets,t,{outcome});
    if(t<VelvetWheel.DURATION)requestAnimationFrame(tick);
    else{running=false;selector.disabled=false;hint.textContent=resultHint(outcome)}
  }
  requestAnimationFrame(tick);
}
wheel.addEventListener('click',e=>{
  const r=wheel.getBoundingClientRect(),x=(e.clientX-r.left)*1086/r.width,y=(e.clientY-r.top)*1448/r.height;
  if(x>235&&x<850&&y>1140&&y<1390)spin();
});
wheel.addEventListener('keydown',e=>{
  if(e.key==='Enter'||e.key===' '){e.preventDefault();spin()}
});
selector.addEventListener('change',()=>{
  if(!ready||running)return;
  const outcome=VelvetWheel.outcomeConfig(selector.value).name;
  ++token;hint.textContent='Выбран '+outcome+' · Нажми «Крутить»';
  VelvetWheel.render(ctx,assets,0,{outcome,motionBlur:false});
});
// An optional deterministic preview hook; no draw, currency or Telegram calls.
window.renderOutcomeAt=(outcome,t)=>{
  VelvetWheel.outcomeConfig(outcome);++token;running=false;selector.disabled=false;selector.value=outcome;
  const state=VelvetWheel.render(ctx,assets,t,{outcome,motionBlur:false});
  hint.textContent=state.outcome?resultHint(state.outcome):'Выбран '+outcome+' · Нажми «Крутить»';
  return state;
};
