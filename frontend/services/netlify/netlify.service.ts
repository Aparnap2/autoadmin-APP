export interface NetlifyFunctionResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  statusCode?: number;
}

export interface FunctionCallOptions {
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
  sessionId?: string;
}

export class NetlifyService {
  private static instance: NetlifyService;
  private baseUrl: string;
  private sessionId: string;

  private constructor() {
    this.baseUrl = process.env.EXPO_PUBLIC_NETLIFY_FUNCTIONS_URL || '';
    this.sessionId = 'default_session';
  }

  static getInstance(): NetlifyService {
    if (!NetlifyService.instance) {
      NetlifyService.instance = new NetlifyService();
    }
    return NetlifyService.instance;
  }

  setSessionId(sessionId: string): void {
    this.sessionId = sessionId;
  }

  getSessionId(): string {
    return this.sessionId;
  }

  private getHeaders(options: FunctionCallOptions): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add session ID header for tracking
    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
    }

    // Add any custom headers
    if (options.headers) {
      Object.assign(headers, options.headers);
    }

    return headers;
  }

  async callFunction<T = any>(
    functionName: string,
    data?: any,
    options: FunctionCallOptions = {}
  ): Promise<NetlifyFunctionResponse<T>> {
    const { timeout = 30000, retries = 3, headers = {} } = options;

    if (!this.baseUrl) {
      return {
        success: false,
        error: 'Netlify Functions URL not configured',
      };
    }

    const url = `${this.baseUrl}/${functionName}`;
    const requestHeaders = this.getHeaders(options);

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(url, {
          method: 'POST',
          headers: requestHeaders,
          body: data ? JSON.stringify(data) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const result = await response.json();
        return {
          success: true,
          data: result,
          statusCode: response.status,
        };
      } catch (error) {
        lastError = error as Error;
        console.warn(`Function call attempt ${attempt + 1} failed:`, error);

        if (attempt < retries) {
          // Exponential backoff
          const delay = Math.pow(2, attempt) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    return {
      success: false,
      error: lastError?.message || 'Unknown error occurred',
    };
  }

  // Specific function calls for different backend operations
  async processComplexTask(taskData: {
    type: string;
    parameters: Record<string, any>;
    priority?: 'low' | 'medium' | 'high';
  }): Promise<NetlifyFunctionResponse> {
    return this.callFunction('process-complex-task', taskData);
  }

  async generateReport(reportData: {
    template: string;
    data: Record<string, any>;
    format?: 'pdf' | 'excel' | 'json';
  }): Promise<NetlifyFunctionResponse<{ url: string }>> {
    return this.callFunction('generate-report', reportData);
  }

  async performDataAnalysis(analysisData: {
    dataset: string;
    analysisType: string;
    parameters?: Record<string, any>;
  }): Promise<NetlifyFunctionResponse> {
    return this.callFunction('data-analysis', analysisData);
  }

  async integrateWithExternalService(serviceData: {
    service: string;
    action: string;
    parameters: Record<string, any>;
  }): Promise<NetlifyFunctionResponse> {
    return this.callFunction('external-service-integration', serviceData);
  }

  async scheduleTask(taskData: {
    taskType: string;
    scheduledTime: string;
    parameters: Record<string, any>;
    recurring?: boolean;
  }): Promise<NetlifyFunctionResponse<{ taskId: string }>> {
    return this.callFunction('schedule-task', taskData);
  }

  async getTaskStatus(taskId: string): Promise<NetlifyFunctionResponse> {
    return this.callFunction('get-task-status', { taskId });
  }

  async cancelTask(taskId: string): Promise<NetlifyFunctionResponse> {
    return this.callFunction('cancel-task', { taskId });
  }

  async uploadFile(fileData: {
    filename: string;
    contentType: string;
    data: string; // Base64 encoded
    path?: string;
  }): Promise<NetlifyFunctionResponse<{ url: string }>> {
    return this.callFunction('upload-file', fileData);
  }

  async processDocument(documentData: {
    documentUrl: string;
    processingType: 'extract' | 'analyze' | 'convert';
    options?: Record<string, any>;
  }): Promise<NetlifyFunctionResponse> {
    return this.callFunction('process-document', documentData);
  }

  async sendNotification(notificationData: {
    recipient: string;
    subject?: string;
    message: string;
    type?: 'email' | 'sms' | 'push';
  }): Promise<NetlifyFunctionResponse> {
    return this.callFunction('send-notification', notificationData);
  }

  // Health check for Netlify Functions
  async healthCheck(): Promise<NetlifyFunctionResponse<{ status: string; timestamp: string }>> {
    return this.callFunction('health-check', {}, { timeout: 5000, retries: 1 });
  }

  // Batch function calls
  async batchCall<T = any>(
    calls: Array<{
      functionName: string;
      data?: any;
      options?: FunctionCallOptions;
    }>
  ): Promise<Array<NetlifyFunctionResponse<T>>> {
    const promises = calls.map(call =>
      this.callFunction<T>(call.functionName, call.data, call.options)
    );

    return Promise.all(promises);
  }

  // Streaming function calls (for real-time responses)
  async streamFunction(
    functionName: string,
    data?: any,
    onChunk?: (chunk: string) => void,
    options: FunctionCallOptions = {}
  ): Promise<NetlifyFunctionResponse> {
    const { timeout = 60000 } = options;

    if (!this.baseUrl) {
      return {
        success: false,
        error: 'Netlify Functions URL not configured',
      };
    }

    try {
      const authHeaders = await this.getAuthHeaders();
      const url = `${this.baseUrl}/${functionName}`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...authHeaders,
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: data ? JSON.stringify(data) : undefined,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Response body is not readable');
      }

      let fullResponse = '';

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          fullResponse += chunk;

          if (onChunk) {
            onChunk(chunk);
          }
        }
      } finally {
        reader.releaseLock();
      }

      return {
        success: true,
        data: fullResponse,
      };
    } catch (error) {
      console.error('Stream function error:', error);
      return {
        success: false,
        error: (error as Error).message,
      };
    }
  }

  getServiceStatus(): { configured: boolean; baseUrl: string } {
    return {
      configured: !!this.baseUrl,
      baseUrl: this.baseUrl,
    };
  }
}

export default NetlifyService;