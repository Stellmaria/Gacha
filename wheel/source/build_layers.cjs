const fs = require('fs');
const path = require('path');
const runtime = process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
const {createCanvas, loadImage} = require(runtime ? require.resolve('@napi-rs/canvas', {paths:[runtime]}) : '@napi-rs/canvas');
const ROOT = path.resolve(__dirname, '..');
const W = 1086, H = 1448;

async function main() {
  const input=(local,fallback)=>fs.existsSync(path.join(__dirname,local))?path.join(__dirname,local):path.resolve(ROOT,fallback);
  const originalPath = input('master.png','../upload/image(20261120-225128).png');
  const rotorPath = input('disk_generated.png','../generated_images/exec-7fa86a5a-9fc6-4d7c-b6d6-8dc4077e6e4e.png');
  const backgroundPath = input('background_generated.png','../generated_images/exec-5020e0c3-b830-49ae-9328-bfd809215c63.png');
  const housingPath = input('housing_generated.png','../generated_images/exec-6f5929f9-83e1-4c3f-9315-1c11058323bc.png');
  const master = await loadImage(originalPath);
  const rotor = await loadImage(rotorPath);
  const background = await loadImage(backgroundPath);
  const housing = await loadImage(housingPath);
  const exportLayer = (name, draw, width=W, height=H) => {
    const canvas = createCanvas(width, height);
    const ctx = canvas.getContext('2d');
    draw(ctx);
    fs.writeFileSync(path.join(ROOT,'layers',name+'.png'),canvas.toBuffer('image/png'));
    return canvas;
  };
  exportLayer('01_background',ctx=>ctx.drawImage(background,0,0,W,H));
  // The extracted alpha housing is registered to the same center as the disk.
  const housingX=22.263,housingY=40.347,housingScale=.959;
  const drawHousing=ctx=>ctx.drawImage(housing,housingX,housingY,W*housingScale,H*housingScale);
  const pointerRect=[297,130,492,267],hubRect=[396,527,292,280];
  exportLayer('02_fixed_frame',ctx=>{
    drawHousing(ctx);ctx.clearRect(...pointerRect);ctx.clearRect(...hubRect);
  });
  exportLayer('03_pointer',ctx=>{
    ctx.beginPath();ctx.rect(...pointerRect);ctx.clip();drawHousing(ctx);
  });
  exportLayer('04_ruby_hub',ctx=>{
    ctx.beginPath();ctx.rect(...hubRect);ctx.clip();drawHousing(ctx);
  });
  exportLayer('05_rotating_disk',ctx=>{
    ctx.beginPath();ctx.arc(600,600,592,0,Math.PI*2);ctx.clip();
    // Sector intersection in generated source = (626, 610).
    ctx.drawImage(rotor,34,18,1184,1184,8,8,1184,1184);
  },1200,1200);
  exportLayer('06_candles',ctx=>{
    const polygons = [
      [[19,805],[73,805],[83,897],[74,919],[86,947],[72,978],[82,1023],[92,1085],[62,1100],[20,1081]],
      [[96,1025],[150,1025],[157,1092],[171,1111],[160,1141],[136,1167],[102,1134]],
      [[985,900],[1044,900],[1041,1000],[1057,1018],[1043,1040],[1051,1084],[1039,1149],[1000,1153],[989,1110],[996,1063],[977,1030],[986,1004]],
      [[1044,985],[1086,985],[1086,1112],[1050,1096],[1042,1060]]
    ];
    for(const p of polygons){ctx.save();ctx.beginPath();p.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.clip();ctx.drawImage(master,0,0);ctx.restore();}
  });
  exportLayer('07_petal',ctx=>{
    const grad=ctx.createLinearGradient(10,4,58,72);grad.addColorStop(0,'#ff6b85');grad.addColorStop(.27,'#e7214c');grad.addColorStop(.65,'#9b0b30');grad.addColorStop(1,'#390719');
    ctx.beginPath();ctx.moveTo(53,4);ctx.bezierCurveTo(46,26,6,29,13,55);ctx.bezierCurveTo(21,81,66,73,66,45);ctx.bezierCurveTo(67,24,57,13,53,4);ctx.fillStyle=grad;ctx.fill();
    ctx.strokeStyle='rgba(255,119,142,.42)';ctx.lineWidth=1.1;ctx.beginPath();ctx.moveTo(53,12);ctx.bezierCurveTo(47,38,27,45,23,61);ctx.stroke();
  },80,88);
  exportLayer('08_button',ctx=>{
    ctx.beginPath();ctx.moveTo(543,1150);
    ctx.bezierCurveTo(519,1164,499,1160,480,1175);ctx.lineTo(336,1175);
    ctx.bezierCurveTo(283,1173,250,1192,247,1238);ctx.bezierCurveTo(244,1289,279,1321,330,1320);
    ctx.lineTo(482,1320);ctx.bezierCurveTo(503,1348,519,1362,543,1384);
    ctx.bezierCurveTo(567,1362,583,1348,604,1320);ctx.lineTo(756,1320);
    ctx.bezierCurveTo(807,1321,842,1289,839,1238);ctx.bezierCurveTo(836,1192,803,1173,750,1175);
    ctx.lineTo(606,1175);ctx.bezierCurveTo(587,1160,567,1164,543,1150);
    ctx.closePath();ctx.clip();ctx.drawImage(master,0,0);
  });
  for(const [src,name]of [[originalPath,'master.png'],[rotorPath,'disk_generated.png'],[backgroundPath,'background_generated.png'],[housingPath,'housing_generated.png']]){
    const dst=path.join(ROOT,'source',name);if(path.resolve(src)!==path.resolve(dst))fs.copyFileSync(src,dst);
  }
  console.log('Eight animation layers exported.');
}
main().catch(e=>{console.error(e);process.exit(1)});
