export class Logger {
  private formatTimestamp(): string {
    return new Date().toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  }

  private log(level: string, message: string, ...args: any[]) {
    const timestamp = this.formatTimestamp();
    const logMessage = `${timestamp} [bot-manager] [${level.toUpperCase()}] ${message}`;
    
    if (level === 'error') {
      console.error(logMessage, ...args);
    } else if (level === 'warn') {
      console.warn(logMessage, ...args);
    } else {
      console.log(logMessage, ...args);
    }
  }

  info(message: string, ...args: any[]) {
    this.log('info', message, ...args);
  }

  warn(message: string, ...args: any[]) {
    this.log('warn', message, ...args);
  }

  error(message: string, ...args: any[]) {
    this.log('error', message, ...args);
  }

  debug(message: string, ...args: any[]) {
    this.log('debug', message, ...args);
  }
}

export const logger = new Logger();
