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
const { Client, GatewayIntentBits, EmbedBuilder } = discord_js_1.default;
const intents = [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildInvites,
];
const bot = new Client({ intents });
// Store invite data
const inviteData = new Map(); // userId -> invite count
const guildInvites = new Map(); // guildId -> Map<inviteCode, uses>
bot.once('ready', () => __awaiter(void 0, void 0, void 0, function* () {
    var _a;
    logger_1.logger.info(`Invites Tracker Bot logged in as ${(_a = bot.user) === null || _a === void 0 ? void 0 : _a.tag}`);
    // Cache invites for all guilds
    for (const guild of bot.guilds.cache.values()) {
        try {
            const invites = yield guild.invites.fetch();
            const inviteMap = new Map();
            for (const invite of invites.values()) {
                inviteMap.set(invite.code, invite.uses || 0);
            }
            guildInvites.set(guild.id, inviteMap);
        }
        catch (error) {
            logger_1.logger.error(`Failed to fetch invites for guild ${guild.name}:`, error);
        }
    }
}));
bot.on('guildCreate', (guild) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        const invites = yield guild.invites.fetch();
        const inviteMap = new Map();
        for (const invite of invites.values()) {
            inviteMap.set(invite.code, invite.uses || 0);
        }
        guildInvites.set(guild.id, inviteMap);
    }
    catch (error) {
        logger_1.logger.error(`Failed to fetch invites for new guild ${guild.name}:`, error);
    }
}));
bot.on('guildMemberAdd', (member) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        const invitesBefore = guildInvites.get(member.guild.id) || new Map();
        const invitesAfter = yield member.guild.invites.fetch();
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
            logger_1.logger.info(`${member.user.username} was invited by ${usedInvite.inviter.username}`);
        }
        // Update cached invites
        const newInviteMap = new Map();
        for (const invite of invitesAfter.values()) {
            newInviteMap.set(invite.code, invite.uses || 0);
        }
        guildInvites.set(member.guild.id, newInviteMap);
    }
    catch (error) {
        logger_1.logger.error('Error tracking member join:', error);
    }
}));
bot.on('guildMemberRemove', (member) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        const invitesBefore = guildInvites.get(member.guild.id) || new Map();
        const invitesAfter = yield member.guild.invites.fetch();
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
        const newInviteMap = new Map();
        for (const invite of invitesAfter.values()) {
            newInviteMap.set(invite.code, invite.uses || 0);
        }
        guildInvites.set(member.guild.id, newInviteMap);
    }
    catch (error) {
        logger_1.logger.error('Error tracking member leave:', error);
    }
}));
bot.on('messageCreate', (message) => __awaiter(void 0, void 0, void 0, function* () {
    var _a, _b, _c, _d, _e;
    if (message.author.bot)
        return;
    if (!message.content.startsWith('inv!'))
        return;
    const args = message.content.slice(4).trim().split(/ +/);
    const command = (_a = args.shift()) === null || _a === void 0 ? void 0 : _a.toLowerCase();
    if (command === 'add') {
        if (!((_b = message.member) === null || _b === void 0 ? void 0 : _b.permissions.has('ManageGuild'))) {
            yield message.reply('❌ You need Manage Server permission to use this command.');
            return;
        }
        const member = (_c = message.mentions.members) === null || _c === void 0 ? void 0 : _c.first();
        const points = parseInt(args[1]);
        if (!member || isNaN(points)) {
            yield message.reply('Usage: `inv!add @member <points>`');
            return;
        }
        const currentCount = inviteData.get(member.id) || 0;
        inviteData.set(member.id, currentCount + points);
        yield message.reply(`✅ Added ${points} points to ${member.displayName}.`);
    }
    if (command === 'remove') {
        if (!((_d = message.member) === null || _d === void 0 ? void 0 : _d.permissions.has('ManageGuild'))) {
            yield message.reply('❌ You need Manage Server permission to use this command.');
            return;
        }
        const member = (_e = message.mentions.members) === null || _e === void 0 ? void 0 : _e.first();
        const points = parseInt(args[1]);
        if (!member || isNaN(points)) {
            yield message.reply('Usage: `inv!remove @member <points>`');
            return;
        }
        const currentCount = inviteData.get(member.id) || 0;
        inviteData.set(member.id, Math.max(0, currentCount - points));
        yield message.reply(`❌ Removed ${points} points from ${member.displayName}.`);
    }
    if (command === 'lb') {
        const sorted = Array.from(inviteData.entries())
            .sort(([, a], [, b]) => b - a)
            .slice(0, 10);
        let description = '';
        for (let i = 0; i < sorted.length; i++) {
            const [userId, points] = sorted[i];
            try {
                const user = yield bot.users.fetch(userId);
                description += `**${i + 1}.** ${user.username} - **${points} invites**\n`;
            }
            catch (error) {
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
        yield message.channel.send({ embeds: [embed] });
    }
}));
bot.on('error', (error) => {
    logger_1.logger.error('Invites Tracker Bot error:', error);
});
bot.on('disconnect', () => {
    logger_1.logger.warn('Invites Tracker Bot disconnected');
});
const token = process.env.BOT_TOKEN || process.env.INVITES_BOT_TOKEN;
if (!token) {
    logger_1.logger.error('No bot token provided for Invites Tracker Bot');
    process.exit(1);
}
bot.login(token).catch((error) => {
    logger_1.logger.error('Failed to login Invites Tracker Bot:', error);
    process.exit(1);
});
