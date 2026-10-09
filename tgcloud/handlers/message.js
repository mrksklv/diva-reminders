import { api } from 'sdk';
import { config } from '../lib/config.js';
import { state, checkReminders, nowSeconds } from '../lib/service.js';
import { formatElapsed } from '../lib/logic.js';

export default async function (message) {
  const current = await state();
  const status = current.last_post_at == null ? 'я ещё не видел постов после запуска'
    : `последний пост вышел ${formatElapsed(current.last_post_at, nowSeconds())}`;

  await api.sendMessage({
    chat_id: message.chat.id, parse_mode: 'HTML',
    text: `👋 привет! я слежу за постами в ${config.channelUsername}\n${status}`,
  });
  
  return checkReminders();
}
