const { App } = require('@slack/bolt');
require('dotenv').config();

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  socketMode: true,
  appToken: process.env.SLACK_APP_TOKEN,
});

app.command('/autoreport', async ({ command, ack, respond }) => {
  await ack();
  await respond({
    response_type: 'ephemeral',
    text: 'Generating Auto-Reporter status report...',
  });
  
  // Trigger report generation
  // This would call the Python core module
  const report = `## Daily Status Report
Generated from #${command.channel_name}

*Core module integration pending - connect to packages/core*
`;
  
  await respond({
    response_type: 'ephemeral',
    text: report,
  });
});

app.event('app_mention', async ({ event, say }) => {
  await say(`Hi <@${event.user}>! Use /autoreport to generate a status report.`);
});

(async () => {
  await app.start(process.env.PORT || 3000);
  console.log('⚡️ Auto-Reporter Slack app is running!');
})();
