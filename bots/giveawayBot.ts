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

    const row = new ActionRowBuilder<typeof ButtonBuilder>()
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

    const approvalRow = new ActionRowBuilder<typeof ButtonBuilder>()
      .addComponents(
        new ButtonBuilder()
          .setCustomId('approve_entry')
          .setLabel('Approve Entry')
          .setStyle(ButtonStyle.Success),
        new ButtonBuilder()
          .setCustomId('reject_entry')
          .setLabel('Reject Entry')
          .setStyle(ButtonStyle.Danger)
      );

    await interaction.followUp({ content: `Ticket created: ${ticketChannel}`, components: [approvalRow] });
  }
});

async function checkGiveaways() {}
function parseDuration(duration: string): number { return 0; }
async function someHandler(message: any) {}
async function someInteractionHandler(interaction: any) {}
function errorHandler(error: any) {}