import discord from 'discord.js';
import { logger } from '../services/logger';

const { Client, GatewayIntentBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, PermissionFlagsBits } = discord;

const intents = [
  GatewayIntentBits.Guilds,
  GatewayIntentBits.GuildMessages,
  GatewayIntentBits.MessageContent,
  GatewayIntentBits.GuildMembers,
];

const bot = new Client({ intents });

// Leveling system
const userExp = new Map<string, { exp: number; level: number }>();

function getRequiredExp(level: number): number {
  return 3 * Math.pow(2, level - 1);
}

// Giveaway system
const giveawayData = new Map<string, any>();

bot.once('ready', () => {
  logger.info(`Giveaway & Levels Bot logged in as ${bot.user?.tag}`);
  
  // Start giveaway monitoring
  setInterval(checkGiveaways, 30000); // Check every 30 seconds
});

bot.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  // Leveling system - award XP for messages
  const userId = message.author.id;
  if (!userExp.has(userId)) {
    userExp.set(userId, { exp: 0, level: 1 });
  }

  const userData = userExp.get(userId)!;
  userData.exp += 1;

  while (userData.exp >= getRequiredExp(userData.level)) {
    userData.exp -= getRequiredExp(userData.level);
    userData.level += 1;
    await message.channel.send(`🎉 ${message.author} leveled up to level ${userData.level}!`);
  }

  // Commands
  if (!message.content.startsWith('mul!')) return;

  const args = message.content.slice(4).trim().split(/ +/);
  const command = args.shift()?.toLowerCase();

  if (command === 'check') {
    const user = userExp.get(message.author.id) || { exp: 0, level: 1 };
    await message.channel.send(`${message.author}, Level: ${user.level}, EXP: ${user.exp} / ${getRequiredExp(user.level)}`);
  }

  if (command === 'lb') {
    const sorted = Array.from(userExp.entries())
      .sort(([, a], [, b]) => b.level - a.level || b.exp - a.exp)
      .slice(0, 10);

    let description = '';
    for (let i = 0; i < sorted.length; i++) {
      const [userId, data] = sorted[i];
      try {
        const user = await bot.users.fetch(userId);
        description += `**${i + 1}. ${user.username}** - Level ${data.level} (${data.exp} EXP)\n`;
      } catch (error) {
        description += `**${i + 1}. Unknown User** - Level ${data.level} (${data.exp} EXP)\n`;
      }
    }

    const embed = new EmbedBuilder()
      .setTitle('📊 Leaderboard')
      .setDescription(description)
      .setColor(0x00ff00);

    await message.channel.send({ embeds: [embed] });
  }

  if (command === 'giveaways') {
    const headline = args.join(' ');
    const winners = parseInt(args[1]) || 1;
    const duration = args[2] || '1h';

    if (!headline) {
      await message.channel.send('Please provide a giveaway headline. Usage: `mul!giveaways <headline> <winners> <duration>`');
      return;
    }

    const durationMs = parseDuration(duration);
    const endTime = new Date(Date.now() + durationMs);

    const embed = new EmbedBuilder()
      .setTitle('🎉 Giveaway')
      .setDescription(headline)
      .addFields(
        { name: '🎁 Casual', value: 'Anyone can join!', inline: false },
        { name: '💎 Premium', value: 'Requires staff approval', inline: false }
      )
      .setFooter({ text: `Ends at ${endTime.toLocaleString()}` })
      .setColor(0x3498db);

    const row = new ActionRowBuilder<ButtonBuilder>()
      .addComponents(
        new ButtonBuilder()
          .setCustomId('join_casual')
          .setLabel('Join Casual')
          .setStyle(ButtonStyle.Success),
        new ButtonBuilder()
          .setCustomId('join_premium')
          .setLabel('Join Premium')
          .setStyle(ButtonStyle.Primary)
      );

    const giveawayMessage = await message.channel.send({ embeds: [embed], components: [row] });

    giveawayData.set(giveawayMessage.id, {
      casualEntries: [],
      premiumEntries: [],
      endTime,
      winners,
      headline,
      message: giveawayMessage,
    });
  }
});

