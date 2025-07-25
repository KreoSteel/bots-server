import type { Express } from "express";
import { createServer, type Server } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { storage } from "./storage";
import { botManager } from "./services/botManager";
import { logger } from "./services/logger";
import { insertBotSchema, insertLogSchema, type WebSocketMessage } from "./shared/schema";

export async function registerRoutes(app: Express): Promise<Server> {
  const httpServer = createServer(app);
  
  // WebSocket server for real-time updates
  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });
  
  // Store WebSocket connections
  const clients = new Set<WebSocket>();
  
  wss.on('connection', (ws: WebSocket) => {
    clients.add(ws);
    logger.info('WebSocket client connected');
    
    ws.on('close', () => {
      clients.delete(ws);
      logger.info('WebSocket client disconnected');
    });
    
    ws.on('error', (error) => {
      logger.error('WebSocket error:', error);
      clients.delete(ws);
    });
  });

  // Broadcast to all connected WebSocket clients
  function broadcast(message: WebSocketMessage) {
    const data = JSON.stringify(message);
    clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(data);
      }
    });
  }

  // Set up bot manager with broadcast callback
  botManager.setBroadcastCallback(broadcast);

  // API Routes

  // Get all bots with their status
  app.get('/api/bots', async (req, res) => {
    try {
      const bots = await storage.getAllBots();
      res.json(bots);
    } catch (error) {
      res.status(500).json({ message: 'Failed to fetch bots' });
    }
  });

  // Get bot statistics
  app.get('/api/stats', async (req, res) => {
    try {
      const bots = await storage.getAllBots();
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
    } catch (error) {
      res.status(500).json({ message: 'Failed to fetch statistics' });
    }
  });

  // Start a bot
  app.post('/api/bots/:id/start', async (req, res) => {
    try {
      const botId = parseInt(req.params.id);
      const result = await botManager.startBot(botId);
      
      if (result.success) {
        res.json({ message: `Bot started successfully` });
      } else {
        res.status(400).json({ message: result.error });
      }
    } catch (error) {
      res.status(500).json({ message: 'Failed to start bot' });
    }
  });

  // Stop a bot
  app.post('/api/bots/:id/stop', async (req, res) => {
    try {
      const botId = parseInt(req.params.id);
      const result = await botManager.stopBot(botId);
      
      if (result.success) {
        res.json({ message: `Bot stopped successfully` });
      } else {
        res.status(400).json({ message: result.error });
      }
    } catch (error) {
      res.status(500).json({ message: 'Failed to stop bot' });
    }
  });

  // Restart a bot
  app.post('/api/bots/:id/restart', async (req, res) => {
    try {
      const botId = parseInt(req.params.id);
      const result = await botManager.restartBot(botId);
      
      if (result.success) {
        res.json({ message: `Bot restarted successfully` });
      } else {
        res.status(400).json({ message: result.error });
      }
    } catch (error) {
      res.status(500).json({ message: 'Failed to restart bot' });
    }
  });

  // Start all bots
  app.post('/api/bots/start-all', async (req, res) => {
    try {
      const result = await botManager.startAllBots();
      res.json({ message: `Started ${result.started} bots, ${result.failed} failed` });
    } catch (error) {
      res.status(500).json({ message: 'Failed to start all bots' });
    }
  });

  // Stop all bots
  app.post('/api/bots/stop-all', async (req, res) => {
    try {
      const result = await botManager.stopAllBots();
      res.json({ message: `Stopped ${result.stopped} bots` });
    } catch (error) {
      res.status(500).json({ message: 'Failed to stop all bots' });
    }
  });

  // Restart all bots
  app.post('/api/bots/restart-all', async (req, res) => {
    try {
      const result = await botManager.restartAllBots();
      res.json({ message: `Restarted ${result.restarted} bots, ${result.failed} failed` });
    } catch (error) {
      res.status(500).json({ message: 'Failed to restart all bots' });
    }
  });

  // Get logs
  app.get('/api/logs', async (req, res) => {
    try {
      const botId = req.query.botId ? parseInt(req.query.botId as string) : undefined;
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 50;
      
      const logs = await storage.getLogs(botId, limit);
      res.json(logs);
    } catch (error) {
      res.status(500).json({ message: 'Failed to fetch logs' });
    }
  });

  // Clear logs
  app.delete('/api/logs', async (req, res) => {
    try {
      const botId = req.query.botId ? parseInt(req.query.botId as string) : undefined;
      await storage.clearLogs(botId);
      res.json({ message: 'Logs cleared successfully' });
    } catch (error) {
      res.status(500).json({ message: 'Failed to clear logs' });
    }
  });

  // Get system health
  app.get('/api/health', async (req, res) => {
    try {
      const health = await storage.getSystemHealth();
      res.json(health);
    } catch (error) {
      res.status(500).json({ message: 'Failed to fetch system health' });
    }
  });

  // Update bot environment variables
  app.patch('/api/bots/:id/env', async (req, res) => {
    try {
      const botId = parseInt(req.params.id);
      const { token } = req.body;
      
      if (!token) {
        return res.status(400).json({ message: 'Token is required' });
      }

      const bot = await storage.updateBot(botId, { token });
      if (!bot) {
        return res.status(404).json({ message: 'Bot not found' });
      }

      res.json({ message: 'Bot token updated successfully' });
    } catch (error) {
      res.status(500).json({ message: 'Failed to update bot token' });
    }
  });

  // Health check endpoint
  app.get('/api/ping', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  // Initialize bot manager
  await botManager.initialize();

  return httpServer;
}
