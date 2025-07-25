import { spawn, ChildProcess } from "child_process";
import { storage } from "../storage";
import { logger } from "./logger";
import path from "path";
import { type WebSocketMessage, type Bot } from "./shared/schema";

interface BotProcess {
  process: ChildProcess;
  startTime: Date;
  restartCount: number;
}

export class BotManager {
  private processes = new Map<number, BotProcess>();
  private broadcastCallback?: (message: WebSocketMessage) => void;
  private monitoringInterval?: NodeJS.Timeout;

  setBroadcastCallback(callback: (message: WebSocketMessage) => void) {
    this.broadcastCallback = callback;
  }

  private broadcast(message: WebSocketMessage) {
    if (this.broadcastCallback) {
      this.broadcastCallback(message);
    }
  }

  async initialize() {
    logger.info("Initializing Bot Manager...");
    
    // Start monitoring
    this.startMonitoring();
    
    // Auto-start enabled bots
    const bots = await storage.getAllBots();
    for (const bot of bots) {
      if (bot.isEnabled) {
        await this.startBot(bot.id);
      }
    }
  }

  private startMonitoring() {
    this.monitoringInterval = setInterval(async () => {
      await this.updateBotStats();
      await this.checkBotHealth();
    }, 5000); // Update every 5 seconds
  }

  private async updateBotStats() {
    for (const [botId, botProcess] of Array.from(this.processes.entries())) {
      const uptime = Math.floor((Date.now() - botProcess.startTime.getTime()) / 1000);
      const memoryUsage = Math.floor(Math.random() * 50) + 80; // Simulate memory usage
      const apiRequests = Math.floor(Math.random() * 100) + 50; // Simulate API requests

      await storage.updateBot(botId, {
        uptime,
        memoryUsage,
        apiRequests,
      });
    }

    // Broadcast stats update
    const bots = await storage.getAllBots();
    this.broadcast({
      type: 'stats_update',
      data: bots,
    });
  }

  private async checkBotHealth() {
    for (const [botId, botProcess] of Array.from(this.processes.entries())) {
      if (botProcess.process.killed || botProcess.process.exitCode !== null) {
        logger.warn(`Bot ${botId} appears to have crashed, attempting restart...`);
        await this.restartBot(botId);
      }
    }
  }

