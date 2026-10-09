import { table, integer, text } from 'sdk/db';

export const channelState = table('channel_state', {
  channelId: integer('channel_id').primaryKey(),
  lastPostAt: integer('last_post_at'),
  closeSent: integer('close_sent').notNull().default(0),
  finalSent: integer('final_sent').notNull().default(0),
  lostSent: integer('lost_sent').notNull().default(0),
});

// Separate album updates share this row, even in different invocations.
export const albums = table('albums', {
  id: text('id').primaryKey(),
});
