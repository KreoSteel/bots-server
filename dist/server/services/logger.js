"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.logger = exports.Logger = void 0;
class Logger {
    formatTimestamp() {
        return new Date().toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
            hour12: true,
        });
    }
    log(level, message, ...args) {
        const timestamp = this.formatTimestamp();
        const logMessage = `${timestamp} [bot-manager] [${level.toUpperCase()}] ${message}`;
        if (level === 'error') {
            console.error(logMessage, ...args);
        }
        else if (level === 'warn') {
            console.warn(logMessage, ...args);
        }
        else {
            console.log(logMessage, ...args);
        }
    }
    info(message, ...args) {
        this.log('info', message, ...args);
    }
    warn(message, ...args) {
        this.log('warn', message, ...args);
    }
    error(message, ...args) {
        this.log('error', message, ...args);
    }
    debug(message, ...args) {
        this.log('debug', message, ...args);
    }
}
exports.Logger = Logger;
exports.logger = new Logger();
