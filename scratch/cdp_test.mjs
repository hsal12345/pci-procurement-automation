import { spawn } from 'node:child_process';

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const chromeProc = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9222',
  '--user-data-dir=C:\\Users\\User\\.gemini\\antigravity-ide\\brain\\78dccf6b-850a-4038-a21f-be8d977a857c\\scratch\\chrome-test-profile',
  'http://localhost:3000/packages'
]);

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function run() {
  await sleep(2500);

  const targetsRes = await fetch('http://localhost:9222/json');
  const targets = await targetsRes.json();
  const pageTarget = targets.find(t => t.type === 'page');
  if (!pageTarget) {
    console.error('No page target found');
    chromeProc.kill();
    return;
  }

  console.log('Connecting to WebSocket:', pageTarget.webSocketDebuggerUrl);
  const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

  let id = 1;
  function send(method, params = {}) {
    ws.send(JSON.stringify({ id: id++, method, params }));
  }

  const errors = [];
  const logs = [];

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.method === 'Runtime.consoleAPICalled') {
      const text = data.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
      logs.push(`[CONSOLE ${data.params.type}] ${text}`);
      if (data.params.type === 'error') {
        errors.push(`[CONSOLE ERROR] ${text}`);
      }
    } else if (data.method === 'Runtime.exceptionThrown') {
      const details = data.params.exceptionDetails;
      errors.push(`[EXCEPTION] ${details.text} ${details.exception?.description || ''}`);
    } else if (data.method === 'Network.responseReceived') {
      const status = data.params.response.status;
      const url = data.params.response.url;
      if (status >= 400 && !url.includes('.ico')) {
        errors.push(`[HTTP ${status}] ${url}`);
      }
    }
  };

  await new Promise(r => ws.onopen = r);

  send('Page.enable');
  send('Runtime.enable');
  send('Network.enable');

  console.log('--- Testing /packages page ---');
  await sleep(3000);

  const pkgsRes = await fetch('http://localhost:8000/api/v1/packages');
  const pkgs = await pkgsRes.json();
  const pkgId = pkgs[0]?.id;
  console.log('Using active package ID:', pkgId);

  console.log(`--- Testing /packages/${pkgId} ---`);
  send('Page.navigate', { url: `http://localhost:3000/packages/${pkgId}` });
  await sleep(4000);

  // Test tabs
  const tabKeys = ['identity', 'items', 'dates', 'logistics', 'inspection', 'documents', 'audit'];
  for (const tab of tabKeys) {
    console.log(`--- Testing tab: ${tab} ---`);
    send('Page.navigate', { url: `http://localhost:3000/packages/${pkgId}?tab=${tab}` });

    await sleep(2000);
  }

  console.log('--- Testing /imports ---');
  send('Page.navigate', { url: 'http://localhost:3000/imports' });
  await sleep(2500);

  console.log('--- Testing /ai/usage ---');
  send('Page.navigate', { url: 'http://localhost:3000/ai/usage' });
  await sleep(2500);


  console.log('\n===== LOGS SUMMARY =====');
  logs.forEach(l => console.log(l));

  console.log('\n===== ERRORS ENCOUNTERED =====');
  if (errors.length === 0) {
    console.log('NO ERRORS FOUND!');
  } else {
    errors.forEach(e => console.log(e));
  }

  ws.close();
  chromeProc.kill();
  process.exit(0);
}

run().catch(err => {
  console.error(err);
  chromeProc.kill();
  process.exit(1);
});
