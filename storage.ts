import { users, bots, logs, systemHealth, type User, type InsertUser, type Bot, type InsertBot, type Log, type InsertLog, type SystemHealth, type InsertSystemHealth } from "./shared/schema";

export interface IStorage {
  // User methods
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  // Bot methods
  getAllBots(): Promise<Bot[]>;
  getBot(id: number): Promise<Bot | undefined>;
  getBotByName(name: string): Promise<Bot | undefined>;
  createBot(bot: InsertBot): Promise<Bot>;
  updateBot(id: number, updates: Partial<Bot>): Promise<Bot | undefined>;
  deleteBot(id: number): Promise<boolean>;

  // Log methods
  getLogs(botId?: number, limit?: number): Promise<Log[]>;
  createLog(log: InsertLog): Promise<Log>;
  clearLogs(botId?: number): Promise<boolean>;

  // System health methods
  getSystemHealth(): Promise<SystemHealth[]>;
  updateSystemHealth(component: string, status: string, details?: string): Promise<SystemHealth>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private bots: Map<number, Bot>;
  private logs: Map<number, Log>;
  private systemHealth: Map<string, SystemHealth>;
  private currentUserId: number;
  private currentBotId: number;
  private currentLogId: number;
  private currentHealthId: number;

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

  private initializeBots() {
    const defaultBots: InsertBot[] = [
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
      const fullBot: Bot = {
        ...bot,
        id,
        status: "offline",
        pid: null,
        uptime: 0,
        lastRestart: null,
        memoryUsage: 0,
        apiRequests: 0,
      };
      this.bots.set(id, fullBot);
    });
  }

  private initializeSystemHealth() {
    const components = [
      { component: "Express.js Server", status: "healthy", details: "HTTP server running" },
      { component: "Discord API Connection", status: "healthy", details: "All bots connected" },
      { component: "Database Connection", status: "healthy", details: "In-memory storage active" },
      { component: "Rate Limiting", status: "warning", details: "85% capacity" },
    ];

    components.forEach((comp) => {
      const id = this.currentHealthId++;
      const health: SystemHealth = {
        ...comp,
        id,
        lastCheck: new Date(),
      };
      this.systemHealth.set(comp.component, health);
    });
  }

  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.currentUserId++;
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async getAllBots(): Promise<Bot[]> {
    return Array.from(this.bots.values());
  }

  async getBot(id: number): Promise<Bot | undefined> {
    return this.bots.get(id);
  }

  async getBotByName(name: string): Promise<Bot | undefined> {
    return Array.from(this.bots.values()).find((bot) => bot.name === name);
  }

  async createBot(insertBot: InsertBot): Promise<Bot> {
    const id = this.currentBotId++;
    const bot: Bot = {
      ...insertBot,
      id,
      status: "offline",
      pid: null,
      uptime: 0,
      lastRestart: null,
      memoryUsage: 0,
      apiRequests: 0,
    };
    this.bots.set(id, bot);
    return bot;
  }

  async updateBot(id: number, updates: Partial<Bot>): Promise<Bot | undefined> {
    const bot = this.bots.get(id);
    if (!bot) return undefined;

    const updatedBot = { ...bot, ...updates };
    this.bots.set(id, updatedBot);
    return updatedBot;
  }

  async deleteBot(id: number): Promise<boolean> {
    return this.bots.delete(id);
  }

  async getLogs(botId?: number, limit: number = 50): Promise<Log[]> {
    let logs = Array.from(this.logs.values());
    
    if (botId) {
      logs = logs.filter((log) => log.botId === botId);
    }

    return logs
      .sort((a, b) => (b.timestamp?.getTime() || 0) - (a.timestamp?.getTime() || 0))
      .slice(0, limit);
  }

  async createLog(insertLog: InsertLog): Promise<Log> {
    const id = this.currentLogId++;
    const log: Log = {
      ...insertLog,
      id,
      timestamp: new Date(),
    };
    this.logs.set(id, log);
    return log;
  }

  async clearLogs(botId?: number): Promise<boolean> {
    if (botId) {
      const logsToDelete = Array.from(this.logs.entries())
        .filter(([_, log]) => log.botId === botId)
        .map(([id]) => id);
      
      logsToDelete.forEach((id) => this.logs.delete(id));
    } else {
      this.logs.clear();
    }
    return true;
  }

  async getSystemHealth(): Promise<SystemHealth[]> {
    return Array.from(this.systemHealth.values());
  }

  async updateSystemHealth(component: string, status: string, details?: string): Promise<SystemHealth> {
    const existing = this.systemHealth.get(component);
    const health: SystemHealth = {
      id: existing?.id || this.currentHealthId++,
      component,
      status,
      details,
      lastCheck: new Date(),
    };
    this.systemHealth.set(component, health);
    return health;
  }
}

export const storage = new MemStorage();
