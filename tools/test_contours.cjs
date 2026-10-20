const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {sstContours}=require('../docs/contours.js');
const grid={lat:[1,0],lon:[0,1],values:[[24,29],[24,29]]};
const contours=sstContours(grid);
assert.deepEqual(contours.map(c=>c.level),[25,26,27,28]);
for(const {level,segments} of contours){
 assert.equal(segments.length,1);
 for(const [x,y] of segments[0]){assert.ok(Math.abs(x-(level-24)/5)<1e-10);assert.ok(y===0||y===1);}
}
assert.ok(sstContours({...grid,values:[[null,29],[24,29]]}).every(c=>c.segments.length===0));
assert.ok(sstContours({...grid,values:[[23,23],[23,23]]}).every(c=>c.segments.length===0));
assert.equal(sstContours({...grid,values:[[24,28],[28,24]]},[26])[0].segments.length,2);
const dir=path.join(__dirname,'../docs/data');
const index=JSON.parse(fs.readFileSync(path.join(dir,'index.json'),'utf8'));
const product=JSON.parse(fs.readFileSync(path.join(dir,index.dates[0].file),'utf8'));
const real=sstContours(product.layers.sst);
for(const c of real)for(const s of c.segments)for(const [x,y] of s){assert.ok(x>=115&&x<=125&&y>=20&&y<=30);}
console.log(JSON.stringify({passed:true,realDate:product.date,segments:real.map(c=>({level:c.level,count:c.segments.length}))}));
