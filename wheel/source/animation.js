(function(scope){
  'use strict';
  const W=1086,H=1448,CX=543,CY=680,R=432;
  const START=.65,ACCEL=.55,SPIN=7,END=START+SPIN,DURATION=10.4;
  const DEG=Math.PI/180;
  const OUTCOMES=Object.freeze({
    Classic:Object.freeze({name:'Classic',centerDegrees:240,accent:'#dcc5ff',glow:'202,166,255',edge:'235,218,255',shadow:'#ad79f0'}),
    Elite:Object.freeze({name:'Elite',centerDegrees:300,accent:'#ffafbd',glow:'255,57,96',edge:'255,178,195',shadow:'#ff416d'}),
    Royal:Object.freeze({name:'Royal',centerDegrees:0,accent:'#ffe0a0',glow:'255,171,44',edge:'255,216,138',shadow:'#ffa333'}),
    Epic:Object.freeze({name:'Epic',centerDegrees:60,accent:'#ffc187',glow:'255,86,21',edge:'255,183,111',shadow:'#ff641c'}),
    Mythic:Object.freeze({name:'Mythic',centerDegrees:120,accent:'#ebaeff',glow:'187,64,255',edge:'232,175,255',shadow:'#bd45ff'}),
    Eternal:Object.freeze({name:'Eternal',centerDegrees:180,accent:'#a3f2ff',glow:'42,218,255',edge:'167,244,255',shadow:'#29dfff'})
  });
  function outcomeConfig(name='Royal'){
    const result=Object.hasOwn(OUTCOMES,name)?OUTCOMES[name]:null;
    if(!result)throw new RangeError('Unknown wheel outcome: '+name);
    return result;
  }
  function targetFor(name='Royal'){
    const c=outcomeConfig(name);
    return (1800+(270-c.centerDegrees+360)%360)*DEG;
  }
  const TARGET=targetFor('Royal');
  const speedFor=name=>targetFor(name)/(2*ACCEL/Math.PI+(SPIN-ACCEL)/4);
  const TAU=Math.PI*2;
  const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
  const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
  function angle(t,outcome='Royal'){
    const TARGET=targetFor(outcome),SPEED=speedFor(outcome);
    const s=t-START;
    if(s<=0)return 0;
    if(s>=SPIN)return TARGET;
    if(s<ACCEL)return SPEED*2*ACCEL/Math.PI*(1-Math.cos(Math.PI*s/(2*ACCEL)));
    const q=(s-ACCEL)/(SPIN-ACCEL);
    return SPEED*(2*ACCEL/Math.PI+(SPIN-ACCEL)/4*(1-Math.pow(1-q,4)));
  }
  function velocity(t,outcome='Royal'){
    const SPEED=speedFor(outcome);
    const s=t-START;
    if(s<=0||s>=SPIN)return 0;
    return s<ACCEL?SPEED*Math.sin(Math.PI*s/(2*ACCEL)):SPEED*Math.pow(1-(s-ACCEL)/(SPIN-ACCEL),3);
  }
  const petals=Array.from({length:15},(_,i)=>({
    x:55+((i*137.17)%976),y:(i*191.37)%1600-120,
    speed:34+(i*7.3)%42,size:18+(i*5.7)%22,phase:i*2.399,depth:i%3
  }));
  function glow(ctx,x,y,r,color,strength=1){
    ctx.save();ctx.globalAlpha=strength;
    const g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,color);g.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2);ctx.restore();
  }
  function drawFlame(ctx,x,y,t,index){
    const flicker=1+.10*Math.sin(t*10.3+index*2)+.05*Math.sin(t*17.7+index);
    const sway=Math.sin(t*7.2+index)*3;
    glow(ctx,x,y-20,70,'rgba(255,133,26,.29)',flicker);
    ctx.save();ctx.translate(x,y);ctx.scale(1,flicker);ctx.shadowColor='rgba(255,169,45,.6)';ctx.shadowBlur=9;
    ctx.beginPath();ctx.moveTo(0,1);ctx.bezierCurveTo(-15,-13,-8,-30,sway,-55);ctx.bezierCurveTo(4+sway,-34,15,-14,0,1);
    const g=ctx.createLinearGradient(0,-55,0,0);g.addColorStop(0,'#ff9a3b');g.addColorStop(.48,'#ffe78f');g.addColorStop(.83,'#fff9d0');g.addColorStop(1,'#ffc44f');ctx.fillStyle=g;ctx.fill();
    ctx.beginPath();ctx.moveTo(0,0);ctx.bezierCurveTo(-6,-9,-3,-24,sway*.3,-31);ctx.bezierCurveTo(4,-19,7,-7,0,0);ctx.fillStyle='#fffde7';ctx.fill();
    ctx.strokeStyle='#4e2218';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(0,2);ctx.lineTo(0,9);ctx.stroke();ctx.restore();
  }
  function drawPetals(ctx,img,t,front){
    for(let i=0;i<petals.length;i++){
      const p=petals[i];if((p.depth>0)!==front)continue;
      const yy=((p.y+t*p.speed+1600)%1600)-100;
      const xx=p.x+Math.sin(t*.55+p.phase)*35;
      ctx.save();ctx.translate(xx,yy);ctx.rotate(p.phase+t*(.31+i*.017));
      ctx.scale(.55+Math.abs(Math.sin(p.phase+t*.8))*.45,1);
      ctx.globalAlpha=front?.78:.4;ctx.drawImage(img,-p.size/2,-p.size/2,p.size,p.size*1.1);ctx.restore();
    }
  }
  function drawRotor(ctx,disk,a,alpha=1){
    ctx.save();ctx.globalAlpha=alpha;ctx.translate(CX,CY);ctx.rotate(a);
    ctx.beginPath();ctx.arc(0,0,R,0,TAU);ctx.clip();
    ctx.drawImage(disk,8,8,1184,1184,-R,-R,R*2,R*2);ctx.restore();
  }
  function sparkle(ctx,x,y,r,opacity){
    ctx.save();ctx.globalAlpha=opacity;ctx.translate(x,y);ctx.beginPath();ctx.moveTo(0,-r);ctx.quadraticCurveTo(r*.13,-r*.13,r,0);ctx.quadraticCurveTo(r*.13,r*.13,0,r);ctx.quadraticCurveTo(-r*.13,r*.13,-r,0);ctx.quadraticCurveTo(-r*.13,-r*.13,0,-r);ctx.fillStyle='#fff0c2';ctx.fill();ctx.restore();
  }
  function render(ctx,assets,t,{width=W,height=H,motionBlur=true,outcome='Royal'}={}){
    t=clamp(t,0,DURATION);
    const prize=outcomeConfig(outcome);
    const a=angle(t,outcome),v=velocity(t,outcome),win=smooth((t-END)/.55);
    ctx.save();ctx.setTransform(width/W,0,0,height/H,0,0);ctx.clearRect(0,0,W,H);
    ctx.drawImage(assets.background,0,0,W,H);
    drawPetals(ctx,assets.petal,t,false);
    glow(ctx,CX,CY,499,'rgba(142,25,44,.22)',.8);
    // Five shutter samples soften lettering during the fastest part of the spin.
    const samples=motionBlur&&v>1.2?5:1;
    for(let k=0;k<samples;k++)drawRotor(ctx,assets.disk,a+(k/(samples-1||1)-.5)*v/45,k===0?1:1/(k+1));
    if(win>0){
      // Highlight the selected source wedge; its center lands at the fixed top pointer.
      ctx.save();ctx.translate(CX,CY);ctx.rotate(a);ctx.beginPath();ctx.moveTo(0,0);ctx.arc(0,0,R,(prize.centerDegrees-30)*DEG,(prize.centerDegrees+30)*DEG);ctx.closePath();ctx.clip();
      const g=ctx.createRadialGradient(0,0,70,0,0,R);g.addColorStop(0,'rgba('+prize.glow+',0)');g.addColorStop(.7,'rgba('+prize.glow+',.15)');g.addColorStop(1,'rgba('+prize.edge+',.45)');ctx.fillStyle=g;ctx.globalAlpha=win*(.8+.14*Math.sin(t*2.8));ctx.fillRect(-R,-R,R*2,R*2);ctx.restore();
      ctx.save();ctx.globalAlpha=win*.75;ctx.strokeStyle=outcome==='Royal'?'#ffcf79':prize.accent;ctx.lineWidth=3;ctx.shadowColor=prize.shadow;ctx.shadowBlur=16;ctx.beginPath();ctx.arc(CX,CY,R-6,-Math.PI/2-Math.PI/6,-Math.PI/2+Math.PI/6);ctx.stroke();ctx.restore();
    }
    ctx.drawImage(assets.frame,0,0,W,H);
    ctx.drawImage(assets.pointer,0,0,W,H);
    ctx.drawImage(assets.hub,0,0,W,H);
    glow(ctx,CX,CY,74,'rgba(255,39,78,.17)',.7+.2*Math.sin(t*2.4));
    // One glint moves over the fixed ruby; its silhouette never rotates or scales.
    sparkle(ctx,CX-21,CY-31,5,.28+.20*Math.sin(t*3.1));
    ctx.drawImage(assets.candles,0,0,W,H);
    [[46,801],[126,1020],[1016,896],[1057,981]].forEach(([x,y],i)=>drawFlame(ctx,x,y,t,i));
    drawPetals(ctx,assets.petal,t,true);
    ctx.drawImage(assets.button,0,0,W,H);
    if(t>START){
      const g=ctx.createLinearGradient(0,1208,0,1282);g.addColorStop(0,'#110407');g.addColorStop(.65,'#210307');g.addColorStop(1,'#31050b');ctx.fillStyle=g;ctx.fillRect(392,1208,310,76);
      ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=t>=END?'italic 61px "Liberation Serif", Georgia, serif':'italic 35px "Liberation Serif", Georgia, serif';
      ctx.fillStyle=t>=END?prize.accent:'#ffece1';ctx.shadowColor=t>=END?prize.shadow:'#ff813b';ctx.shadowBlur=t>=END?14:4;ctx.fillText(t>=END?prize.name:'Судьба решает…',CX,1248);ctx.shadowBlur=0;
    }
    ctx.textAlign='center';ctx.textBaseline='alphabetic';ctx.font='italic 43px "Liberation Serif", Georgia, serif';ctx.fillStyle='#fff1e1';ctx.shadowColor='#9b411b';ctx.shadowBlur=5;
    ctx.fillText(t<=START?'Колесо судьбы':t<END?'Колесо вращается…':'Твой исход — '+prize.name,CX,91);ctx.shadowBlur=0;
    ctx.strokeStyle='rgba(251,182,143,.7)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(306,123);ctx.lineTo(780,123);ctx.stroke();sparkle(ctx,CX,123,10,1);
    if(win>0){
      for(let i=0;i<14;i++){
        const elapsed=t-END,ph=i*2.399,distance=35+elapsed*(35+i*4),x=CX+Math.cos(ph)*distance*.9,y=CY-335+Math.sin(ph)*distance*.5;
        sparkle(ctx,x,y,3+i%3,win*clamp(1-elapsed/2.6)*(.4+.4*Math.sin(i+t*6)));
      }
    }
    ctx.restore();
    return {time:t,angle:a,velocity:v,outcome:t>=END?prize.name:null,phase:t<=START?'idle':t<END?'spinning':'result',pointer:{x:CX,y:350},hub:{x:CX,y:CY}};
  }
  const api={W,H,CX,CY,R,START,END,DURATION,TARGET,OUTCOMES,outcomeConfig,targetFor,angle,velocity,render};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else {scope.VelvetWheel=api;scope.RoyalWheel=api;}
})(typeof globalThis!=='undefined'?globalThis:this);
