const fs=require('fs'),path=require('path');
const {spawn}=require('child_process');
const {once}=require('events');
const runtime=process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
const {createCanvas,loadImage}=require(runtime?require.resolve('@napi-rs/canvas',{paths:[runtime]}):'@napi-rs/canvas');
const A=require('./animation.js');
const ROOT=path.resolve(__dirname,'..');
const OUT=process.env.VELVET_WHEEL_OUTPUT_DIR?path.resolve(process.env.VELVET_WHEEL_OUTPUT_DIR):path.resolve(ROOT,'../sector_deliverables');
const NAMES={background:'01_background',frame:'02_fixed_frame',pointer:'03_pointer',hub:'04_ruby_hub',disk:'05_rotating_disk',candles:'06_candles',petal:'07_petal',button:'08_button'};
const ALL=Object.keys(A.OUTCOMES),NEW=ALL.filter(name=>name!=='Royal');
async function loadAssets(){
  const assets={};for(const[key,file]of Object.entries(NAMES))assets[key]=await loadImage(path.join(ROOT,'layers',file+'.png'));
  return assets;
}
function buildHTML(){
  const encoded={};for(const[key,file]of Object.entries(NAMES))encoded[key]='data:image/png;base64,'+fs.readFileSync(path.join(ROOT,'layers',file+'.png')).toString('base64');
  const engine=fs.readFileSync(path.join(__dirname,'animation.js'),'utf8');
  const viewer=fs.readFileSync(path.join(__dirname,'viewer.js'),'utf8');
  const template=fs.readFileSync(path.join(__dirname,'viewer.html'),'utf8');
  fs.writeFileSync(path.join(OUT,'Velvet_all_outcomes.html'),template.replace('__ENGINE__',()=>engine).replace('__ASSETS__',()=>JSON.stringify(encoded)).replace('__VIEWER__',()=>viewer));
}
function buildStills(assets){
  const canvas=createCanvas(A.W,A.H),ctx=canvas.getContext('2d');
  for(const name of ALL){
    const state=A.render(ctx,assets,9,{outcome:name,motionBlur:false});
    fs.writeFileSync(path.join(ROOT,'checks',name+'_result.png'),canvas.toBuffer('image/png'));
    console.log(name+': final rotation '+Math.round(state.angle*180/Math.PI)+'°, result '+state.outcome);
  }
  const overview=createCanvas(3*360,2*480+84),o=overview.getContext('2d');o.fillStyle='#090507';o.fillRect(0,0,overview.width,overview.height);
  ALL.forEach((name,i)=>{const col=i%3,row=Math.floor(i/3),x=col*360,y=row*522;o.fillStyle=A.OUTCOMES[name].accent;o.font='24px Georgia';o.textAlign='center';o.fillText(name,x+180,y+31);A.render(ctx,assets,9,{outcome:name,motionBlur:false});o.drawImage(canvas,x,y+42,360,480)});
  fs.writeFileSync(path.join(ROOT,'checks','All_outcomes_result.png'),overview.toBuffer('image/png'));
}
async function renderVideo(assets,outcome){
  A.outcomeConfig(outcome);
  const width=720,height=960,fps=30,frames=Math.round(A.DURATION*fps);
  const file=path.join(OUT,outcome+'.mp4');
  const encoder=spawn('ffmpeg',['-y','-hide_banner','-loglevel','error','-f','rawvideo','-pixel_format','rgba','-video_size',`${width}x${height}`,'-framerate',String(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',file],{stdio:['pipe','inherit','inherit']});
  const done=new Promise((resolve,reject)=>{encoder.once('error',reject);encoder.once('exit',code=>code===0?resolve():reject(new Error('ffmpeg failed: '+code)))});
  encoder.stdin.on('error',()=>{});
  const canvas=createCanvas(width,height),ctx=canvas.getContext('2d');
  for(let i=0;i<frames;i++){
    A.render(ctx,assets,i/fps,{width,height,outcome});
    const raw=ctx.getImageData(0,0,width,height).data;
    if(!encoder.stdin.write(Buffer.from(raw.buffer,raw.byteOffset,raw.byteLength)))await once(encoder.stdin,'drain');
    if(i%90===0)console.log(outcome+': '+i+'/'+frames);
  }
  encoder.stdin.end();await done;console.log(outcome+': MP4 ready');
}
async function main(){
  fs.mkdirSync(OUT,{recursive:true});fs.mkdirSync(path.join(ROOT,'checks'),{recursive:true});
  const preservedRoyal=path.join(ROOT,'videos','Royal.mp4');
  if(fs.existsSync(preservedRoyal)&&!fs.existsSync(path.join(OUT,'Royal.mp4')))fs.copyFileSync(preservedRoyal,path.join(OUT,'Royal.mp4'));
  const assets=await loadAssets();buildHTML();buildStills(assets);
  if(process.argv.includes('--stills'))return;
  const at=process.argv.indexOf('--outcome');
  const outcomes=at>=0?[process.argv[at+1]]:NEW;
  for(const outcome of outcomes)await renderVideo(assets,outcome);
}
if(require.main===module)main().catch(e=>{console.error(e);process.exit(1)});
module.exports={ROOT,OUT,ALL,NEW,NAMES,loadAssets,buildHTML,buildStills,renderVideo};
