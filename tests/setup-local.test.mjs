import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { parseEnv } from 'node:util';

const template = readFileSync(new URL('../.env.example', import.meta.url), 'utf8');
const script = new URL('../scripts/setup-local.mjs', import.meta.url);
const proxySecret = 'existing-proxy-secret-'.repeat(4);

function fixture(t, example = template) {
  const root = mkdtempSync(join(tmpdir(), 'viraldy-setup-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const dir of ['scripts', 'apps/backend', 'apps/web']) {
    mkdirSync(join(root, dir), { recursive: true });
  }
  copyFileSync(script, join(root, 'scripts/setup-local.mjs'));
  writeFileSync(join(root, '.env.example'), example);
  return root;
}

function run(root, cwd = root) {
  return spawnSync(process.execPath, [join(root, 'scripts/setup-local.mjs')], {
    cwd,
    encoding: 'utf8',
  });
}

function read(root, path) {
  return readFileSync(join(root, path), 'utf8');
}

test('fresh clone creates private env files with independent secrets and matching defaults', (t) => {
  const root = fixture(t);
  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  const backend = parseEnv(read(root, 'apps/backend/.env'));
  const web = parseEnv(read(root, 'apps/web/.env.local'));
  assert.match(backend.AUTH_JWT_SECRET, /^[a-f0-9]{64}$/);
  assert.match(backend.AUTH_PROXY_SECRET, /^[a-f0-9]{64}$/);
  assert.notEqual(backend.AUTH_JWT_SECRET, backend.AUTH_PROXY_SECRET);
  assert.equal(web.AUTH_PROXY_SECRET, backend.AUTH_PROXY_SECRET);
  assert.equal(backend.AUTH_MODE, 'password');
  assert.equal(backend.AUTH_DISABLED, 'false');
  assert.equal(web.VITE_API_BASE_URL, 'http://localhost:8000/api/v1');
  assert.equal(web.AUTH_PUBLIC_ORIGIN, 'http://localhost:5173');
  assert.deepEqual(JSON.parse(backend.BACKEND_CORS_ORIGINS), [web.AUTH_PUBLIC_ORIGIN]);
  assert.equal(web.AUTH_TRUST_PROXY_HEADERS, 'false');
  assert.equal(backend.AI_MODE, 'fixture');
  assert.equal(backend.TIKTOK_MARKET_INTELLIGENCE, 'false');
  assert.equal(backend.CREATIVE_FAMILY, 'false');
  assert.equal(web.AUTH_JWT_SECRET, undefined);
  assert.equal(web.DATABASE_URL, undefined);
  assert.equal(web.GEMINI_API_KEY, undefined);
  for (const path of ['apps/backend/.env', 'apps/web/.env.local']) {
    assert.equal(statSync(join(root, path)).mode & 0o777, 0o600);
  }
  assert.ok(!result.stdout.includes(backend.AUTH_JWT_SECRET));
  assert.ok(!result.stdout.includes(backend.AUTH_PROXY_SECRET));
});

test('a rerun preserves file contents, secret values, and timestamps', (t) => {
  const root = fixture(t);
  assert.equal(run(root).status, 0);
  const paths = ['apps/backend/.env', 'apps/web/.env.local'];
  const before = paths.map((path) => ({
    content: read(root, path),
    modified: statSync(join(root, path)).mtimeMs,
  }));
  assert.equal(run(root).status, 0);
  for (const [index, path] of paths.entries()) {
    assert.equal(read(root, path), before[index].content);
    assert.equal(statSync(join(root, path)).mtimeMs, before[index].modified);
  }
});

test('missing web env reuses the backend proxy secret without rewriting backend settings', (t) => {
  const root = fixture(t);
  const original = `AUTH_MODE=oidc\nAUTH_JWT_SECRET=keep-this-jwt\nexport AUTH_PROXY_SECRET='${proxySecret}' # keep\nTIKTOK_MARKET_INTELLIGENCE=true\n`;
  writeFileSync(join(root, 'apps/backend/.env'), original);
  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(read(root, 'apps/backend/.env'), original);
  assert.equal(parseEnv(read(root, 'apps/web/.env.local')).AUTH_PROXY_SECRET, proxySecret);
});

test('missing backend env reuses the web proxy secret and generates its own JWT secret', (t) => {
  const root = fixture(t);
  const original = `AUTH_PUBLIC_ORIGIN=http://localhost:5173\nAUTH_PROXY_SECRET="${proxySecret}"\n`;
  writeFileSync(join(root, 'apps/web/.env.local'), original);
  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  const backend = parseEnv(read(root, 'apps/backend/.env'));
  assert.equal(read(root, 'apps/web/.env.local'), original);
  assert.equal(backend.AUTH_PROXY_SECRET, proxySecret);
  assert.match(backend.AUTH_JWT_SECRET, /^[a-f0-9]{64}$/);
  assert.notEqual(backend.AUTH_JWT_SECRET, proxySecret);
});

test('separate fresh clones get different secrets', (t) => {
  const first = fixture(t);
  const second = fixture(t);
  assert.equal(run(first).status, 0);
  assert.equal(run(second).status, 0);
  const a = parseEnv(read(first, 'apps/backend/.env'));
  const b = parseEnv(read(second, 'apps/backend/.env'));
  assert.notEqual(a.AUTH_JWT_SECRET, b.AUTH_JWT_SECRET);
  assert.notEqual(a.AUTH_PROXY_SECRET, b.AUTH_PROXY_SECRET);
});

for (const existing of ['apps/backend/.env', 'apps/web/.env.local']) {
  test(`a blank proxy secret in ${existing} fails without creating a mismatched peer`, (t) => {
    const root = fixture(t);
    const original = 'AUTH_PROXY_SECRET=\n# Private settings must stay intact.\n';
    writeFileSync(join(root, existing), original);
    const result = run(root);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /AUTH_PROXY_SECRET/);
    assert.equal(read(root, existing), original);
    const missing = existing === 'apps/backend/.env' ? 'apps/web/.env.local' : 'apps/backend/.env';
    assert.equal(existsSync(join(root, missing)), false);
  });
}

