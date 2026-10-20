'use strict';
// Every integer Celsius value in this dated grid, without crossing missing cells.
function integerTemperatureLevels(grid){
 let min=Infinity,max=-Infinity;
 for(const row of grid.values)for(const value of row){
  if(value!==null&&Number.isFinite(value)){min=Math.min(min,value);max=Math.max(max,value);}
 }
 const levels=[];
 for(let level=Math.ceil(min);level<=Math.floor(max);level++)levels.push(level);
 return levels;
}
function temperatureContours(grid,levels=integerTemperatureLevels(grid)){
 return levels.map(level=>{
  const segments=[];
  for(let i=0;i<grid.lat.length-1;i++)for(let j=0;j<grid.lon.length-1;j++){
   const values=[grid.values[i][j],grid.values[i][j+1],grid.values[i+1][j+1],grid.values[i+1][j]];
   if(values.some(v=>v===null||!Number.isFinite(v)))continue;
   const corners=[[grid.lon[j],grid.lat[i]],[grid.lon[j+1],grid.lat[i]],[grid.lon[j+1],grid.lat[i+1]],[grid.lon[j],grid.lat[i+1]]];
   const hits=[];
   for(let k=0;k<4;k++){
    const n=(k+1)%4,a=values[k],b=values[n];
    if((a<level)===(b<level))continue;
    const f=(level-a)/(b-a);
    hits.push([corners[k][0]+f*(corners[n][0]-corners[k][0]),corners[k][1]+f*(corners[n][1]-corners[k][1])]);
   }
   if(hits.length===2)segments.push(hits);
   else if(hits.length===4){
    // Asymptotic decider resolves a saddle without inventing a centre observation.
    const q=(values[0]-level)*(values[2]-level)-(values[1]-level)*(values[3]-level);
    if(q>=0)segments.push([hits[0],hits[1]],[hits[2],hits[3]]);
    else segments.push([hits[0],hits[3]],[hits[1],hits[2]]);
   }
  }
  return {level,segments};
 });
}
if(typeof module!=='undefined')module.exports={temperatureContours,integerTemperatureLevels};
