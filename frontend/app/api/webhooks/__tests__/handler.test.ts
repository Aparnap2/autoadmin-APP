import handler from '../handler';
import { createMockRequest, createMockResponse, createMockSupabaseClient } from '../../../../jest.setup';

// Mock the Supabase client
const mockSupabase = createMockSupabaseClient();
jest.mock('../../../../lib/supabase', () => ({
  createServerSupabaseClient: jest.fn(() => mockSupabase)
}));

// Mock crypto for webhook signature verification
jest.mock('crypto', () => ({
  createHmac: jest.fn(() => ({
    update: jest.fn().mockReturnThis(),
    digest: jest.fn(() => 'mock-signature-hex')
  })),
  timingSafeEqual: jest.fn((a, b) => {
    return Buffer.compare(a, b) === 0;
  })
}));

describe('Webhook Handler API', () => {
  let mockReq, mockRes;

  beforeEach(() => {
    mockReq = createMockRequest();
    mockRes = createMockResponse();
    jest.clearAllMocks();
  });

  describe('HTTP Method Validation', () => {
    it('should reject non-POST requests', async () => {
      mockReq.method = 'GET';

      await handler(mockReq, mockRes);

      expect(mockRes.statusCode).toBe(405);
      expect(mockRes.data).toEqual({
        success: false,
        error: 'Method not allowed. Use POST.'
      });
    });

    it('should accept POST requests', async () => {
      mockReq.method = 'POST';
      mockReq.body = { test: 'data' };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      expect(mockRes.statusCode).toBe(200);
      expect(mockRes.data.success).toBe(true);
    });
  });

  describe('Signature Verification', () => {
    it('should verify webhook signature when provided', async () => {
      process.env.WEBHOOK_SECRET = 'test-secret';

      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-signature': 'mock-signature-hex',
        'x-webhook-source': 'github'
      };
      mockReq.body = { test: 'data' };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      expect(require('crypto').createHmac).toHaveBeenCalledWith('sha256', 'test-secret');
    });

    it('should reject invalid webhook signatures', async () => {
      process.env.WEBHOOK_SECRET = 'test-secret';

      const crypto = require('crypto');
      crypto.timingSafeEqual.mockReturnValue(false); // Invalid signature

      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-signature': 'invalid-signature',
        'x-webhook-source': 'github'
      };
      mockReq.body = { test: 'data' };

      await handler(mockReq, mockRes);

      expect(mockRes.statusCode).toBe(401);
      expect(mockRes.data.error).toBe('Invalid webhook signature');
    });

    it('should process webhooks without signature', async () => {
      mockReq.method = 'POST';
      mockReq.body = { test: 'data' };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      expect(mockRes.statusCode).toBe(200);
      expect(mockRes.data.success).toBe(true);
    });
  });

  describe('GitHub Webhook Processing', () => {
    it('should handle GitHub push events', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'github',
        'x-github-event': 'push'
      };
      mockReq.body = {
        ref: 'refs/heads/main',
        repository: { full_name: 'test/repo' },
        commits: [{}, {}, {}],
        sender: { login: 'testuser' }
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      expect(mockSupabase.from).toHaveBeenCalledWith('webhook_events');
      expect(mockSupabase.from().insert).toHaveBeenCalledWith(
        expect.objectContaining({
          source: 'github',
          event: 'push',
          payload: expect.any(Object)
        })
      );
    });

    it('should handle GitHub PR opened events', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'github',
        'x-github-event': 'pull_request'
      };
      mockReq.body = {
        action: 'opened',
        repository: { full_name: 'test/repo' },
        pull_request: {
          number: 123,
          title: 'Add new feature',
          user: { login: 'testuser' }
        }
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('github_pr_opened');
      expect(insertCall.processed_data.triggerAgent).toBe(true);
    });

    it('should handle GitHub issue opened events', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'github',
        'x-github-event': 'issues'
      };
      mockReq.body = {
        action: 'opened',
        repository: { full_name: 'test/repo' },
        issue: {
          number: 456,
          title: 'Bug report',
          user: { login: 'testuser' }
        }
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('github_issue_opened');
      expect(insertCall.processed_data.triggerAgent).toBe(true);
    });

    it('should handle GitHub PR merged events', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'github',
        'x-github-event': 'pull_request'
      };
      mockReq.body = {
        action: 'closed',
        repository: { full_name: 'test/repo' },
        pull_request: {
          number: 789,
          merged: true,
          title: 'Merged feature'
        }
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('github_pr_merged');
      expect(insertCall.processed_data.triggerAgent).toBe(false);
    });
  });

  describe('HubSpot Webhook Processing', () => {
    it('should handle HubSpot contact creation events', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'hubspot'
      };
      mockReq.body = {
        eventType: 'contact.creation',
        objectId: 'contact-123'
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('hubspot_contact_created');
      expect(insertCall.processed_data.triggerAgent).toBe(true);
      expect(insertCall.processed_data.agentType).toBe('marketing');
    });

    it('should handle HubSpot deal creation events', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'hubspot'
      };
      mockReq.body = {
        eventType: 'deal.creation',
        objectId: 'deal-456'
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('hubspot_deal_created');
      expect(insertCall.processed_data.triggerAgent).toBe(true);
      expect(insertCall.processed_data.agentType).toBe('finance');
    });

    it('should handle HubSpot deal stage changes', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'hubspot'
      };
      mockReq.body = {
        eventType: 'deal.stage_change',
        objectId: 'deal-789',
        propertyName: 'dealstage',
        propertyValue: 'closedwon'
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('hubspot_deal_stage_changed');
      expect(insertCall.processed_data.newStage).toBe('closedwon');
      expect(insertCall.processed_data.triggerAgent).toBe(true);
    });
  });

  describe('Monitoring Webhook Processing', () => {
    it('should handle monitoring alerts', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'monitoring'
      };
      mockReq.body = {
        alertType: 'uptime',
        service: 'api-server',
        status: 'down',
        message: 'API server is not responding'
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('monitoring_alert');
      expect(insertCall.processed_data.triggerAgent).toBe(true);
      expect(insertCall.processed_data.agentType).toBe('devops');
      expect(insertCall.processed_data.priority).toBe('high');
    });
  });

  describe('Generic Webhook Processing', () => {
    it('should handle generic webhooks from unknown sources', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'unknown-service'
      };
      mockReq.body = {
        event: 'generic.event',
        data: { some: 'data' }
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      const insertCall = mockSupabase.from().insert.mock.calls[0][0];
      expect(insertCall.processed_data.type).toBe('generic_webhook');
      expect(insertCall.processed_data.source).toBe('unknown-service');
      expect(insertCall.processed_data.triggerAgent).toBe(false);
    });
  });

  describe('Database Operations', () => {
    it('should store webhook events in database', async () => {
      mockReq.method = 'POST';
      mockReq.body = {
        test: 'data',
        event: 'test.event'
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      expect(mockSupabase.from).toHaveBeenCalledWith('webhook_events');
      expect(mockSupabase.from().insert).toHaveBeenCalledWith(
        expect.objectContaining({
          source: 'unknown',
          event: 'generic',
          payload: { test: 'data', event: 'test.event' }
        })
      );
    });

    it('should continue processing even if database storage fails', async () => {
      mockReq.method = 'POST';
      mockReq.body = { test: 'data' };

      mockSupabase.from().insert().mockResolvedValue({
        error: new Error('Database error')
      });

      await handler(mockReq, mockRes);

      // Should still return success
      expect(mockRes.statusCode).toBe(200);
      expect(mockRes.data.success).toBe(true);
    });
  });

  describe('Task Triggering', () => {
    it('should create agent task when triggerAgent is true', async () => {
      mockReq.method = 'POST';
      mockReq.headers = {
        'x-webhook-source': 'github'
      };
      mockReq.body = {
        action: 'opened',
        repository: { full_name: 'test/repo' },
        pull_request: {
          number: 123,
          title: 'New PR',
          user: { login: 'testuser' }
        }
      };

      // Mock the webhook event insert
      mockSupabase.from.mockImplementation((table) => {
        if (table === 'webhook_events') {
          return {
            insert: jest.fn().mockResolvedValue({ error: null })
          };
        }
        if (table === 'tasks') {
          return {
            insert: jest.fn().mockResolvedValue({ error: null })
          };
        }
        return createMockSupabaseClient().from(table);
      });

      await handler(mockReq, mockRes);

      expect(mockSupabase.from).toHaveBeenCalledWith('tasks');
    });
  });

  describe('Error Handling', () => {
    it('should handle unexpected errors gracefully', async () => {
      mockReq.method = 'POST';
      mockReq.body = { test: 'data' };

      // Mock an unexpected error
      mockSupabase.from.mockImplementationOnce(() => {
        throw new Error('Unexpected error');
      });

      await handler(mockReq, mockRes);

      expect(mockRes.statusCode).toBe(500);
      expect(mockRes.data).toEqual({
        success: false,
        error: 'Internal server error'
      });
    });
  });

  describe('Success Response', () => {
    it('should return success response for processed webhook', async () => {
      mockReq.method = 'POST';
      mockReq.body = {
        event: 'test.success'
      };

      mockSupabase.from().insert().mockResolvedValue({ error: null });

      await handler(mockReq, mockRes);

      expect(mockRes.statusCode).toBe(200);
      expect(mockRes.data).toEqual({
        success: true,
        message: 'Webhook processed successfully'
      });
    });
  });
});