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
exports.botManager = exports.BotManager = void 0;
const child_process_1 = require("child_process");
const storage_1 = require("../storage");
const logger_1 = require("./logger");
const path_1 = __importDefault(require("path"));
class BotManager {
    constructor() {
        this.processes = new Map();
    }
    setBroadcastCallback(callback) {
        this.broadcastCallback = callback;
    }
    broadcast(message) {
        if (this.broadcastCallback) {
            this.broadcastCallback(message);
        }
    }
    initialize() {
        return __awaiter(this, void 0, void 0, function* () {
            logger_1.logger.info("Initializing Bot Manager...");
            // Start monitoring
            this.startMonitoring();
            // Auto-start enabled bots
            const bots = yield storage_1.storage.getAllBots();
            for (const bot of bots) {
                if (bot.isEnabled) {
                    yield this.startBot(bot.id);
                }
            }
        });
    }
    startMonitoring() {
        this.monitoringInterval = setInterval(() => __awaiter(this, void 0, void 0, function* () {
            yield this.updateBotStats();
            yield this.checkBotHealth();
        }), 5000); // Update every 5 seconds
    }
    updateBotStats() {
        return __awaiter(this, void 0, void 0, function* () {
            for (const [botId, botProcess] of Array.from(this.processes.entries())) {
                const uptime = Math.floor((Date.now() - botProcess.startTime.getTime()) / 1000);
                const memoryUsage = Math.floor(Math.random() * 50) + 80; // Simulate memory usage
                const apiRequests = Math.floor(Math.random() * 100) + 50; // Simulate API requests
                yield storage_1.storage.updateBot(botId, {
                    uptime,
                    memoryUsage,
                    apiRequests,
                });
            }
            // Broadcast stats update
            const bots = yield storage_1.storage.getAllBots();
            this.broadcast({
                type: 'stats_update',
                data: bots,
            });
        });
    }
    checkBotHealth() {
        return __awaiter(this, void 0, void 0, function* () {
            for (const [botId, botProcess] of Array.from(this.processes.entries())) {
                if (botProcess.process.killed || botProcess.process.exitCode !== null) {
                    logger_1.logger.warn(`Bot ${botId} appears to have crashed, attempting restart...`);
                    yield this.restartBot(botId);
                }
            }
        });
    }
    startBot(botId) {
        return __awaiter(this, void 0, void 0, function* () {
            var _a, _b;
            try {
                const bot = yield storage_1.storage.getBot(botId);
                if (!bot) {
                    return { success: false, error: "Bot not found" };
                }
                if (this.processes.has(botId)) {
                    return { success: false, error: "Bot is already running" };
                }
                if (!bot.token) {
                    return { success: false, error: "Bot token not configured" };
                }
                logger_1.logger.info(`Starting bot: ${bot.name} (${bot.prefix})`);
                // Determine bot file based on bot name
                const botFile = this.getBotFilePath(bot.name);
                if (!botFile) {
                    return { success: false, error: "Bot implementation not found" };
                }
                // Start the bot process
                const botProcess = (0, child_process_1.spawn)('node', ['-r', 'tsx/esm', botFile], {
                    env: Object.assign(Object.assign({}, process.env), { BOT_TOKEN: bot.token, BOT_ID: botId.toString() }),
                    stdio: ['ignore', 'pipe', 'pipe'],
                });
                const botProcessData = {
                    process: botProcess,
                    startTime: new Date(),
                    restartCount: 0,
                };
                this.processes.set(botId, botProcessData);
                // Handle process output
                (_a = botProcess.stdout) === null || _a === void 0 ? void 0 : _a.on('data', (data) => {
                    const message = data.toString().trim();
                    logger_1.logger.info(`[${bot.name}] ${message}`);
                    this.logBotMessage(botId, 'info', message, 'discord');
                });
                (_b = botProcess.stderr) === null || _b === void 0 ? void 0 : _b.on('data', (data) => {
                    const message = data.toString().trim();
                    logger_1.logger.error(`[${bot.name}] ${message}`);
                    this.logBotMessage(botId, 'error', message, 'discord');
                });
                botProcess.on('exit', (code) => __awaiter(this, void 0, void 0, function* () {
                    logger_1.logger.warn(`Bot ${bot.name} exited with code ${code}`);
                    this.processes.delete(botId);
                    yield storage_1.storage.updateBot(botId, {
                        status: 'offline',
                        pid: null,
                    });
                    this.broadcast({
                        type: 'bot_status',
                        data: { botId, status: 'offline' },
                    });
                    this.logBotMessage(botId, 'warn', `Bot exited with code ${code}`, 'system');
                }));
                // Update bot status
                yield storage_1.storage.updateBot(botId, {
                    status: 'online',
                    pid: botProcess.pid || null,
                    lastRestart: new Date(),
                });
                this.broadcast({
                    type: 'bot_status',
                    data: { botId, status: 'online' },
                });
                this.logBotMessage(botId, 'info', `Bot started successfully`, 'system');
                return { success: true };
            }
            catch (error) {
                logger_1.logger.error(`Failed to start bot ${botId}:`, error);
                return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
            }
        });
    }
    stopBot(botId) {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                const bot = yield storage_1.storage.getBot(botId);
                if (!bot) {
                    return { success: false, error: "Bot not found" };
                }
                const botProcess = this.processes.get(botId);
                if (!botProcess) {
                    return { success: false, error: "Bot is not running" };
                }
                logger_1.logger.info(`Stopping bot: ${bot.name}`);
                // Gracefully terminate the process
                botProcess.process.kill('SIGTERM');
                // Force kill after 5 seconds if still running
                setTimeout(() => {
                    if (!botProcess.process.killed) {
                        botProcess.process.kill('SIGKILL');
                    }
                }, 5000);
                this.processes.delete(botId);
                yield storage_1.storage.updateBot(botId, {
                    status: 'offline',
                    pid: null,
                });
                this.broadcast({
                    type: 'bot_status',
                    data: { botId, status: 'offline' },
                });
                this.logBotMessage(botId, 'info', `Bot stopped manually`, 'system');
                return { success: true };
            }
            catch (error) {
                logger_1.logger.error(`Failed to stop bot ${botId}:`, error);
                return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
            }
        });
    }
    restartBot(botId) {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                const bot = yield storage_1.storage.getBot(botId);
                if (!bot) {
                    return { success: false, error: "Bot not found" };
                }
                logger_1.logger.info(`Restarting bot: ${bot.name}`);
                // Update status to restarting
                yield storage_1.storage.updateBot(botId, { status: 'restarting' });
                this.broadcast({
                    type: 'bot_status',
                    data: { botId, status: 'restarting' },
                });
                // Stop if running
                if (this.processes.has(botId)) {
                    yield this.stopBot(botId);
                    // Wait a moment for cleanup
                    yield new Promise(resolve => setTimeout(resolve, 1000));
                }
                // Start again
                const result = yield this.startBot(botId);
                if (result.success) {
                    this.logBotMessage(botId, 'info', `Bot restarted successfully`, 'system');
                }
                return result;
            }
            catch (error) {
                logger_1.logger.error(`Failed to restart bot ${botId}:`, error);
                return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
            }
        });
    }
    startAllBots() {
        return __awaiter(this, void 0, void 0, function* () {
            const bots = yield storage_1.storage.getAllBots();
            let started = 0;
            let failed = 0;
            for (const bot of bots) {
                if (bot.isEnabled) {
                    const result = yield this.startBot(bot.id);
                    if (result.success) {
                        started++;
                    }
                    else {
                        failed++;
                    }
                }
            }
            return { started, failed };
        });
    }
    stopAllBots() {
        return __awaiter(this, void 0, void 0, function* () {
            const runningBots = Array.from(this.processes.keys());
            let stopped = 0;
            for (const botId of runningBots) {
                const result = yield this.stopBot(botId);
                if (result.success) {
                    stopped++;
                }
            }
            return { stopped };
        });
    }
    restartAllBots() {
        return __awaiter(this, void 0, void 0, function* () {
            const bots = yield storage_1.storage.getAllBots();
            let restarted = 0;
            let failed = 0;
            for (const bot of bots) {
                if (bot.isEnabled) {
                    const result = yield this.restartBot(bot.id);
                    if (result.success) {
                        restarted++;
                    }
                    else {
                        failed++;
                    }
                }
            }
            return { restarted, failed };
        });
    }
    getBotFilePath(botName) {
        const botFiles = {
            "Application Bot": path_1.default.join(import.meta.dirname, "..", "bots", "applicationBot.ts"),
            "Giveaway & Levels Bot": path_1.default.join(import.meta.dirname, "..", "bots", "giveawayBot.ts"),
            "Invites Tracker Bot": path_1.default.join(import.meta.dirname, "..", "bots", "invitesBot.ts"),
            "Ticket Bot": path_1.default.join(import.meta.dirname, "..", "bots", "ticketBot.ts"),
        };
        return botFiles[botName] || null;
    }
    logBotMessage(botId, level, message, source) {
        return __awaiter(this, void 0, void 0, function* () {
            try {
                const log = yield storage_1.storage.createLog({
                    botId,
                    level,
                    message,
                    source,
                });
                this.broadcast({
                    type: 'new_log',
                    data: log,
                });
            }
            catch (error) {
                logger_1.logger.error('Failed to create log entry:', error);
            }
        });
    }
    shutdown() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
        // Stop all bots
        for (const [botId] of Array.from(this.processes.entries())) {
            this.stopBot(botId);
        }
    }
}
exports.BotManager = BotManager;
exports.botManager = new BotManager();
