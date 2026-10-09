import { config } from '../lib/config.js';
import { rememberPost, checkReminders } from '../lib/service.js';

export default async function (message) {
  if (message.chat.id !== config.channelId) return;
  
  await rememberPost(message);
  
  return checkReminders();
}