  async startBot(botId: number): Promise<{ success: boolean; error?: string }> {
    try {
      const bot = await storage.getBot(botId);
      if (!bot) {
        return { success: false, error: "Bot not found" };
      }

      if (this.processes.has(botId)) {
        return { success: false, error: "Bot is already running" };
      }

      if (!bot.token) {
        return { success: false, error: "Bot token not configured" };
      }

      logger.info(`Starting bot: ${bot.name} (${bot.prefix})`);

      // Determine bot file based on bot name
      const botFile = this.getBotFilePath(bot.name);
      if (!botFile) {
        return { success: false, error: "Bot implementation not found" };
      }

      // Start the bot process
      const botProcess = spawn('node', ['-r', 'tsx/esm', botFile], {
        env: {
          ...process.env,
          BOT_TOKEN: bot.token,
          BOT_ID: botId.toString(),
        },
        stdio: ['ignore', 'pipe', 'pipe'],
      });

      const botProcessData: BotProcess = {
        process: botProcess,
        startTime: new Date(),
        restartCount: 0,
      };

      this.processes.set(botId, botProcessData);

      // Handle process output
      botProcess.stdout?.on('data', (data: any) => {
        const message = data.toString().trim();
        logger.info(`[${bot.name}] ${message}`);
        this.logBotMessage(botId, 'info', message, 'discord');
      });

      botProcess.stderr?.on('data', (data: any) => {
        const message = data.toString().trim();
        logger.error(`[${bot.name}] ${message}`);
        this.logBotMessage(botId, 'error', message, 'discord');
      });

      botProcess.on('exit', async (code: any) => {
        logger.warn(`Bot ${bot.name} exited with code ${code}`);
        this.processes.delete(botId);
        
        await storage.updateBot(botId, {
          status: 'offline',
          pid: null,
        });

        this.broadcast({
          type: 'bot_status',
          data: { botId, status: 'offline' },
        });

        this.logBotMessage(botId, 'warn', `Bot exited with code ${code}`, 'system');
      });

      // Update bot status
      await storage.updateBot(botId, {
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
    } catch (error) {
      logger.error(`Failed to start bot ${botId}:`, error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  async stopBot(botId: number): Promise<{ success: boolean; error?: string }> {
    try {
      const bot = await storage.getBot(botId);
      if (!bot) {
        return { success: false, error: "Bot not found" };
      }

      const botProcess = this.processes.get(botId);
      if (!botProcess) {
        return { success: false, error: "Bot is not running" };
      }

      logger.info(`Stopping bot: ${bot.name}`);

      // Gracefully terminate the process
      botProcess.process.kill('SIGTERM');
      
      // Force kill after 5 seconds if still running
      setTimeout(() => {
        if (!botProcess.process.killed) {
          botProcess.process.kill('SIGKILL');
        }
      }, 5000);

      this.processes.delete(botId);

      await storage.updateBot(botId, {
        status: 'offline',
        pid: null,
      });

      this.broadcast({
        type: 'bot_status',
        data: { botId, status: 'offline' },
      });

      this.logBotMessage(botId, 'info', `Bot stopped manually`, 'system');

      return { success: true };
    } catch (error) {
      logger.error(`Failed to stop bot ${botId}:`, error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  async restartBot(botId: number): Promise<{ success: boolean; error?: string }> {
    try {
      const bot = await storage.getBot(botId);
      if (!bot) {
        return { success: false, error: "Bot not found" };
      }

      logger.info(`Restarting bot: ${bot.name}`);

      // Update status to restarting
      await storage.updateBot(botId, { status: 'restarting' });
      this.broadcast({
        type: 'bot_status',
        data: { botId, status: 'restarting' },
      });

      // Stop if running
      if (this.processes.has(botId)) {
        await this.stopBot(botId);
        // Wait a moment for cleanup
        await new Promise(resolve => setTimeout(resolve, 1000));
      }

      // Start again
      const result = await this.startBot(botId);
      
      if (result.success) {
        this.logBotMessage(botId, 'info', `Bot restarted successfully`, 'system');
      }

      return result;
    } catch (error) {
      logger.error(`Failed to restart bot ${botId}:`, error);
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  }

  async startAllBots(): Promise<{ started: number; failed: number }> {
    const bots = await storage.getAllBots();
    let started = 0;
    let failed = 0;

    for (const bot of bots) {
      if (bot.isEnabled) {
        const result = await this.startBot(bot.id);
        if (result.success) {
          started++;
        } else {
          failed++;
        }
      }
    }

    return { started, failed };
  }

  async stopAllBots(): Promise<{ stopped: number }> {
    const runningBots = Array.from(this.processes.keys());
    let stopped = 0;

    for (const botId of runningBots) {
      const result = await this.stopBot(botId);
      if (result.success) {
        stopped++;
      }
    }

    return { stopped };
  }

  async restartAllBots(): Promise<{ restarted: number; failed: number }> {
    const bots = await storage.getAllBots();
    let restarted = 0;
    let failed = 0;

    for (const bot of bots) {
      if (bot.isEnabled) {
        const result = await this.restartBot(bot.id);
        if (result.success) {
          restarted++;
        } else {
          failed++;
        }
      }
    }

    return { restarted, failed };
  }

  private getBotFilePath(botName: string): string | null {
    const botFiles: Record<string, string> = {
      "Application Bot": path.join(import.meta.dirname, "..", "bots", "applicationBot.ts"),
      "Giveaway & Levels Bot": path.join(import.meta.dirname, "..", "bots", "giveawayBot.ts"),
      "Invites Tracker Bot": path.join(import.meta.dirname, "..", "bots", "invitesBot.ts"),
      "Ticket Bot": path.join(import.meta.dirname, "..", "bots", "ticketBot.ts"),
    };

    return botFiles[botName] || null;
  }

  private async logBotMessage(botId: number, level: string, message: string, source: string) {
    try {
      const log = await storage.createLog({
        botId,
        level,
        message,
        source,
      });

      this.broadcast({
        type: 'new_log',
        data: log,
      });
    } catch (error) {
      logger.error('Failed to create log entry:', error);
    }
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

export const botManager = new BotManager();
