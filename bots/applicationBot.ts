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

const ASTDX_ROLE_ID = '1382679356975087647';
const ALS_ROLE_ID = '1397023739631108188';
const CATEGORY_ID = '1397234544368685269';
const STAFF_ROLE_ID = '1397186487044411522';

let application_counter = {
  "astdx": 1,
  "als": 1,
  "all": 1
};

const form_message = (
  "Welcome! We are glad that you want to become our important part - Helpers, but we need to clarify that you could do it or not.\n\n" +
  "**1. Respect**\n" +
  "- You must respect people, but if they don't respect or are not grateful for your help, please make a report with proofs.\n\n" +
  "**2. Choices**\n" +
  "- You can choose what requests you want to do. If you see a request you can't handle, pass it to someone else.\n\n" +
  "**3. Ratings**\n" +
  "- After finishing the request, ask them to click 'Delete Ticket' and a rating board will appear. With enough 5-star ratings, you can join special giveaways!"
);

bot.once('ready', () => {
  logger.info(`Application Bot logged in as ${bot.user?.tag}`);
});

bot.on('interactionCreate', async (interaction) => {
  if (!interaction.isButton()) return;

  const { customId, user, guild } = interaction;

  if (customId.startsWith('apply_')) {
    const appType = customId.split('_')[1];
    const category = guild?.channels.cache.get(CATEGORY_ID);

    const number = application_counter[appType as keyof typeof application_counter];
    application_counter[appType as keyof typeof application_counter] += 1;

    const channelName = `${appType}-application-${number.toString().padStart(4, '0')}`;
    
    try {
      const channel = await guild?.channels.create({
        name: channelName,
        type: discord.ChannelType.GuildText,
        parent: category?.id,
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
      });

      await interaction.reply({ content: `✅ Application created: ${channel}`, ephemeral: true });

      await channel?.send(`${user}\n${form_message}`);

      const row = new ActionRowBuilder<ButtonBuilder>()
        .addComponents(
          new ButtonBuilder()
            .setCustomId(`accept_${appType}_${user.id}`)
            .setLabel('✅ Accept')
            .setStyle(ButtonStyle.Success),
          new ButtonBuilder()
            .setCustomId(`reject_${user.id}`)
            .setLabel('❌ Reject')
            .setStyle(ButtonStyle.Danger),
          new ButtonBuilder()
            .setCustomId(`delete_${channel?.id}_${user.id}`)
            .setLabel('🗑️ Delete Ticket')
            .setStyle(ButtonStyle.Danger)
        );

      await channel?.send({ content: 'Staff controls:', components: [row] });
    } catch (error) {
      logger.error('Error creating application channel:', error);
      await interaction.reply({ content: 'Failed to create application channel.', ephemeral: true });
    }
  }

  if (customId.startsWith('accept_')) {
    const parts = customId.split('_');
    const appType = parts[1];
    const userId = parts[2];

    const member = guild?.members.cache.get(userId);
    if (!member) return;

    const roles = [];
    if (appType === 'astdx') {
      roles.push(ASTDX_ROLE_ID);
    } else if (appType === 'als') {
      roles.push(ALS_ROLE_ID);
    } else if (appType === 'all') {
      roles.push(ALS_ROLE_ID, ASTDX_ROLE_ID);
    }

    try {
      for (const roleId of roles) {
        const role = guild?.roles.cache.get(roleId);
        if (role) await member.roles.add(role);
      }

      await interaction.reply({ content: `✅ ${member} has been accepted and given roles.`, ephemeral: true });
    } catch (error) {
      logger.error('Error adding roles:', error);
    }
  }

  if (customId.startsWith('reject_')) {
    const userId = customId.split('_')[1];
    const member = guild?.members.cache.get(userId);
    await interaction.reply({ content: `❌ ${member}'s application was rejected.`, ephemeral: true });
  }

  if (customId.startsWith('delete_')) {
    const channelId = customId.split('_')[1];
    const channel = guild?.channels.cache.get(channelId);
    
    await interaction.reply({ content: 'This ticket will be deleted in 5 seconds...', ephemeral: true });
    setTimeout(async () => {
      try {
        await channel?.delete();
      } catch (error) {
        logger.error('Error deleting channel:', error);
      }
    }, 5000);
  }
});

// Application command
bot.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.startsWith('app!')) return;

  const args = message.content.slice(4).trim().split(/ +/);
  const command = args.shift()?.toLowerCase();

  if (command === 'application') {
    const row = new ActionRowBuilder<ButtonBuilder>()
      .addComponents(
        new ButtonBuilder()
          .setCustomId('apply_astdx')
          .setLabel('Apply on ASTDX')
          .setStyle(ButtonStyle.Primary),
        new ButtonBuilder()
          .setCustomId('apply_als')
          .setLabel('Apply on ALS')
          .setStyle(ButtonStyle.Primary),
        new ButtonBuilder()
          .setCustomId('apply_all')
          .setLabel('Apply All')
          .setStyle(ButtonStyle.Primary)
      );

    await message.channel.send({ content: 'Click a button below to apply:', components: [row] });
  }

  if (command === 'rules') {
    const embed1 = new EmbedBuilder()
      .setTitle('📜 AVS Server Rules & Guidelines')
      .setDescription(
        "**Welcome to AVS — a fun community for ALS, ASTDX, and chill chats!**\n\n" +
        "**🌟 1. Respect & Kindness**\n" +
        "• Be respectful to everyone.\n" +
        "• No harassment, hate, threats, or toxic behavior — jokes are fine, but not harmful ones.\n" +
        "• If someone bothers you, don't retaliate — report them.\n\n" +
        "**📢 2. Language & Behavior**\n" +
        "• Keep chats appropriate for all ages.\n" +
        "• Swearing is okay in moderation — no slurs or hate speech.\n" +
        "• No spam, flooding, mass pings.\n\n" +
        "**📌 3. Use the Right Channels**\n" +
        "• Chat in general, memes in #memes, help in #support, etc.\n\n" +
        "**🧠 4. Content Rules**\n" +
        "• No NSFW/NSFL, illegal, pirated, or disturbing content.\n\n" +
        "**🚫 5. Alts & Raids**\n" +
        "• No alts unless approved. Trolls = instant ban.\n\n" +
        "**✅ Final:**\n" +
        "• No disrespect to helpers. Major = ban. Minor = mute.\n"
      )
      .setColor(0x0099ff);

    const nextButton = new ActionRowBuilder<ButtonBuilder>()
      .addComponents(
        new ButtonBuilder()
          .setCustomId(`rules_next_${message.author.id}`)
          .setLabel('Next ▶️')
          .setStyle(ButtonStyle.Primary),
        new ButtonBuilder()
          .setCustomId(`rules_back_${message.author.id}`)
          .setLabel('◀️ Back')
          .setStyle(ButtonStyle.Secondary)
          .setDisabled(true)
      );

    await message.channel.send({ embeds: [embed1], components: [nextButton] });
  }
});

