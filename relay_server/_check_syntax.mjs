// Quick syntax check for modified Relay files
import { readFileSync } from 'fs';

const files = [
  'D:/armtool415/relay_server/src/routes.js',
  'D:/armtool415/relay_server/src/ws_handler.js',
  'D:/armtool415/relay_server/src/db.js',
];

for (const f of files) {
  try {
    const src = readFileSync(f, 'utf8');
    // Basic syntax check via dynamic import (won't run, just parse)
    new Function('module', 'exports', 'require', src);
    console.log(`✅ ${f.split('/').pop()}`);
  } catch (e) {
    console.log(`❌ ${f.split('/').pop()}: ${e.message}`);
  }
}
