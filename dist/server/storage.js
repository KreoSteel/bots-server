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
Object.defineProperty(exports, "__esModule", { value: true });
exports.storage = exports.MemStorage = void 0;
class MemStorage {
    constructor() {
        this.users = new Map();
        this.bots = new Map();
        this.logs = new Map();
        this.systemHealth = new Map();
        this.currentUserId = 1;
        this.currentBotId = 1;
        this.currentLogId = 1;
        this.currentHealthId = 1;
        // Initialize with the 4 Discord bots
        this.initializeBots();
        this.initializeSystemHealth();
    }
    initializeBots() {
        const defaultBots = [
            {
                name: "Application Bot",
                prefix: "app!",
                token: process.env.APPLICATION_BOT_TOKEN || "",
                isEnabled: true,
            },
            {
                name: "Giveaway & Levels Bot",
                prefix: "mul!",
                token: process.env.GIVEAWAY_BOT_TOKEN || "",
                isEnabled: true,
            },
            {
                name: "Invites Tracker Bot",
                prefix: "inv!",
                token: process.env.INVITES_BOT_TOKEN || "",
                isEnabled: true,
            },
            {
                name: "Ticket Bot",
                prefix: "dio!",
                token: process.env.TICKET_BOT_TOKEN || "",
                isEnabled: true,
            },
        ];
        defaultBots.forEach((bot) => {
            const id = this.currentBotId++;
            const fullBot = Object.assign(Object.assign({}, bot), { id, status: "offline", pid: null, uptime: 0, lastRestart: null, memoryUsage: 0, apiRequests: 0 });
            this.bots.set(id, fullBot);
        });
    }
    initializeSystemHealth() {
        const components = [
            { component: "Express.js Server", status: "healthy", details: "HTTP server running" },
            { component: "Discord API Connection", status: "healthy", details: "All bots connected" },
            { component: "Database Connection", status: "healthy", details: "In-memory storage active" },
            { component: "Rate Limiting", status: "warning", details: "85% capacity" },
        ];
        components.forEach((comp) => {
            const id = this.currentHealthId++;
            const health = Object.assign(Object.assign({}, comp), { id, lastCheck: new Date() });
            this.systemHealth.set(comp.component, health);
        });
    }
    getUser(id) {
        return __awaiter(this, void 0, void 0, function* () {
            return this.users.get(id);
        });
    }
    getUserByUsername(username) {
        return __awaiter(this, void 0, void 0, function* () {
            return Array.from(this.users.values()).find((user) => user.username === username);
        });
    }
    createUser(insertUser) {
        return __awaiter(this, void 0, void 0, function* () {
            const id = this.currentUserId++;
            const user = Object.assign(Object.assign({}, insertUser), { id });
            this.users.set(id, user);
            return user;
        });
    }
    getAllBots() {
        return __awaiter(this, void 0, void 0, function* () {
            return Array.from(this.bots.values());
        });
    }
    getBot(id) {
        return __awaiter(this, void 0, void 0, function* () {
            return this.bots.get(id);
        });
    }
    getBotByName(name) {
        return __awaiter(this, void 0, void 0, function* () {
            return Array.from(this.bots.values()).find((bot) => bot.name === name);
        });
    }
    createBot(insertBot) {
        return __awaiter(this, void 0, void 0, function* () {
            const id = this.currentBotId++;
            const bot = Object.assign(Object.assign({}, insertBot), { id, status: "offline", pid: null, uptime: 0, lastRestart: null, memoryUsage: 0, apiRequests: 0 });
            this.bots.set(id, bot);
            return bot;
        });
    }
    updateBot(id, updates) {
        return __awaiter(this, void 0, void 0, function* () {
            const bot = this.bots.get(id);
            if (!bot)
                return undefined;
            const updatedBot = Object.assign(Object.assign({}, bot), updates);
            this.bots.set(id, updatedBot);
            return updatedBot;
        });
    }
    deleteBot(id) {
        return __awaiter(this, void 0, void 0, function* () {
            return this.bots.delete(id);
        });
    }
    getLogs(botId_1) {
        return __awaiter(this, arguments, void 0, function* (botId, limit = 50) {
            let logs = Array.from(this.logs.values());
            if (botId) {
                logs = logs.filter((log) => log.botId === botId);
            }
            return logs
                .sort((a, b) => { var _a, _b; return (((_a = b.timestamp) === null || _a === void 0 ? void 0 : _a.getTime()) || 0) - (((_b = a.timestamp) === null || _b === void 0 ? void 0 : _b.getTime()) || 0); })
                .slice(0, limit);
        });
    }
    createLog(insertLog) {
        return __awaiter(this, void 0, void 0, function* () {
            const id = this.currentLogId++;
            const log = Object.assign(Object.assign({}, insertLog), { id, timestamp: new Date() });
            this.logs.set(id, log);
            return log;
        });
    }
    clearLogs(botId) {
        return __awaiter(this, void 0, void 0, function* () {
            if (botId) {
                const logsToDelete = Array.from(this.logs.entries())
                    .filter(([_, log]) => log.botId === botId)
                    .map(([id]) => id);
                logsToDelete.forEach((id) => this.logs.delete(id));
            }
            else {
                this.logs.clear();
            }
            return true;
        });
    }
    getSystemHealth() {
        return __awaiter(this, void 0, void 0, function* () {
            return Array.from(this.systemHealth.values());
        });
    }
    updateSystemHealth(component, status, details) {
        return __awaiter(this, void 0, void 0, function* () {
            const existing = this.systemHealth.get(component);
            const health = {
                id: (existing === null || existing === void 0 ? void 0 : existing.id) || this.currentHealthId++,
                component,
                status,
                details,
                lastCheck: new Date(),
            };
            this.systemHealth.set(component, health);
            return health;
        });
    }
}
exports.MemStorage = MemStorage;
exports.storage = new MemStorage();
