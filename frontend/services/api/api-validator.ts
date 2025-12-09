/**
 * API Data Validation and Sanitization
 * Comprehensive validation for all API requests and responses
 */

import { API_CONFIG } from './api-config';

// Sanitization utilities
export class Sanitizer {
  /**
   * Sanitize string input by removing potentially harmful characters
   */
  static sanitizeString(input: string, maxLength?: number): string {
    if (typeof input !== 'string') {
      return '';
    }

    // Remove null bytes, control characters, and normalize whitespace
    let sanitized = input
      .replace(/[\x00-\x1F\x7F]/g, '') // Remove control characters
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();

    // Trim to max length if specified
    if (maxLength && sanitized.length > maxLength) {
      sanitized = sanitized.substring(0, maxLength);
    }

    return sanitized;
  }

  /**
   * Sanitize HTML content
   */
  static sanitizeHTML(input: string): string {
    if (typeof input !== 'string') {
      return '';
    }

    // Basic HTML sanitization - remove script tags and dangerous attributes
    return input
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
      .replace(/on\w+="[^"]*"/gi, '') // Remove event handlers
      .replace(/javascript:/gi, '') // Remove javascript protocol
      .trim();
  }

  /**
   * Sanitize numeric input
   */
  static sanitizeNumber(input: any, min?: number, max?: number): number | null {
    const num = Number(input);

    if (isNaN(num) || !isFinite(num)) {
      return null;
    }

    if (min !== undefined && num < min) {
      return null;
    }

    if (max !== undefined && num > max) {
      return null;
    }

    return num;
  }

  /**
   * Sanitize array input
   */
  static sanitizeArray(input: any, itemValidator?: (item: any) => boolean): any[] {
    if (!Array.isArray(input)) {
      return [];
    }

    if (!itemValidator) {
      return input.slice(); // Return shallow copy
    }

    return input.filter(itemValidator);
  }

  /**
   * Sanitize object input by removing dangerous properties
   */
  static sanitizeObject(input: any, allowedKeys?: string[]): Record<string, any> {
    if (typeof input !== 'object' || input === null) {
      return {};
    }

    const result: Record<string, any> = {};

    for (const [key, value] of Object.entries(input)) {
      // Skip __proto__ and other dangerous properties
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
        continue;
      }

      // Filter by allowed keys if specified
      if (allowedKeys && !allowedKeys.includes(key)) {
        continue;
      }

      // Recursively sanitize nested objects
      if (typeof value === 'object' && value !== null) {
        result[key] = this.sanitizeObject(value);
      } else if (typeof value === 'string') {
        result[key] = this.sanitizeString(value);
      } else {
        result[key] = value;
      }
    }

    return result;
  }
}

// Validation utilities
export class Validator {
  /**
   * Validate email format
   */
  static isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * Validate UUID format
   */
  static isValidUUID(uuid: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  }

  /**
   * Validate agent type
   */
  static isValidAgentType(type: string): boolean {
    return API_CONFIG.validation.allowedAgentTypes.includes(type);
  }

  /**
   * Validate task type
   */
  static isValidTaskType(type: string): boolean {
    return API_CONFIG.validation.allowedTaskTypes.includes(type);
  }

  /**
   * Validate priority level
   */
  static isValidPriority(priority: string): boolean {
    return API_CONFIG.validation.allowedPriorities.includes(priority);
  }

  /**
   * Validate agent status
   */
  static isValidAgentStatus(status: string): boolean {
    const validStatuses = ['idle', 'busy', 'offline', 'error', 'processing', 'maintenance'];
    return validStatuses.includes(status);
  }

  /**
   * Validate task status
   */
  static isValidTaskStatus(status: string): boolean {
    const validStatuses = ['pending', 'processing', 'completed', 'failed', 'delegated', 'cancelled'];
    return validStatuses.includes(status);
  }
}

