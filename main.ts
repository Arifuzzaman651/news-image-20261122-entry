// "The World in One Day" — Sunday 22 November 2026 (Node 22, standard library only).
// The poster is the entry.png beside this file: a newspaper front page summing up
// the day's news, drawn by render_poster.py from the verified stories in
// stories.json. This program copies it to /output/entry.png.
// The file is a JPEG under 1 MiB at 1024x1024, and the copy is byte-for-byte, so
// both runs of the program write identical bytes.
//
// Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { copyFileSync, mkdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const OUTPUT_DIR = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const DEST = join(OUTPUT_DIR, 'entry.png');
const MAX_BYTES = 1048576; // gate cap: at most 1 MiB

mkdirSync(OUTPUT_DIR, { recursive: true });
copyFileSync(new URL('./entry.png', import.meta.url), DEST);

// Sanity checks: the gate refuses an empty file, a non-image, or anything
// over 1 MiB, so fail loudly instead of handing one in. A successful copy
// is byte-for-byte identical to the source.
const size = statSync(DEST).size;
if (size === 0) {
  throw new Error('entry.png copied to /output is empty');
}
if (size > MAX_BYTES) {
  throw new Error(`entry.png is ${size} bytes, over the 1 MiB gate cap`);
}
const head = readFileSync(DEST).subarray(0, 8);
const isJpeg = head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff;
const isPng =
  head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47;
if (!isJpeg && !isPng) {
  throw new Error('entry.png is neither a JPEG nor a PNG (bad magic bytes)');
}
console.log(`entry.png written (${size} bytes)`);
