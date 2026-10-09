import { api, db } from 'sdk';
import { config } from './config.js';
import { dueReminder, russianNumber } from './logic.js';

export const nowSeconds = () => Math.floor(Date.now() / 1000);

export async function state() {
  await db.run(`INSERT INTO channel_state (channel_id, last_post_at)
    VALUES (:channel, :initial) ON CONFLICT(channel_id) DO NOTHING`, {
    ':channel': config.channelId,
    ':initial': config.initialLastPostAt == null ? null : Math.floor(Date.parse(config.initialLastPostAt) / 1000),
  });
  return db.get('SELECT * FROM channel_state WHERE channel_id = :channel', { ':channel': config.channelId });
}

async function notify(text) {
  for (const chatId of config.subscriberIds) {
    try {
      await api.sendMessage({
        chat_id: chatId, parse_mode: 'HTML',
        text: `${text}\n\n<b>${config.channelEmoji} ${config.channelUsername}</b>`,
        link_preview_options: { is_disabled: true },
      });
    } catch (error) {
      console.error('Could not send notification', { code: error.code });
    }
  }
}

export async function rememberPost(message) {
  await state();
  await db.run(`UPDATE channel_state SET last_post_at = :posted, close_sent = 0, final_sent = 0, lost_sent = 0
    WHERE channel_id = :channel AND (last_post_at IS NULL OR last_post_at < :posted)`, {
    ':channel': config.channelId, ':posted': message.date,
  });

  if (message.media_group_id) {
    const id = `${config.channelId}:${message.media_group_id}`;
    const inserted = await db.run(`INSERT INTO albums (id) VALUES (:id)
      ON CONFLICT(id) DO NOTHING RETURNING id`, { ':id': id });
    if (!inserted.rows.length) return;
  }

  const url = `https://t.me/${config.channelUsername.slice(1)}/${message.message_id}`;
  await notify(`✨ в канале вышел новый <a href="${url}">пост</a>!`);
}

export async function checkReminders() {
  const current = await state();
  const reminder = dueReminder(current.last_post_at, nowSeconds(), config);
  if (!reminder) return;

  const flag = `${reminder}_sent`;
  const claimed = await db.run(`UPDATE channel_state SET ${flag} = 1
    WHERE channel_id = :channel AND last_post_at = :posted AND ${flag} = 0 RETURNING channel_id`, {
    ':channel': config.channelId, ':posted': current.last_post_at,
  });
  if (!claimed.rows.length) return;

  const texts = {
    close: '🔥 ты близко! завтра — последний день, чтобы сохранить серию',
    final: '⏰ ОСТАЛОСЬ 2 ЧАСА! опубликуй пост до полуночи',
    lost: `💔 серия потеряна — постов не было ${russianNumber(config.streakDays, 'день', 'дня', 'дней')}`,
  };
  await notify(texts[reminder]);
}