test('existing files stay untouched even when settings differ from the template', (t) => {
  const root = fixture(t);
  const backend = 'AUTH_MODE=oidc\nAUTH_PROXY_SECRET=custom-backend\nMARKET_PATTERN_EVIDENCE=true\n';
  const web = 'AUTH_PUBLIC_ORIGIN=http://localhost:9999\nAUTH_PROXY_SECRET=custom-web\n';
  writeFileSync(join(root, 'apps/backend/.env'), backend);
  writeFileSync(join(root, 'apps/web/.env.local'), web);
  rmSync(join(root, '.env.example'));
  assert.equal(run(root).status, 0);
  assert.equal(read(root, 'apps/backend/.env'), backend);
  assert.equal(read(root, 'apps/web/.env.local'), web);
});

test('web env copies only public API config and the private auth runtime allowlist', (t) => {
  const root = fixture(t, `${template}\nPRIVATE_PROVIDER_TOKEN=do-not-copy\n`);
  const result = run(root);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(Object.keys(parseEnv(read(root, 'apps/web/.env.local'))).sort(), [
    'AUTH_PROXY_SECRET',
    'AUTH_PUBLIC_ORIGIN',
    'AUTH_TRUST_PROXY_HEADERS',
    'VITE_API_BASE_URL',
  ]);
  assert.match(read(root, 'apps/backend/.env'), /PRIVATE_PROVIDER_TOKEN=do-not-copy/);
});

test('script finds its clone root even when invoked from another working directory', (t) => {
  const root = fixture(t);
  assert.equal(run(root, join(root, 'apps/web')).status, 0);
  assert.equal(existsSync(join(root, 'apps/backend/.env')), true);
  assert.equal(existsSync(join(root, 'apps/web/.env.local')), true);
});

test('missing template fails before creating either env file', (t) => {
  const root = fixture(t);
  rmSync(join(root, '.env.example'));
  const result = run(root);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /\.env\.example/);
  assert.equal(existsSync(join(root, 'apps/backend/.env')), false);
  assert.equal(existsSync(join(root, 'apps/web/.env.local')), false);
});

test('make setup-env works twice in an isolated clone fixture', (t) => {
  const root = fixture(t);
  copyFileSync(new URL('../Makefile', import.meta.url), join(root, 'Makefile'));
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const result = spawnSync('make', ['setup-env'], { cwd: root, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  }
  const backend = parseEnv(read(root, 'apps/backend/.env'));
  const web = parseEnv(read(root, 'apps/web/.env.local'));
  assert.equal(backend.AUTH_PROXY_SECRET, web.AUTH_PROXY_SECRET);
  assert.notEqual(backend.AUTH_JWT_SECRET, web.AUTH_PROXY_SECRET);
});

test('exclusive creation preserves a dangling env symlink and does not create its target', (t) => {
  const root = fixture(t);
  const target = join(root, 'private-backend-env');
  symlinkSync(target, join(root, 'apps/backend/.env'));
  const result = run(root);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /EEXIST/);
  assert.equal(existsSync(target), false);
  assert.equal(existsSync(join(root, 'apps/web/.env.local')), false);
});

test('multiline existing secrets require manual copying instead of producing mismatched values', (t) => {
  const root = fixture(t);
  const original = `AUTH_PROXY_SECRET="${proxySecret}\nsecond-line"\n`;
  writeFileSync(join(root, 'apps/backend/.env'), original);
  const result = run(root);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /single-line/);
  assert.ok(!result.stderr.includes(proxySecret));
  assert.equal(read(root, 'apps/backend/.env'), original);
  assert.equal(existsSync(join(root, 'apps/web/.env.local')), false);
});
