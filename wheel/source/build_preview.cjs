const path=require('path');
const {spawnSync,execFileSync}=require('child_process');
const {OUT,ALL}=require('./render.cjs');
const A=require('./animation.js');
const args=['-y','-hide_banner','-loglevel','error'];
for(const name of ALL)args.push('-i',path.join(OUT,name+'.mp4'));
let font="font='Liberation Serif'";
try{const file=execFileSync('fc-match',['-f','%{file}','Liberation Serif'],{encoding:'utf8'}).trim();if(file)font="fontfile='"+file.replace(/'/g,"\\'")+"'"}catch{}
const filters=ALL.map((name,i)=>`[${i}:v]scale=240:320,pad=240:352:0:32:color=0x080406,drawtext=${font}:text='${name}':fontsize=21:fontcolor=0x${A.OUTCOMES[name].accent.slice(1)}:x=(w-tw)/2:y=4[v${i}]`);
filters.push(ALL.map((_,i)=>`[v${i}]`).join('')+'xstack=inputs=6:layout=0_0|240_0|480_0|0_352|240_352|480_352:shortest=1[out]');
args.push('-filter_complex',filters.join(';'),'-filter_complex_threads','2','-map','[out]','-an','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',path.join(OUT,'All_outcomes_preview.mp4'));
const result=spawnSync('ffmpeg',args,{stdio:'inherit'});
if(result.error)throw result.error;
if(result.status)process.exit(result.status);
console.log('Six-outcome video preview ready.');
