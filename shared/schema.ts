// Minimal placeholder schema for compilation

export interface User { id: number; username: string; }
export interface InsertUser { username: string; }
export interface Bot {
  id: number;
  name: string;
  status?: string;
  apiRequests?: number;
  memoryUsage?: number;
  uptime?: number;
  token?: string;
  prefix?: string;
  isEnabled?: boolean;
}
export interface InsertBot {
  name: string;
  prefix?: string;
  status?: string;
}
export interface Log {
  id: number;
  message: string;
  botId?: number;
  timestamp?: string | number;
}
export interface InsertLog {
  message: string;
  botId?: number;
  timestamp?: string | number;
}
export interface SystemHealth {
  id?: number;
  component: string;
  status: string;
  details?: string;
}
export interface InsertSystemHealth {
  component: string;
  status: string;
  details?: string;
}
export interface WebSocketMessage { type: string; payload: any; }

export const insertBotSchema = {};
export const insertLogSchema = {};
export const users: User[] = [];
export const bots: Bot[] = [];
export const logs: Log[] = [];
export const systemHealth: SystemHealth[] = []; 