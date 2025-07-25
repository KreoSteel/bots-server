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
const { Client, GatewayIntentBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder, StringSelectMenuOptionBuilder, PermissionFlagsBits } = discord_js_1.default;
const intents = [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
];
const bot = new Client({ intents });
const CATEGORY_ID = '1397234544368685269';
const ALS_ROLE_ID = '1397023739631108188';
const ASTDX_ROLE_ID = '1382679356975087647';
const PROMOTION_ROLE_ID = '1397185106975920138';
const LOG_CHANNEL_ID = '1397579436274090035';
const STAFF_ROLE_ID = '1397186487044411522';
let ticketCounter = 0;
const activeTickets = new Map();
const staffRatings = new Map();
bot.once('ready', () => {
    var _a;
    logger_1.logger.info(`Ticket Bot logged in as ${(_a = bot.user) === null || _a === void 0 ? void 0 : _a.tag}`);
});
bot.on('messageCreate', (message) => __awaiter(void 0, void 0, void 0, function* () {
    var _a;
    if (message.author.bot)
        return;
    if (!message.content.startsWith('dio!'))
        return;
    const args = message.content.slice(4).trim().split(/ +/);
    const command = (_a = args.shift()) === null || _a === void 0 ? void 0 : _a.toLowerCase();
    if (command === 'ticketboard') {
        const selectMenu = new StringSelectMenuBuilder()
            .setCustomId('ticket_type_select')
            .setPlaceholder('Ticket Selector')
            .addOptions(new StringSelectMenuOptionBuilder()
            .setLabel('ALS')
            .setDescription('Open a ticket for ALS Staff')
            .setValue('als'), new StringSelectMenuOptionBuilder()
            .setLabel('ASTDX')
            .setDescription('Open a ticket for ASTDX Staffs')
            .setValue('astdx'));
        const row = new ActionRowBuilder()
            .addComponents(selectMenu);
        yield message.channel.send({ content: '🎫 Select a ticket type below:', components: [row] });
    }
    if (command === 'staffratings') {
        if (staffRatings.size === 0) {
            yield message.reply('No ratings yet.');
            return;
        }
        const embed = new EmbedBuilder()
            .setTitle('⭐ Staff Ratings')
            .setColor(0x00ff00);
        for (const [staffId, ratings] of staffRatings) {
            try {
                const user = yield bot.users.fetch(staffId);
                const avg = ratings.reduce((sum, rating) => sum + rating, 0) / ratings.length;
                embed.addFields({
                    name: user.username,
                    value: `${ratings.length} ratings | Avg: ${avg.toFixed(2)}⭐`,
                    inline: false,
                });
            }
            catch (error) {
                embed.addFields({
                    name: 'Unknown User',
                    value: `${ratings.length} ratings | Avg: ${(ratings.reduce((sum, rating) => sum + rating, 0) / ratings.length).toFixed(2)}⭐`,
                    inline: false,
                });
            }
        }
        yield message.channel.send({ embeds: [embed] });
    }
}));
bot.on('interactionCreate', (interaction) => __awaiter(void 0, void 0, void 0, function* () {
    var _a, _b;
    if (interaction.isStringSelectMenu() && interaction.customId === 'ticket_type_select') {
        const ticketType = interaction.values[0];
        ticketCounter++;
        const ticketName = `${ticketType}-ticket-${ticketCounter.toString().padStart(4, '0')}`;
        const guild = interaction.guild;
        const category = guild === null || guild === void 0 ? void 0 : guild.channels.cache.get(CATEGORY_ID);
        const helpersRole = guild === null || guild === void 0 ? void 0 : guild.roles.cache.get(STAFF_ROLE_ID);
        try {
            const ticketChannel = yield (guild === null || guild === void 0 ? void 0 : guild.channels.create({
                name: ticketName,
                type: discord_js_1.default.ChannelType.GuildText,
                parent: category === null || category === void 0 ? void 0 : category.id,
                permissionOverwrites: [
                    {
                        id: guild.roles.everyone.id,
                        deny: [PermissionFlagsBits.ViewChannel],
                    },
                    {
                        id: interaction.user.id,
                        allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.AttachFiles, PermissionFlagsBits.EmbedLinks],
                    },
                    {
                        id: (helpersRole === null || helpersRole === void 0 ? void 0 : helpersRole.id) || '',
                        allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages],
                    },
                ],
            }));
            activeTickets.set((ticketChannel === null || ticketChannel === void 0 ? void 0 : ticketChannel.id) || '', {
                creatorId: interaction.user.id,
                staffId: null,
            });
            const controlRow = new ActionRowBuilder()
                .addComponents(new ButtonBuilder()
                .setCustomId(`take_request_${interaction.user.id}`)
                .setLabel('🎯 Take Request')
                .setStyle(ButtonStyle.Primary), new ButtonBuilder()
                .setCustomId(`delete_ticket_${interaction.user.id}`)
                .setLabel('🗑️ Delete Ticket')
                .setStyle(ButtonStyle.Danger));
            const roleId = ticketType === 'als' ? ALS_ROLE_ID : ASTDX_ROLE_ID;
            const staffRole = guild === null || guild === void 0 ? void 0 : guild.roles.cache.get(roleId);
            yield (ticketChannel === null || ticketChannel === void 0 ? void 0 : ticketChannel.send({
                content: `${interaction.user} has opened a **${ticketType.toUpperCase()}** support ticket!\n${staffRole || ''}`,
                components: [controlRow],
            }));
            yield interaction.reply({ content: `✅ Your ticket has been created: ${ticketChannel}`, ephemeral: true });
        }
        catch (error) {
            logger_1.logger.error('Error creating ticket:', error);
            yield interaction.reply({ content: 'Failed to create ticket.', ephemeral: true });
        }
    }
    if (interaction.isButton()) {
        const { customId, user, guild, channel } = interaction;
        if (customId.startsWith('take_request_')) {
            const creatorId = customId.split('_')[2];
            const ticketData = activeTickets.get((channel === null || channel === void 0 ? void 0 : channel.id) || '');
            if (!ticketData) {
                yield interaction.reply({ content: '⚠️ Internal error.', ephemeral: true });
                return;
            }
            if (ticketData.staffId !== null) {
                yield interaction.reply({ content: '❌ This request has already been taken.', ephemeral: true });
                return;
            }
            if (user.id === creatorId) {
                yield interaction.reply({ content: '❌ You cannot take your own request.', ephemeral: true });
                return;
            }
            ticketData.staffId = user.id;
            yield (channel === null || channel === void 0 ? void 0 : channel.send(`✅ This request has been taken by ${user}.`));
            yield interaction.reply({ content: '🎯 You claimed this request!', ephemeral: true });
            // Disable the button
            const newRow = new ActionRowBuilder()
                .addComponents(new ButtonBuilder()
                .setCustomId(`take_request_${creatorId}`)
                .setLabel('🎯 Take Request')
                .setStyle(ButtonStyle.Primary)
                .setDisabled(true), new ButtonBuilder()
                .setCustomId(`delete_ticket_${creatorId}`)
                .setLabel('🗑️ Delete Ticket')
                .setStyle(ButtonStyle.Danger));
            yield interaction.message.edit({ components: [newRow] });
        }
        if (customId.startsWith('delete_ticket_')) {
            const creatorId = customId.split('_')[2];
            if (user.id !== creatorId) {
                yield interaction.reply({ content: '❌ Only the ticket creator can delete this ticket.', ephemeral: true });
                return;
            }
            const ticketData = activeTickets.get((channel === null || channel === void 0 ? void 0 : channel.id) || '');
            if (!(ticketData === null || ticketData === void 0 ? void 0 : ticketData.staffId)) {
                yield (channel === null || channel === void 0 ? void 0 : channel.delete());
                return;
            }
            // Show rating system
            const ratingRow = new ActionRowBuilder();
            for (let i = 1; i <= 5; i++) {
                ratingRow.addComponents(new ButtonBuilder()
                    .setCustomId(`rate_${i}_${ticketData.staffId}_${channel === null || channel === void 0 ? void 0 : channel.id}_${user.id}`)
                    .setLabel(`${i} ⭐`)
                    .setStyle(ButtonStyle.Secondary));
            }
            yield interaction.reply({ content: 'Please rate the support you received:', components: [ratingRow], ephemeral: true });
        }
        if (customId.startsWith('rate_')) {
            const parts = customId.split('_');
            const rating = parseInt(parts[1]);
            const staffId = parts[2];
            const channelId = parts[3];
            const raterId = parts[4];
            if (user.id !== raterId)
                return;
            // Add rating
            if (!staffRatings.has(staffId)) {
                staffRatings.set(staffId, []);
            }
            (_a = staffRatings.get(staffId)) === null || _a === void 0 ? void 0 : _a.push(rating);
            yield interaction.reply({ content: `✅ You rated ${rating} stars!`, ephemeral: true });
            // Log the rating
            const logChannel = guild === null || guild === void 0 ? void 0 : guild.channels.cache.get(LOG_CHANNEL_ID);
            if (logChannel && logChannel.isTextBased()) {
                const rater = guild === null || guild === void 0 ? void 0 : guild.members.cache.get(raterId);
                const staff = guild === null || guild === void 0 ? void 0 : guild.members.cache.get(staffId);
                yield logChannel.send(`⭐ **Rating**: \`${rating} stars\`\n👤 From: ${rater}\n🎯 To: ${staff}`);
            }
            // Check for promotion
            if (rating === 5) {
                const fiveStarCount = ((_b = staffRatings.get(staffId)) === null || _b === void 0 ? void 0 : _b.filter(r => r === 5).length) || 0;
                if (fiveStarCount === 15) {
                    const staffMember = guild === null || guild === void 0 ? void 0 : guild.members.cache.get(staffId);
                    const promotionRole = guild === null || guild === void 0 ? void 0 : guild.roles.cache.get(PROMOTION_ROLE_ID);
                    if (staffMember && promotionRole && !staffMember.roles.cache.has(PROMOTION_ROLE_ID)) {
                        yield staffMember.roles.add(promotionRole);
                        const logChannel = guild === null || guild === void 0 ? void 0 : guild.channels.cache.get(LOG_CHANNEL_ID);
                        if (logChannel && logChannel.isTextBased()) {
                            yield logChannel.send(`🎉 ${staffMember} has been promoted with 15 five-star ratings!`);
                        }
                    }
                }
            }
            // Delete the ticket
            const ticketChannel = guild === null || guild === void 0 ? void 0 : guild.channels.cache.get(channelId);
            yield (ticketChannel === null || ticketChannel === void 0 ? void 0 : ticketChannel.delete());
        }
    }
}));
bot.on('error', (error) => {
    logger_1.logger.error('Ticket Bot error:', error);
});
bot.on('disconnect', () => {
    logger_1.logger.warn('Ticket Bot disconnected');
});
const token = process.env.BOT_TOKEN || process.env.TICKET_BOT_TOKEN;
if (!token) {
    logger_1.logger.error('No bot token provided for Ticket Bot');
    process.exit(1);
}
bot.login(token).catch((error) => {
    logger_1.logger.error('Failed to login Ticket Bot:', error);
    process.exit(1);
});
