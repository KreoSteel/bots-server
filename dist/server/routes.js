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
exports.registerRoutes = registerRoutes;
const http_1 = require("http");
const ws_1 = require("ws");
const storage_1 = require("./storage");
const botManager_1 = require("./services/botManager");
const logger_1 = require("./services/logger");
function registerRoutes(app) {
    return __awaiter(this, void 0, void 0, function* () {
        const httpServer = (0, http_1.createServer)(app);
        // WebSocket server for real-time updates
        const wss = new ws_1.WebSocketServer({ server: httpServer, path: '/ws' });
        // Store WebSocket connections
        const clients = new Set();
        wss.on('connection', (ws) => {
            clients.add(ws);
            logger_1.logger.info('WebSocket client connected');
            ws.on('close', () => {
                clients.delete(ws);
                logger_1.logger.info('WebSocket client disconnected');
            });
            ws.on('error', (error) => {
                logger_1.logger.error('WebSocket error:', error);
                clients.delete(ws);
            });
        });
        // Broadcast to all connected WebSocket clients
        function broadcast(message) {
            const data = JSON.stringify(message);
            clients.forEach((client) => {
                if (client.readyState === ws_1.WebSocket.OPEN) {
                    client.send(data);
                }
            });
        }
        // Set up bot manager with broadcast callback
        botManager_1.botManager.setBroadcastCallback(broadcast);
        // API Routes
        // Get all bots with their status
        app.get('/api/bots', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const bots = yield storage_1.storage.getAllBots();
                res.json(bots);
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to fetch bots' });
            }
        }));
        // Get bot statistics
        app.get('/api/stats', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const bots = yield storage_1.storage.getAllBots();
                const activeBots = bots.filter(bot => bot.status === 'online').length;
                const totalApiRequests = bots.reduce((sum, bot) => sum + (bot.apiRequests || 0), 0);
                const totalMemory = bots.reduce((sum, bot) => sum + (bot.memoryUsage || 0), 0);
                // Calculate average uptime
                const onlineBots = bots.filter(bot => bot.status === 'online');
                const avgUptime = onlineBots.length > 0
                    ? onlineBots.reduce((sum, bot) => sum + (bot.uptime || 0), 0) / onlineBots.length
                    : 0;
                const uptimePercentage = Math.min(99.9, 95 + (avgUptime / 86400) * 5); // Convert uptime to percentage
                res.json({
                    activeBots,
                    totalUptime: `${uptimePercentage.toFixed(1)}%`,
                    apiRequests: totalApiRequests,
                    memoryUsage: `${totalMemory} MB`,
                });
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to fetch statistics' });
            }
        }));
        // Start a bot
        app.post('/api/bots/:id/start', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const botId = parseInt(req.params.id);
                const result = yield botManager_1.botManager.startBot(botId);
                if (result.success) {
                    res.json({ message: `Bot started successfully` });
                }
                else {
                    res.status(400).json({ message: result.error });
                }
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to start bot' });
            }
        }));
        // Stop a bot
        app.post('/api/bots/:id/stop', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const botId = parseInt(req.params.id);
                const result = yield botManager_1.botManager.stopBot(botId);
                if (result.success) {
                    res.json({ message: `Bot stopped successfully` });
                }
                else {
                    res.status(400).json({ message: result.error });
                }
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to stop bot' });
            }
        }));
        // Restart a bot
        app.post('/api/bots/:id/restart', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const botId = parseInt(req.params.id);
                const result = yield botManager_1.botManager.restartBot(botId);
                if (result.success) {
                    res.json({ message: `Bot restarted successfully` });
                }
                else {
                    res.status(400).json({ message: result.error });
                }
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to restart bot' });
            }
        }));
        // Start all bots
        app.post('/api/bots/start-all', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const result = yield botManager_1.botManager.startAllBots();
                res.json({ message: `Started ${result.started} bots, ${result.failed} failed` });
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to start all bots' });
            }
        }));
        // Stop all bots
        app.post('/api/bots/stop-all', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const result = yield botManager_1.botManager.stopAllBots();
                res.json({ message: `Stopped ${result.stopped} bots` });
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to stop all bots' });
            }
        }));
        // Restart all bots
        app.post('/api/bots/restart-all', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const result = yield botManager_1.botManager.restartAllBots();
                res.json({ message: `Restarted ${result.restarted} bots, ${result.failed} failed` });
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to restart all bots' });
            }
        }));
        // Get logs
        app.get('/api/logs', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const botId = req.query.botId ? parseInt(req.query.botId) : undefined;
                const limit = req.query.limit ? parseInt(req.query.limit) : 50;
                const logs = yield storage_1.storage.getLogs(botId, limit);
                res.json(logs);
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to fetch logs' });
            }
        }));
        // Clear logs
        app.delete('/api/logs', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const botId = req.query.botId ? parseInt(req.query.botId) : undefined;
                yield storage_1.storage.clearLogs(botId);
                res.json({ message: 'Logs cleared successfully' });
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to clear logs' });
            }
        }));
        // Get system health
        app.get('/api/health', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const health = yield storage_1.storage.getSystemHealth();
                res.json(health);
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to fetch system health' });
            }
        }));
        // Update bot environment variables
        app.patch('/api/bots/:id/env', (req, res) => __awaiter(this, void 0, void 0, function* () {
            try {
                const botId = parseInt(req.params.id);
                const { token } = req.body;
                if (!token) {
                    return res.status(400).json({ message: 'Token is required' });
                }
                const bot = yield storage_1.storage.updateBot(botId, { token });
                if (!bot) {
                    return res.status(404).json({ message: 'Bot not found' });
                }
                res.json({ message: 'Bot token updated successfully' });
            }
            catch (error) {
                res.status(500).json({ message: 'Failed to update bot token' });
            }
        }));
        // Health check endpoint
        app.get('/api/ping', (req, res) => {
            res.json({ status: 'ok', timestamp: new Date().toISOString() });
        });
        // Initialize bot manager
        yield botManager_1.botManager.initialize();
        return httpServer;
    });
}
