// Upload do instalador para o Vercel Blob (download publico no site).
//
// Uso (a partir de web/):
//   node scripts/upload.mjs
//   node scripts/upload.mjs ../dist/Maouse-Setup-1.0.0.exe Maouse-Setup-1.0.0.exe
//
// Lê o token de process.env.BLOB_READ_WRITE_TOKEN ou de web/.env.local.
// Depois do upload confirma o blob com head() e imprime a URL publica.

import { put, head } from '@vercel/blob';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { createReadStream } from 'node:fs';
import { Readable } from 'node:stream';

const installer = process.argv[2] ?? '../dist/Maouse-Setup-1.0.0.exe';
const name = process.argv[3] ?? installer.split(/[\\/]/).pop();

let token = process.env.BLOB_READ_WRITE_TOKEN;
if (!token) {
  try {
    const envLocal = readFileSync(new URL('../.env.local', import.meta.url), 'utf8');
    const m = envLocal.match(/^BLOB_READ_WRITE_TOKEN="([^"]+)"/m);
    if (m) token = m[1];
  } catch {
    /* sem .env.local */
  }
}
if (!token) {
  console.error('BLOB_READ_WRITE_TOKEN nao encontrado (env ou web/.env.local).');
  process.exit(1);
}
if (!existsSync(installer)) {
  console.error('Instalador nao encontrado:', installer);
  process.exit(1);
}

const size = statSync(installer).size;
console.log(`[1/2] A enviar ${(size / 1048576).toFixed(1)} MB -> ${name}`);

const stream = Readable.toWeb(createReadStream(installer));
const blob = await put(name, stream, {
  access: 'public',
  addRandomSuffix: false,
  contentType: 'application/octet-stream',
  multipart: size > 10 * 1024 * 1024,
  token,
});

console.log('[2/2] URL:', blob.url);
const info = await head(blob.url, { token }).catch(() => null);
if (info) {
  console.log(
    `  OK: ${(info.size / 1048576).toFixed(1)} MB | ${info.contentType} | cache ${info.cacheControl}`,
  );
}