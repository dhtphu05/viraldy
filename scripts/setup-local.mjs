import { randomBytes } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parseEnv } from 'node:util';

const root = new URL('../', import.meta.url);
const backendPath = 'apps/backend/.env';
const webPath = 'apps/web/.env.local';

function readExisting(path) {
  try {
    return readFileSync(new URL(path, root), 'utf8');
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}

function assignment(text, name) {
  const line = [...text.matchAll(new RegExp(`^[ \\t]*(?:export[ \\t]+)?${name}[ \\t]*=.*$`, 'gm'))].at(-1)?.[0];
  const value = parseEnv(text)[name];
  if (!line || !value?.trim() || parseEnv(line)[name] !== value) {
    throw new Error(`${name} needs a nonempty single-line value; configure it in the existing env file before rerunning. No existing files were changed.`);
  }
  return line;
}

function setup() {
  const backend = readExisting(backendPath);
  const web = readExisting(webPath);
  if (backend !== null && web !== null) {
    console.log('Kept existing backend and web env files; settings were not changed or validated.');
    return;
  }

  const template = readFileSync(new URL('.env.example', root), 'utf8');
  // Reuse the exact assignment, including quoting, when only one env exists.
  const proxy = backend !== null || web !== null
    ? assignment(backend ?? web, 'AUTH_PROXY_SECRET')
    : `AUTH_PROXY_SECRET=${randomBytes(32).toString('hex')}`;
  const replacements = {
    AUTH_MODE: 'AUTH_MODE=password',
    AUTH_DISABLED: 'AUTH_DISABLED=false',
    AUTH_JWT_SECRET: `AUTH_JWT_SECRET=${randomBytes(32).toString('hex')}`,
    AUTH_PROXY_SECRET: proxy,
  };
  let backendEnv = template;
  for (const [name, line] of Object.entries(replacements)) {
    backendEnv = backendEnv.replace(new RegExp(`^${name}=.*$`, 'gm'), () => line);
  }
  // Never copy backend credentials or provider keys into the frontend env.
  const webEnv = [
    '# Local frontend config. AUTH_* values are private server runtime settings.',
    assignment(template, 'VITE_API_BASE_URL'),
    assignment(template, 'AUTH_PUBLIC_ORIGIN'),
    proxy,
    assignment(template, 'AUTH_TRUST_PROXY_HEADERS'),
    '',
  ].join('\n');

  for (const [path, existing, content] of [
    [backendPath, backend, backendEnv],
    [webPath, web, webEnv],
  ]) {
    if (existing !== null) {
      console.log(`Kept ${path}`);
      continue;
    }
    // Exclusive creation also protects existing files if two setups race.
    writeFileSync(new URL(path, root), content, { flag: 'wx', mode: 0o600 });
    console.log(`Created ${path}`);
  }
}

try {
  setup();
} catch (error) {
  console.error(`Local env setup failed in ${fileURLToPath(root)}: ${error.message}`);
  process.exitCode = 1;
}