// Handle rules pagination
bot.on('interactionCreate', async (interaction) => {
  if (!interaction.isButton()) return;

  const { customId, user } = interaction;

  if (customId.startsWith('rules_next_')) {
    const userId = customId.split('_')[2];
    if (user.id !== userId) {
      await interaction.reply({ content: '🚫 You don\'t have permission to use this button.', ephemeral: true });
      return;
    }

    const member = interaction.guild?.members.cache.get(userId);
    const staffRole = interaction.guild?.roles.cache.get(STAFF_ROLE_ID);
    
    if (staffRole && member?.roles.cache.has(STAFF_ROLE_ID)) {
      const embed2 = new EmbedBuilder()
        .setTitle('👮 Staff Guide')
        .setDescription(
          "• **Take Requests:** When a ticket appears, check what the member needs. If you're confident you can help, press **TAKE REQUEST**.\n\n" +
          "• **Deletion & Ratings:** After completing the request, ask the member to press **DELETE TICKET** to leave a rating.\n\n" +
          "• **Choices:** You don't have to take every ticket. Only take the ones you can handle.\n\n" +
          "• **Respect:** Always respect members. If someone disrespects you, stop helping and report it.\n\n" +
          "• **Benefits:** Staff can join exclusive giveaways and perks."
        )
        .setColor(0xff0000);

      const backButton = new ActionRowBuilder<ButtonBuilder>()
        .addComponents(
          new ButtonBuilder()
            .setCustomId(`rules_next_${userId}`)
            .setLabel('Next ▶️')
            .setStyle(ButtonStyle.Primary)
            .setDisabled(true),
          new ButtonBuilder()
            .setCustomId(`rules_back_${userId}`)
            .setLabel('◀️ Back')
            .setStyle(ButtonStyle.Secondary)
        );

      await interaction.update({ embeds: [embed2], components: [backButton] });
    } else {
      await interaction.reply({ content: '🚫 You don\'t have permission to view this page.', ephemeral: true });
    }
  }

  if (customId.startsWith('rules_back_')) {
    const userId = customId.split('_')[2];
    if (user.id !== userId) return;

    const embed1 = new EmbedBuilder()
      .setTitle('📜 AVS Server Rules & Guidelines')
      .setDescription(
        "**Welcome to AVS — a fun community for ALS, ASTDX, and chill chats!**\n\n" +
        "**🌟 1. Respect & Kindness**\n" +
        "• Be respectful to everyone.\n" +
        "• No harassment, hate, threats, or toxic behavior — jokes are fine, but not harmful ones.\n" +
        "• If someone bothers you, don't retaliate — report them.\n\n" +
        "**📢 2. Language & Behavior**\n" +
        "• Keep chats appropriate for all ages.\n" +
        "• Swearing is okay in moderation — no slurs or hate speech.\n" +
        "• No spam, flooding, mass pings.\n\n" +
        "**📌 3. Use the Right Channels**\n" +
        "• Chat in general, memes in #memes, help in #support, etc.\n\n" +
        "**🧠 4. Content Rules**\n" +
        "• No NSFW/NSFL, illegal, pirated, or disturbing content.\n\n" +
        "**🚫 5. Alts & Raids**\n" +
        "• No alts unless approved. Trolls = instant ban.\n\n" +
        "**✅ Final:**\n" +
        "• No disrespect to helpers. Major = ban. Minor = mute.\n"
      )
      .setColor(0x0099ff);

    const nextButton = new ActionRowBuilder<ButtonBuilder>()
      .addComponents(
        new ButtonBuilder()
          .setCustomId(`rules_next_${userId}`)
          .setLabel('Next ▶️')
          .setStyle(ButtonStyle.Primary),
        new ButtonBuilder()
          .setCustomId(`rules_back_${userId}`)
          .setLabel('◀️ Back')
          .setStyle(ButtonStyle.Secondary)
          .setDisabled(true)
      );

    await interaction.update({ embeds: [embed1], components: [nextButton] });
  }
});

bot.on('error', (error) => {
  logger.error('Application Bot error:', error);
});

bot.on('disconnect', () => {
  logger.warn('Application Bot disconnected');
});

const token = process.env.BOT_TOKEN || process.env.APPLICATION_BOT_TOKEN;
if (!token) {
  logger.error('No bot token provided for Application Bot');
  process.exit(1);
}

bot.login(token).catch((error) => {
  logger.error('Failed to login Application Bot:', error);
  process.exit(1);
});
