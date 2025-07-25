"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const discord_js_1 = __importDefault(require("discord.js"));
const logger_1 = require("../services/logger");
const { Client, GatewayIntentBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, PermissionFlagsBits } = discord_js_1.default;
const intents = [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
];
const bot = new Client({ intents });
// Leveling system
const userExp = new Map();
function getRequiredExp(level) {
    return 3 * Math.pow(2, level - 1);
}
// Giveaway system
const giveawayData = new Map();
bot.once('ready', () => {
    var _a;
    logger_1.logger.info(`Giveaway & Levels Bot logged in as ${(_a = bot.user) === null || _a === void 0 ? void 0 : _a.tag}`);
    // Start giveaway monitoring
    setInterval(checkGiveaways, 30000); // Check every 30 seconds
});
bot.on('messageCreate', (message) => __awaiter(void 0, void 0, void 0, function* () {
    var _a;
    if (message.author.bot)
        return;
    // Leveling system - award XP for messages
    const userId = message.author.id;
    if (!userExp.has(userId)) {
        userExp.set(userId, { exp: 0, level: 1 });
    }
    const userData = userExp.get(userId);
    userData.exp += 1;
    while (userData.exp >= getRequiredExp(userData.level)) {
        userData.exp -= getRequiredExp(userData.level);
        userData.level += 1;
        yield message.channel.send(`🎉 ${message.author} leveled up to level ${userData.level}!`);
    }
    // Commands
    if (!message.content.startsWith('mul!'))
        return;
    const args = message.content.slice(4).trim().split(/ +/);
    const command = (_a = args.shift()) === null || _a === void 0 ? void 0 : _a.toLowerCase();
    if (command === 'check') {
        const user = userExp.get(message.author.id) || { exp: 0, level: 1 };
        yield message.channel.send(`${message.author}, Level: ${user.level}, EXP: ${user.exp} / ${getRequiredExp(user.level)}`);
    }
    if (command === 'lb') {
        const sorted = Array.from(userExp.entries())
            .sort(([, a], [, b]) => b.level - a.level || b.exp - a.exp)
            .slice(0, 10);
        let description = '';
        for (let i = 0; i < sorted.length; i++) {
            const [userId, data] = sorted[i];
            try {
                const user = yield bot.users.fetch(userId);
                description += `**${i + 1}. ${user.username}** - Level ${data.level} (${data.exp} EXP)\n`;
            }
            catch (error) {
                description += `**${i + 1}. Unknown User** - Level ${data.level} (${data.exp} EXP)\n`;
            }
        }
        const embed = new EmbedBuilder()
            .setTitle('📊 Leaderboard')
            .setDescription(description)
            .setColor(0x00ff00);
        yield message.channel.send({ embeds: [embed] });
    }
    if (command === 'giveaways') {
        const headline = args.join(' ');
        const winners = parseInt(args[1]) || 1;
        const duration = args[2] || '1h';
        if (!headline) {
            yield message.channel.send('Please provide a giveaway headline. Usage: `mul!giveaways <headline> <winners> <duration>`');
            return;
        }
        const durationMs = parseDuration(duration);
        const endTime = new Date(Date.now() + durationMs);
        const embed = new EmbedBuilder()
            .setTitle('🎉 Giveaway')
            .setDescription(headline)
            .addFields({ name: '🎁 Casual', value: 'Anyone can join!', inline: false }, { name: '💎 Premium', value: 'Requires staff approval', inline: false })
            .setFooter({ text: `Ends at ${endTime.toLocaleString()}` })
            .setColor(0x3498db);
        const row = new ActionRowBuilder()
            .addComponents(new ButtonBuilder()
            .setCustomId('join_casual')
            .setLabel('Join Casual')
            .setStyle(ButtonStyle.Success), new ButtonBuilder()
            .setCustomId('join_premium')
            .setLabel('Join Premium')
            .setStyle(ButtonStyle.Primary));
        const giveawayMessage = yield message.channel.send({ embeds: [embed], components: [row] });
        giveawayData.set(giveawayMessage.id, {
            casualEntries: [],
            premiumEntries: [],
            endTime,
            winners,
            headline,
            message: giveawayMessage,
        });
    }
}));
bot.on('interactionCreate', (interaction) => __awaiter(void 0, void 0, void 0, function* () {
    if (!interaction.isButton())
        return;
    const { customId, user, guild } = interaction;
    const messageId = interaction.message.id;
    const giveaway = giveawayData.get(messageId);
    if (!giveaway)
        return;
    if (customId === 'join_casual') {
        if (giveaway.casualEntries.includes(user.id)) {
            yield interaction.reply({ content: '❌ You already joined the casual giveaway.', ephemeral: true });
            return;
        }
        giveaway.casualEntries.push(user.id);
        yield interaction.reply({ content: '✅ Joined casual giveaway!', ephemeral: true });
    }
    if (customId === 'join_premium') {
        const ticketChannel = yield (guild === null || guild === void 0 ? void 0 : guild.channels.create({
            name: `giveaway-entry-${Math.floor(Math.random() * 9000) + 1000}`,
            type: discord_js_1.default.ChannelType.GuildText,
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
        }));
        yield interaction.reply({ content: `📩 A ticket was created: ${ticketChannel}`, ephemeral: true });
        const approvalRow = new ActionRowBuilder()
            .addComponents(new ButtonBuilder()
            .setCustomId(`approve_${messageId}_${user.id}_${ticketChannel === null || ticketChannel === void 0 ? void 0 : ticketChannel.id}`)
            .setLabel('Approve')
            .setStyle(ButtonStyle.Success), new ButtonBuilder()
            .setCustomId(`decline_${user.id}_${ticketChannel === null || ticketChannel === void 0 ? void 0 : ticketChannel.id}`)
            .setLabel('Decline')
            .setStyle(ButtonStyle.Danger));
        yield (ticketChannel === null || ticketChannel === void 0 ? void 0 : ticketChannel.send({
            content: `Staff, please review the premium entry by ${user}.`,
            components: [approvalRow],
        }));
    }
    if (customId.startsWith('approve_')) {
        const parts = customId.split('_');
        const giveawayId = parts[1];
        const userId = parts[2];
        const channelId = parts[3];
        const giveaway = giveawayData.get(giveawayId);
        if (giveaway) {
            giveaway.premiumEntries.push(userId);
            yield interaction.reply({ content: `✅ Approved <@${userId}>` });
        }
        const channel = guild === null || guild === void 0 ? void 0 : guild.channels.cache.get(channelId);
        yield (channel === null || channel === void 0 ? void 0 : channel.delete());
    }
    if (customId.startsWith('decline_')) {
        const parts = customId.split('_');
        const userId = parts[1];
        const channelId = parts[2];
        yield interaction.reply({ content: `❌ Declined <@${userId}>` });
        const channel = guild === null || guild === void 0 ? void 0 : guild.channels.cache.get(channelId);
        yield (channel === null || channel === void 0 ? void 0 : channel.delete());
    }
}));
function checkGiveaways() {
    return __awaiter(this, void 0, void 0, function* () {
        const now = new Date();
        const expired = [];
        for (const [messageId, data] of giveawayData) {
            if (data.endTime <= now) {
                expired.push(messageId);
                const allEntries = [...data.casualEntries, ...data.premiumEntries];
                if (allEntries.length === 0) {
                    yield data.message.channel.send('🎁 Giveaway ended. No valid entries.');
                    continue;
                }
                const winners = [];
                const numWinners = Math.min(allEntries.length, data.winners);
                for (let i = 0; i < numWinners; i++) {
                    const randomIndex = Math.floor(Math.random() * allEntries.length);
                    winners.push(allEntries.splice(randomIndex, 1)[0]);
                }
                const winnerMentions = winners.map(id => `<@${id}>`).join(', ');
                yield data.message.channel.send(`🎉 Giveaway Over!\n**${data.headline}**\nWinners: ${winnerMentions}`);
            }
        }
        expired.forEach(id => giveawayData.delete(id));
    });
}
function parseDuration(duration) {
    const match = duration.match(/^(\d+)([hm])$/);
    if (!match)
        return 3600000; // Default 1 hour
    const value = parseInt(match[1]);
    const unit = match[2];
    return unit === 'h' ? value * 3600000 : value * 60000;
}
bot.on('error', (error) => {
    logger_1.logger.error('Giveaway & Levels Bot error:', error);
});
bot.on('disconnect', () => {
    logger_1.logger.warn('Giveaway & Levels Bot disconnected');
});
const token = process.env.BOT_TOKEN || process.env.GIVEAWAY_BOT_TOKEN;
if (!token) {
    logger_1.logger.error('No bot token provided for Giveaway & Levels Bot');
    process.exit(1);
}
bot.login(token).catch((error) => {
    logger_1.logger.error('Failed to login Giveaway & Levels Bot:', error);
    process.exit(1);
});
