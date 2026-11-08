#!/usr/bin/env node
// Production build: `node scripts/build.mjs` (set NODE_ENV=development for an unminified build).
import { buildAll } from './lib/pipeline.mjs';

const production = process.env.NODE_ENV !== 'development';
const started = Date.now();
try {
  const out = await buildAll({ production });
  const kb = (n) => (n / 1024).toFixed(1) + ' kB';
  console.log(
    `[ednova] built dist/ in ${Date.now() - started} ms — ${out.jsFile} (${kb(out.jsBytes)}), ${out.cssFile} (${kb(out.cssBytes)})`,
  );
} catch (err) {
  console.error('[ednova] build failed');
  console.error(err);
  process.exit(1);
}
