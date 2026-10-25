const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createHooks} = require('../docs/explore/integration.js');
const {catalogUrl, manifestUrl} = require('../docs/explore/integration.js');

test('remote catalogs resolve current and archived manifests against the data origin', () => {
  const catalog = catalogUrl({catalogUrl:'https://data.example.com/explore/catalog.json'}, 'https://example.com/explore/');
  const entry = {manifest:'data/demo/aaaaaaaaaaaaaaaa/manifest.json',versions:[{bundle:'bbbbbbbbbbbbbbbb',manifest:'data/demo/bbbbbbbbbbbbbbbb/manifest.json'}]};
  assert.equal(manifestUrl(entry,new URLSearchParams(),catalog),'https://data.example.com/explore/data/demo/aaaaaaaaaaaaaaaa/manifest.json');
  assert.equal(manifestUrl(entry,new URLSearchParams('bundle=bbbbbbbbbbbbbbbb'),catalog),'https://data.example.com/explore/data/demo/bbbbbbbbbbbbbbbb/manifest.json');
  assert.equal(manifestUrl(entry,new URLSearchParams('bundle=cccccccccccccccc'),catalog),'https://data.example.com/explore/data/demo/cccccccccccccccc/manifest.json');
  assert.equal(manifestUrl(entry,new URLSearchParams('bundle=../../other'),catalog),manifestUrl(entry,new URLSearchParams(),catalog));
  assert.equal(catalogUrl(null,'https://example.com/explore/'),'https://example.com/explore/catalog.json');
});

test('the standalone viewer needs no host adapter and retains share state', () => {
  const hooks = createHooks();
  hooks.ready({city:'demo'}, 123); hooks.action(); hooks.event('artworkReady');
  const href = 'https://example.com/explore/#city=demo&time=123';
  assert.equal(hooks.shareUrl(href), href);
});
test('failing host callbacks and invalid share overrides cannot break the viewer', () => {
  const hooks = createHooks({ready(){throw Error('collector down');}, shareUrl(){return 'javascript:bad';}});
  assert.doesNotThrow(() => hooks.ready({}, 123));
  const href = 'https://example.com/explore/#city=demo';
  assert.equal(hooks.shareUrl(href), href);
});
test('the host receives lifecycle and successful action notifications with context', () => {
  const records = [];
  const hooks = createHooks({ready:(...args)=>records.push(['ready',...args]), event:(...args)=>records.push(['event',...args]), shareUrl:href=>href.replace('/explore/', '/explore/?utm_source=visitor_share')});
  hooks.ready({city:'demo',bundle:'demo',view:'rhythm'}, 123);
  hooks.event('loadFailed',{stage:'day'}); hooks.event('linkCopied');
  assert.deepEqual(records, [['ready',{city:'demo',bundle:'demo',view:'rhythm'},123],['event','loadFailed',{stage:'day'}],['event','linkCopied']]);
  assert.equal(hooks.shareUrl('https://example.com/explore/#city=demo'), 'https://example.com/explore/?utm_source=visitor_share#city=demo');
});
