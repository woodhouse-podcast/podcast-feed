#!/usr/bin/env node
/**
 * Reads logs/token-usage.jsonl and prints a compact delta report.
 *
 * Output is plain text for WhatsApp.
 */
import fs from 'node:fs';
import path from 'node:path';

function readLastNLines(filePath, n = 2) {
  if (!fs.existsSync(filePath)) return [];
  const data = fs.readFileSync(filePath, 'utf8').trimEnd();
  if (!data) return [];
  const lines = data.split(/\n/);
  return lines.slice(-n);
}

function toMap(snapshot) {
  const m = new Map();
  const recent = snapshot?.status?.sessions?.recent || [];
  for (const s of recent) {
    m.set(s.key, s);
  }
  return m;
}

function fmtInt(n) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return '0';
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function main() {
  const filePath = process.argv[2] || '/home/ubuntu/clawd/logs/token-usage.jsonl';
  const lines = readLastNLines(filePath, 2);

  if (lines.length === 0) {
    console.log('No token usage snapshots found yet.');
    process.exit(0);
  }

  const cur = JSON.parse(lines[lines.length - 1]);
  const prev = lines.length > 1 ? JSON.parse(lines[0]) : null;

  const curMap = toMap(cur);
  const prevMap = prev ? toMap(prev) : new Map();

  // Total across sessions
  let curTotal = 0;
  let prevTotal = 0;
  for (const s of curMap.values()) curTotal += (s.totalTokens || 0);
  for (const s of prevMap.values()) prevTotal += (s.totalTokens || 0);
  const deltaTotal = curTotal - prevTotal;

  const header = `Token usage report (UTC ${cur.ts})`;
  const linesOut = [
    header,
    `Total (recent sessions): ${fmtInt(curTotal)} (${deltaTotal >= 0 ? '+' : ''}${fmtInt(deltaTotal)} since last snapshot)`
  ];

  // Show top deltas by session
  const deltas = [];
  for (const [key, s] of curMap.entries()) {
    const p = prevMap.get(key);
    const d = (s.totalTokens || 0) - (p?.totalTokens || 0);
    deltas.push({ key, delta: d, total: s.totalTokens || 0, model: s.model, updatedAt: s.updatedAt });
  }

  deltas.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  const top = deltas.slice(0, 5);
  linesOut.push('');
  linesOut.push('Top sessions (by change):');
  for (const d of top) {
    const sign = d.delta >= 0 ? '+' : '';
    linesOut.push(`- ${d.key} (${d.model || 'unknown'}): ${fmtInt(d.total)} (${sign}${fmtInt(d.delta)})`);
  }

  linesOut.push('');
  linesOut.push('Tip: send "/status" anytime for live session tokens; "clawdbot status --usage" shows provider windows + recent session totals.');

  console.log(linesOut.join('\n'));
}

main();
