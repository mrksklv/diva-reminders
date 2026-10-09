import { mkdir, writeFile } from 'node:fs/promises';

let config;
try {
  config = JSON.parse(process.env.BOT_CONFIG);
} catch {
  throw new Error('Set BOT_CONFIG to valid JSON matching config.example.json');
}

if (!config || !Number.isSafeInteger(config.channelId) || config.channelId >= 0 ||
    !/^@[a-zA-Z0-9_]+$/.test(config.channelUsername) ||
    typeof config.channelEmoji !== 'string' ||
    !Array.isArray(config.subscriberIds) || !config.subscriberIds.length ||
    config.subscriberIds.some(id => !Number.isSafeInteger(id) || id <= 0) ||
    !Number.isInteger(config.streakDays) || config.streakDays < 1) {
  throw new Error('Invalid BOT_CONFIG: check channel, recipients, emoji, and streakDays');
}
try {
  new Intl.DateTimeFormat('en', { timeZone: config.timezone }).format();
  if (typeof config.timezone !== 'string') throw new Error();
  if (config.initialLastPostAt != null &&
      (typeof config.initialLastPostAt !== 'string' ||
       !/(Z|[+-]\d{2}:\d{2})$/.test(config.initialLastPostAt) ||
       !Number.isFinite(Date.parse(config.initialLastPostAt)))) throw new Error();
} catch {
  throw new Error('Invalid BOT_CONFIG timezone or initialLastPostAt');
}
config.initialLastPostAt ??= null;
config.initialSent = { close: false, final: false, lost: false, ...config.initialSent };
if (Object.values(config.initialSent).some(value => typeof value !== 'boolean')) {
  throw new Error('BOT_CONFIG initialSent values must be booleans');
}


if (process.env.GITHUB_ACTIONS === 'true') {
  const mask = value => {
    if (value && typeof value === 'object') return Object.values(value).forEach(mask);
    if (value == null || typeof value === 'boolean' || value === '') return;
    const escaped = String(value).replaceAll('%', '%25').replaceAll('\r', '%0D').replaceAll('\n', '%0A');
    console.log(`::add-mask::${escaped}`);
  };
  mask(config);
}

const target = new URL('../tgcloud/lib/config.js', import.meta.url);
await mkdir(new URL('.', target), { recursive: true });
await writeFile(target, `// Generated from BOT_CONFIG. Do not commit.\nexport const config = ${JSON.stringify(config, null, 2)};\n`, { mode: 0o600 });
