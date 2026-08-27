import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const watermarkSource = readFileSync(new URL('../src/components/ResultWatermark.tsx', import.meta.url), 'utf8');
const teamPageSource = readFileSync(new URL('../src/pages/TeamPage.tsx', import.meta.url), 'utf8');
const analyticsPageSource = readFileSync(new URL('../src/pages/UsageAnalyticsPage.tsx', import.meta.url), 'utf8');

assert.match(
  watermarkSource,
  /content=\{`MSKPP&AIBench \+ \$\{employeeId\}`\}/,
  'result watermark must include the authenticated employee ID',
);
assert.match(
  teamPageSource,
  /<ResultWatermark className="team-archive-watermark">/,
  'team achievement archive drawer must use ResultWatermark',
);
assert.match(
  analyticsPageSource,
  /<ResultWatermark className="analytics-user-detail-watermark">/,
  'identified user analytics drawer must use ResultWatermark',
);

console.log('Result watermark checks passed');
