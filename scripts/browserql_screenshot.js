#!/usr/bin/env node
/**
 * Minimal BrowserQL runner: navigate to a URL and take a screenshot.
 *
 * Usage:
 *   node scripts/browserql_screenshot.js https://example.com out.jpg
 *
 * Auth:
 *   Reads Browserless token from Clawdbot config at ~/.clawdbot/clawdbot.json
 *   (browser.profiles.browserless.cdpUrl query param token=...)
 */

import fs from 'node:fs';
import path from 'node:path';

function getTokenFromClawdbotConfig() {
  const cfgPath = path.join(process.env.HOME || '', '.clawdbot', 'clawdbot.json');
  const raw = fs.readFileSync(cfgPath, 'utf8');
  const cfg = JSON.parse(raw);
  const cdpUrl = cfg?.browser?.profiles?.browserless?.cdpUrl;
  if (!cdpUrl) throw new Error('Missing browser.profiles.browserless.cdpUrl in ~/.clawdbot/clawdbot.json');
  const u = new URL(cdpUrl);
  const token = u.searchParams.get('token');
  if (!token) throw new Error('No token=... found in browserless cdpUrl');
  return token;
}

async function main() {
  const [url, outPath] = process.argv.slice(2);
  if (!url || !outPath) {
    console.error('Usage: node scripts/browserql_screenshot.js <url> <out.jpg>');
    process.exit(2);
  }

  const token = getTokenFromClawdbotConfig();

  // BrowserQL endpoint (Chromium)
  const endpoint = 'https://production-sfo.browserless.io/chromium/bql';

  const body = {
    query: `
      mutation Screenshot($url: String!) {
        goto(url: $url, waitUntil: load) { status }
        screenshot(type: jpeg, fullPage: true) { base64 }
      }
    `,
    variables: { url },
  };

  const res = await fetch(`${endpoint}?token=${token}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch {
    throw new Error(`Non-JSON response (HTTP ${res.status}): ${text.slice(0, 200)}`);
  }

  if (!res.ok || json.errors?.length) {
    throw new Error(`BrowserQL error (HTTP ${res.status}): ${JSON.stringify(json.errors || json, null, 2)}`);
  }

  const b64 = json?.data?.screenshot?.base64;
  if (!b64) throw new Error('No screenshot.base64 in response');

  const buf = Buffer.from(b64, 'base64');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);

  console.log(`OK ${outPath} (${buf.length} bytes)`);
}

main().catch((err) => {
  console.error(String(err?.stack || err));
  process.exit(1);
});