// Request validators
export const RequestValidators = {
  /**
   * Validate agent task request
   */
  validateAgentTaskRequest(request: any): { isValid: boolean; errors: string[]; sanitized: any } {
    const errors: string[] = [];
    const sanitized = Sanitizer.sanitizeObject(request, [
      'type',
      'title',
      'description',
      'priority',
      'parameters',
      'context',
      'metadata'
    ]);

    // Validate required fields
    if (!sanitized.type || typeof sanitized.type !== 'string') {
      errors.push('Task type is required and must be a string');
    } else if (!Validator.isValidTaskType(sanitized.type)) {
      errors.push(`Invalid task type: ${sanitized.type}`);
    }

    if (!sanitized.title || typeof sanitized.title !== 'string') {
      errors.push('Title is required and must be a string');
    } else {
      sanitized.title = Sanitizer.sanitizeString(sanitized.title, API_CONFIG.validation.maxTitleLength);
      if (!sanitized.title) {
        errors.push('Title cannot be empty after sanitization');
      }
    }

    if (!sanitized.description || typeof sanitized.description !== 'string') {
      errors.push('Description is required and must be a string');
    } else {
      sanitized.description = Sanitizer.sanitizeString(sanitized.description, API_CONFIG.validation.maxDescriptionLength);
      if (!sanitized.description) {
        errors.push('Description cannot be empty after sanitization');
      }
    }

    if (!sanitized.priority || typeof sanitized.priority !== 'string') {
      errors.push('Priority is required and must be a string');
    } else if (!Validator.isValidPriority(sanitized.priority)) {
      errors.push(`Invalid priority: ${sanitized.priority}`);
    }

    // Validate optional fields
    if (sanitized.parameters && typeof sanitized.parameters !== 'object') {
      errors.push('Parameters must be an object');
      delete sanitized.parameters;
    }

    if (sanitized.context && typeof sanitized.context !== 'object') {
      errors.push('Context must be an object');
      delete sanitized.context;
    }

    if (sanitized.metadata && typeof sanitized.metadata !== 'object') {
      errors.push('Metadata must be an object');
      delete sanitized.metadata;
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitized
    };
  },

  /**
   * Validate agent action request
   */
  validateAgentActionRequest(action: any): { isValid: boolean; errors: string[]; sanitized: any } {
    const errors: string[] = [];
    const sanitized = Sanitizer.sanitizeObject(action, ['action', 'parameters']);

    const validActions = ['start', 'stop', 'restart', 'pause', 'resume', 'configure'];

    if (!sanitized.action || typeof sanitized.action !== 'string') {
      errors.push('Action is required and must be a string');
    } else if (!validActions.includes(sanitized.action)) {
      errors.push(`Invalid action: ${sanitized.action}. Valid actions: ${validActions.join(', ')}`);
    }

    if (sanitized.parameters && typeof sanitized.parameters !== 'object') {
      errors.push('Parameters must be an object');
      delete sanitized.parameters;
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitized
    };
  },

  /**
   * Validate swarm process request
   */
  validateSwarmProcessRequest(request: any): { isValid: boolean; errors: string[]; sanitized: any } {
    const errors: string[] = [];
    const sanitized = Sanitizer.sanitizeObject(request, ['message', 'context', 'options']);

    if (!sanitized.message || typeof sanitized.message !== 'string') {
      errors.push('Message is required and must be a string');
    } else {
      sanitized.message = Sanitizer.sanitizeString(sanitized.message, 5000);
    }

    if (sanitized.context && typeof sanitized.context !== 'object') {
      errors.push('Context must be an object');
      delete sanitized.context;
    }

    if (sanitized.options && typeof sanitized.options !== 'object') {
      errors.push('Options must be an object');
      delete sanitized.options;
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitized
    };
  }
};

// Response validators
export const ResponseValidators = {
  /**
   * Validate API response structure
   */
  validateAPIResponse(response: any): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!response || typeof response !== 'object') {
      errors.push('Response must be an object');
      return { isValid: false, errors };
    }

    if (typeof response.success !== 'boolean') {
      errors.push('Response must have a boolean success field');
    }

    if (response.data !== undefined && typeof response.data !== 'object') {
      errors.push('Response data must be an object');
    }

    if (response.error && typeof response.error !== 'string') {
      errors.push('Response error must be a string');
    }

    if (response.timestamp && typeof response.timestamp !== 'string') {
      errors.push('Response timestamp must be a string');
    }

    return { isValid: errors.length === 0, errors };
  },

  /**
   * Validate agent status response
   */
  validateAgentStatusResponse(response: any): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!response || typeof response !== 'object') {
      errors.push('Agent status response must be an object');
      return { isValid: false, errors };
    }

    if (!response.agent_id || typeof response.agent_id !== 'string') {
      errors.push('Agent ID is required and must be a string');
    } else if (!Validator.isValidUUID(response.agent_id)) {
      errors.push('Agent ID must be a valid UUID');
    }

    if (response.status && !Validator.isValidAgentStatus(response.status)) {
      errors.push(`Invalid agent status: ${response.status}`);
    }

    if (response.current_tasks !== undefined && !Number.isInteger(response.current_tasks)) {
      errors.push('Current tasks must be an integer');
    }

    return { isValid: errors.length === 0, errors };
  }
};

// Validation middleware
export function createValidationMiddleware<T>(
  validator: (data: any) => { isValid: boolean; errors: string[]; sanitized?: T }
) {
  return (data: any): { isValid: boolean; errors: string[]; sanitized?: T } => {
    try {
      return validator(data);
    } catch (error) {
      return {
        isValid: false,
        errors: [`Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`]
      };
    }
  };
}

// Error handler for validation failures
export class ValidationError extends Error {
  public readonly errors: string[];

  constructor(errors: string[]) {
    super(`Validation failed: ${errors.join(', ')}`);
    this.name = 'ValidationError';
    this.errors = errors;
  }
}

export default {
  Sanitizer,
  Validator,
  RequestValidators,
  ResponseValidators,
  createValidationMiddleware,
  ValidationError
};