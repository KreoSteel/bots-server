// Minimal placeholder schema for compilation

export interface User { id: number; username: string; }
export interface InsertUser { username: string; }
export interface Bot { id: number; name: string; }
export interface InsertBot { name: string; }
export interface Log { id: number; message: string; }
export interface InsertLog { message: string; }
export interface SystemHealth { component: string; status: string; details?: string; }
export interface InsertSystemHealth { component: string; status: string; details?: string; }
export interface WebSocketMessage { type: string; payload: any; }

export const insertBotSchema = {};
export const insertLogSchema = {}; 