bot.on('interactionCreate', async (interaction) => {
  if (!interaction.isButton()) return;

  const { customId, user, guild } = interaction;
  const messageId = interaction.message.id;
  const giveaway = giveawayData.get(messageId);

  if (!giveaway) return;

  if (customId === 'join_casual') {
    if (giveaway.casualEntries.includes(user.id)) {
      await interaction.reply({ content: '❌ You already joined the casual giveaway.', ephemeral: true });
      return;
    }
    giveaway.casualEntries.push(user.id);
    await interaction.reply({ content: '✅ Joined casual giveaway!', ephemeral: true });
  }

  if (customId === 'join_premium') {
    const ticketChannel = await guild?.channels.create({
      name: `giveaway-entry-${Math.floor(Math.random() * 9000) + 1000}`,
      type: discord.ChannelType.GuildText,
      permissionOverwrites: [
        {
          id: guild.roles.everyone.id,
          deny: [PermissionFlagsBits.ViewChannel],
        },
        {
          id: user.id,
          allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages],
        },
      ],
      reason: 'Premium giveaway entry',
    });

    await interaction.reply({ content: `📩 A ticket was created: ${ticketChannel}`, ephemeral: true });

    const approvalRow = new ActionRowBuilder<ButtonBuilder>()
      .addComponents(
        new ButtonBuilder()
          .setCustomId(`approve_${messageId}_${user.id}_${ticketChannel?.id}`)
          .setLabel('Approve')
          .setStyle(ButtonStyle.Success),
        new ButtonBuilder()
          .setCustomId(`decline_${user.id}_${ticketChannel?.id}`)
          .setLabel('Decline')
          .setStyle(ButtonStyle.Danger)
      );

    await ticketChannel?.send({
      content: `Staff, please review the premium entry by ${user}.`,
      components: [approvalRow],
    });
  }

  if (customId.startsWith('approve_')) {
    const parts = customId.split('_');
    const giveawayId = parts[1];
    const userId = parts[2];
    const channelId = parts[3];

    const giveaway = giveawayData.get(giveawayId);
    if (giveaway) {
      giveaway.premiumEntries.push(userId);
      await interaction.reply({ content: `✅ Approved <@${userId}>` });
    }

    const channel = guild?.channels.cache.get(channelId);
    await channel?.delete();
  }

  if (customId.startsWith('decline_')) {
    const parts = customId.split('_');
    const userId = parts[1];
    const channelId = parts[2];

    await interaction.reply({ content: `❌ Declined <@${userId}>` });

    const channel = guild?.channels.cache.get(channelId);
    await channel?.delete();
  }
});

async function checkGiveaways() {
  const now = new Date();
  const expired = [];

  for (const [messageId, data] of giveawayData) {
    if (data.endTime <= now) {
      expired.push(messageId);

      const allEntries = [...data.casualEntries, ...data.premiumEntries];
      if (allEntries.length === 0) {
        await data.message.channel.send('🎁 Giveaway ended. No valid entries.');
        continue;
      }

      const winners = [];
      const numWinners = Math.min(allEntries.length, data.winners);
      
      for (let i = 0; i < numWinners; i++) {
        const randomIndex = Math.floor(Math.random() * allEntries.length);
        winners.push(allEntries.splice(randomIndex, 1)[0]);
      }

      const winnerMentions = winners.map(id => `<@${id}>`).join(', ');
      await data.message.channel.send(`🎉 Giveaway Over!\n**${data.headline}**\nWinners: ${winnerMentions}`);
    }
  }

  expired.forEach(id => giveawayData.delete(id));
}

function parseDuration(duration: string): number {
  const match = duration.match(/^(\d+)([hm])$/);
  if (!match) return 3600000; // Default 1 hour

  const value = parseInt(match[1]);
  const unit = match[2];

  return unit === 'h' ? value * 3600000 : value * 60000;
}

bot.on('error', (error) => {
  logger.error('Giveaway & Levels Bot error:', error);
});

bot.on('disconnect', () => {
  logger.warn('Giveaway & Levels Bot disconnected');
});

const token = process.env.BOT_TOKEN || process.env.GIVEAWAY_BOT_TOKEN;
if (!token) {
  logger.error('No bot token provided for Giveaway & Levels Bot');
  process.exit(1);
}

bot.login(token).catch((error) => {
  logger.error('Failed to login Giveaway & Levels Bot:', error);
  process.exit(1);
});
