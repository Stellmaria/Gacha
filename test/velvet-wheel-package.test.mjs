import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const wheel=resolve(root,'wheel');
const read=(p)=>readFileSync(resolve(wheel,p));
const outcomes=['Classic','Elite','Royal','Epic','Mythic','Eternal'];

test('all 33 original archive members remain byte-for-byte unchanged',()=>{
  const hashes=JSON.parse(read('checks/original_sha256.json'));
  assert.equal(Object.keys(hashes).length,33);
  for(const [path,sha] of Object.entries(hashes)){
    assert.equal(createHash('sha256').update(read(path)).digest('hex'),sha,path);
  }
});

test('each of the six outcomes has its own playable MP4 and valid rotation',()=>{
  const manifest=JSON.parse(read('animation_manifest.json'));
  assert.deepEqual(manifest.outcomes.map(x=>x.name),outcomes);
  assert.equal(manifest.composition.duration_seconds,10.4);
  for(const x of manifest.outcomes){
    assert.equal(x.video,`videos/${x.name}.mp4`);
    const mp4=read(x.video);
    assert.ok(mp4.length>2000000,`unexpectedly small MP4: ${x.name}`);
    assert.equal(mp4.toString('ascii',4,8),'ftyp',x.video);
    assert.equal((x.source_center_degrees+x.clockwise_rotation_degrees)%360,270,x.name);
  }
});

test('playable local HTML has embedded assets and no external dependency',()=>{
  const html=read('index.html').toString('utf8');
  const standalone=read('Velvet_all_outcomes.html').toString('utf8');
  assert.equal(html,standalone,'wheel/index.html must exactly mirror approved viewer');
  assert.equal((html.match(/data:image\//g)||[]).length,8);
  for(const name of outcomes)assert.ok(html.includes(name),name);
  assert.match(html,/canvas/);
  assert.match(html,/requestAnimationFrame/);
  assert.doesNotMatch(html,/<script[^>]+src="https?:\/\//i);
});

test('Gacha homepage links to the imported wheel, without removing earlier test',()=>{
  const page=readFileSync(resolve(root,'index.html'),'utf8');
  assert.ok(page.includes('href="./wheel/"'));
  assert.ok(page.includes('id="spin"'));
  assert.ok(page.includes('визуальное демо'));
});
