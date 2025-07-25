import discord from 'discord.js';
import { logger } from '../services/logger';

const { Client, GatewayIntentBits, EmbedBuilder } = discord;

const intents = [
  GatewayIntentBits.Guilds,
  GatewayIntentBits.GuildMessages,
  GatewayIntentBits.MessageContent,
  GatewayIntentBits.GuildMembers,
  GatewayIntentBits.GuildInvites,
];

const bot = new Client({ intents });

// Store invite data
const inviteData = new Map<string, number>(); // userId -> invite count
const guildInvites = new Map<string, Map<string, number>>(); // guildId -> Map<inviteCode, uses>

bot.once('ready', async () => {
  logger.info(`Invites Tracker Bot logged in as ${bot.user?.tag}`);
  
  // Cache invites for all guilds
  for (const guild of bot.guilds.cache.values()) {
    try {
      const invites = await guild.invites.fetch();
      const inviteMap = new Map<string, number>();
      
      for (const invite of invites.values()) {
        inviteMap.set(invite.code, invite.uses || 0);
      }
      
      guildInvites.set(guild.id, inviteMap);
    } catch (error) {
      logger.error(`Failed to fetch invites for guild ${guild.name}:`, error);
    }
  }
});

bot.on('guildCreate', async (guild) => {
  try {
    const invites = await guild.invites.fetch();
    const inviteMap = new Map<string, number>();
    
    for (const invite of invites.values()) {
      inviteMap.set(invite.code, invite.uses || 0);
    }
    
    guildInvites.set(guild.id, inviteMap);
  } catch (error) {
    logger.error(`Failed to fetch invites for new guild ${guild.name}:`, error);
  }
});

bot.on('guildMemberAdd', async (member) => {
  try {
    const invitesBefore = guildInvites.get(member.guild.id) || new Map();
    const invitesAfter = await member.guild.invites.fetch();

    let usedInvite = null;
    for (const invite of invitesAfter.values()) {
      const beforeUses = invitesBefore.get(invite.code) || 0;
      if (invite.uses && invite.uses > beforeUses) {
        usedInvite = invite;
        break;
      }
    }

    if (usedInvite && usedInvite.inviter) {
      const inviterId = usedInvite.inviter.id;
      const currentCount = inviteData.get(inviterId) || 0;
      inviteData.set(inviterId, currentCount + 1);

      logger.info(`${member.user.username} was invited by ${usedInvite.inviter.username}`);
    }

    // Update cached invites
    const newInviteMap = new Map<string, number>();
    for (const invite of invitesAfter.values()) {
      newInviteMap.set(invite.code, invite.uses || 0);
    }
    guildInvites.set(member.guild.id, newInviteMap);

  } catch (error) {
    logger.error('Error tracking member join:', error);
  }
});

bot.on('guildMemberRemove', async (member) => {
  try {
    const invitesBefore = guildInvites.get(member.guild.id) || new Map();
    const invitesAfter = await member.guild.invites.fetch();

    let usedInvite = null;
    for (const invite of invitesAfter.values()) {
      const beforeUses = invitesBefore.get(invite.code) || 0;
      if (invite.uses !== undefined && invite.uses < beforeUses) {
        usedInvite = invite;
        break;
      }
    }

    if (usedInvite && usedInvite.inviter) {
      const inviterId = usedInvite.inviter.id;
      const currentCount = inviteData.get(inviterId) || 0;
      inviteData.set(inviterId, Math.max(0, currentCount - 1));
    }

    // Update cached invites
    const newInviteMap = new Map<string, number>();
    for (const invite of invitesAfter.values()) {
      newInviteMap.set(invite.code, invite.uses || 0);
    }
    guildInvites.set(member.guild.id, newInviteMap);

  } catch (error) {
    logger.error('Error tracking member leave:', error);
  }
});

bot.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith('inv!')) return;

  const args = message.content.slice(4).trim().split(/ +/);
  const command = args.shift()?.toLowerCase();

  if (command === 'add') {
    if (!message.member?.permissions.has('ManageGuild')) {
      await message.reply('❌ You need Manage Server permission to use this command.');
      return;
    }

    const member = message.mentions.members?.first();
    const points = parseInt(args[1]);

    if (!member || isNaN(points)) {
      await message.reply('Usage: `inv!add @member <points>`');
      return;
    }

    const currentCount = inviteData.get(member.id) || 0;
    inviteData.set(member.id, currentCount + points);

    await message.reply(`✅ Added ${points} points to ${member.displayName}.`);
  }

  if (command === 'remove') {
    if (!message.member?.permissions.has('ManageGuild')) {
      await message.reply('❌ You need Manage Server permission to use this command.');
      return;
    }

    const member = message.mentions.members?.first();
    const points = parseInt(args[1]);

    if (!member || isNaN(points)) {
      await message.reply('Usage: `inv!remove @member <points>`');
      return;
    }

    const currentCount = inviteData.get(member.id) || 0;
    inviteData.set(member.id, Math.max(0, currentCount - points));

    await message.reply(`❌ Removed ${points} points from ${member.displayName}.`);
  }

  if (command === 'lb') {
    const sorted = Array.from(inviteData.entries())
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10);

    let description = '';
    for (let i = 0; i < sorted.length; i++) {
      const [userId, points] = sorted[i];
      try {
        const user = await bot.users.fetch(userId);
        description += `**${i + 1}.** ${user.username} - **${points} invites**\n`;
      } catch (error) {
        description += `**${i + 1}.** Unknown User - **${points} invites**\n`;
      }
    }

    if (!description) {
      description = 'No invite data available yet.';
    }

    const embed = new EmbedBuilder()
      .setTitle('🏆 Invite Leaderboard')
      .setDescription(description)
      .setColor(0x00ff00);

    await message.channel.send({ embeds: [embed] });
  }
});

bot.on('error', (error) => {
  logger.error('Invites Tracker Bot error:', error);
});

bot.on('disconnect', () => {
  logger.warn('Invites Tracker Bot disconnected');
});

const token = process.env.BOT_TOKEN || process.env.INVITES_BOT_TOKEN;
if (!token) {
  logger.error('No bot token provided for Invites Tracker Bot');
  process.exit(1);
}

bot.login(token).catch((error) => {
  logger.error('Failed to login Invites Tracker Bot:', error);
  process.exit(1);
});
