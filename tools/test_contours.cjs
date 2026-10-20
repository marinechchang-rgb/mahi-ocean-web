const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {temperatureContours,integerTemperatureLevels}=require('../docs/contours.js');
const grid={lat:[1,0],lon:[0,1],values:[[24,29],[24,29]]};
const contours=temperatureContours(grid,[25,26,27,28]);
assert.deepEqual(contours.map(c=>c.level),[25,26,27,28]);
for(const {level,segments} of contours){
 assert.equal(segments.length,1);
 for(const [x,y] of segments[0]){assert.ok(Math.abs(x-(level-24)/5)<1e-10);assert.ok(y===0||y===1);}
}
assert.ok(temperatureContours({...grid,values:[[null,29],[24,29]]}).every(c=>c.segments.length===0));
assert.ok(temperatureContours({...grid,values:[[23,23],[23,23]]}).every(c=>c.segments.length===0));
assert.equal(temperatureContours({...grid,values:[[24,28],[28,24]]},[26])[0].segments.length,2);
assert.deepEqual(integerTemperatureLevels({...grid,values:[[-1.5,3.2],[null,2]]}),[-1,0,1,2,3]);
assert.deepEqual(integerTemperatureLevels({...grid,values:[[null,null],[null,null]]}),[]);
assert.deepEqual(integerTemperatureLevels(grid),[24,25,26,27,28,29]);
const dir=path.join(__dirname,'../docs/data');
const index=JSON.parse(fs.readFileSync(path.join(dir,'index.json'),'utf8'));
const product=JSON.parse(fs.readFileSync(path.join(dir,index.dates[0].file),'utf8'));
const results=[];
for(const key of ['sst','50','100','200','400']){
 const entry=index.dates.find(d=>d.layers.includes(key));
 const d=JSON.parse(fs.readFileSync(path.join(dir,entry.file),'utf8')),g=d.layers[key];
 const real=temperatureContours(g),levels=integerTemperatureLevels(g);
 assert.deepEqual(real.map(c=>c.level),levels);
 assert.ok(real.some(c=>c.segments.length>0));
 for(let i=1;i<levels.length;i++)assert.equal(levels[i]-levels[i-1],1);
 for(const c of real)for(const s of c.segments)for(const [x,y] of s){assert.ok(x>=115&&x<=125&&y>=20&&y<=30);}
 results.push({layer:key,date:d.date,levels,segments:real.reduce((n,c)=>n+c.segments.length,0)});
}
console.log(JSON.stringify({passed:true,layers:results}));
