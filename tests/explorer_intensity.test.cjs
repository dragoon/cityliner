const {test}=require('node:test');
const assert=require('node:assert/strict');
const {visual,color,blend}=require('../docs/explore/intensity.js');

test('local normalization reveals a corridor slowing down even beside a busy corridor',()=>{
  const quiet=visual(1,8,80,'rhythm').intensity;
  const peak=visual(8,8,80,'rhythm').intensity;
  assert(quiet<peak*.1);
  assert.equal(peak,visual(80,80,80,'rhythm').intensity);
  assert(visual(8,8,80,'departures').intensity<visual(80,80,80,'departures').intensity);
});
test('a fixed weekly reference preserves date and mode comparisons',()=>{
  assert.equal(visual(4,8,80,'rhythm').intensity,visual(4,8,8,'rhythm').intensity);
  assert(visual(4,8,80,'rhythm').intensity<visual(8,8,80,'rhythm').intensity);
  assert.equal(visual(0,8,80,'rhythm').intensity,0);
  assert.equal(visual(0,0,0,'rhythm').intensity,0);
});
test('change view distinguishes disappeared, unchanged, and increased service',()=>{
  const down=visual(0,8,80,'change',4),same=visual(4,8,80,'change',4),up=visual(8,8,80,'change',4);
  assert(down.delta<0&&up.delta>0);
  assert.equal(down.intensity,up.intensity);
  assert.equal(same.intensity,0);
  assert.equal(visual(4.5,6,80,'change',4).delta,.5);
});
test('display transforms leave fractional frequency counts untouched',()=>{
  assert(visual(4.5,6,80,'rhythm').intensity>visual(4,6,80,'rhythm').intensity);
  assert.equal(color('#b4eccd',1),'rgb(180,236,205)');
  assert.equal(color('#b4eccd',0),'rgb(0,0,0)');
});
test('rare departures stay subdued and all views fade continuously from zero',()=>{
  assert(visual(1,1,80,'rhythm').intensity<.25);
  for(const view of ['rhythm','change','departures']){
    assert(visual(.00001,8,80,view,0).intensity<.001);
    assert.equal(visual(0,8,80,view,0).intensity,0);
  }
});
test('animation interpolates counts without mutating cached timetable frames',()=>{
  const a=new Float32Array([0,8,4.5]),b=new Float32Array([4,0,6]),out=new Float32Array(3);
  assert.deepEqual([...blend(a,b,.5,out)],[2,4,5.25]);
  assert.deepEqual([...a],[0,8,4.5]);assert.deepEqual([...b],[4,0,6]);
  assert.deepEqual([...blend(a,b,0,out)],[...a]);
  assert.deepEqual([...blend(a,b,1,out)],[...b]);
});
test('adjacent animation intervals meet without a frame-boundary jump',()=>{
  const a=new Float32Array([0,8]),b=new Float32Array([4,0]),c=new Float32Array([0,6]);
  const end=blend(a,b,1,new Float32Array(2)),start=blend(b,c,0,new Float32Array(2));
  assert.deepEqual([...end],[...start]);
  for(let i=0;i<=100;i++){
    const v=blend(a,b,i/100,new Float32Array(2));
    assert(v[0]>=0&&v[0]<=4&&v[1]>=0&&v[1]<=8);
  }
});
