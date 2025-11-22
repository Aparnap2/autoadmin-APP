import { POST } from '../trigger';
import { firebaseService } from '../../../../lib/firebase';

// Mock the Firebase service
jest.mock('../../../../lib/firebase', () => ({
  firebaseService: {
    createTask: jest.fn(),
    updateTaskStatus: jest.fn()
  }
}));

const mockFirebaseService = firebaseService as jest.Mocked<typeof firebaseService>;

// Mock fetch for GitHub API
global.fetch = jest.fn();

describe('Agent Trigger API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Request Validation', () => {
    it('should reject requests missing agentType', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          task: 'Test task'
        })
      });

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(400);
      expect(result).toEqual({
        success: false,
        error: 'Missing required fields: agentType, task'
      });
    });

    it('should reject requests missing task', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing'
        })
      });

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(400);
      expect(result).toEqual({
        success: false,
        error: 'Missing required fields: agentType, task'
      });
    });

    it('should reject invalid agent types', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'invalid',
          task: 'Test task'
        })
      });

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(400);
      expect(result.error).toContain('Invalid agentType');
    });

    it('should reject invalid priorities', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing',
          task: 'Test task',
          priority: 'invalid'
        })
      });

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(400);
      expect(result.error).toContain('Invalid priority');
    });
  });

  describe('Database Operations', () => {
    it('should create a task record in the database', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing',
          task: 'Create content about AI',
          priority: 'high'
        })
      });

      mockFirebaseService.createTask.mockResolvedValue({
        id: 'task-123',
        status: 'pending',
        agent_type: 'marketing',
        priority: 'high'
      } as any);

      (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true });

      const response = await POST(request);
      const result = await response.json();

      expect(mockFirebaseService.createTask).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'pending',
          input_prompt: 'Create content about AI',
          agent_type: 'marketing',
          priority: 'high'
        })
      );
      expect(response.status).toBe(200);
      expect(result.success).toBe(true);
    });

    it('should handle database errors gracefully', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing',
          task: 'Test task'
        })
      });

      mockFirebaseService.createTask.mockResolvedValue(null);

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(500);
      expect(result).toEqual({
        success: false,
        error: 'Failed to create task record'
      });
    });
  });

  describe('GitHub Integration', () => {
    beforeEach(() => {
      process.env.GITHUB_TOKEN = 'test-github-token';
      process.env.GITHUB_REPO_OWNER = 'test-owner';
      process.env.GITHUB_REPO_NAME = 'test-repo';
    });

    afterEach(() => {
      delete process.env.GITHUB_TOKEN;
      delete process.env.GITHUB_REPO_OWNER;
      delete process.env.GITHUB_REPO_NAME;
    });

    it('should trigger GitHub Action on successful task creation', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'devops',
          task: 'Review PR #123',
          priority: 'high'
        })
      });

      mockFirebaseService.createTask.mockResolvedValue({
        id: 'task-456'
      } as any);

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true
      });

      const response = await POST(request);

      expect(global.fetch).toHaveBeenCalledWith(
        'https://api.github.com/repos/test-owner/test-repo/dispatches',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'token test-github-token',
            'Content-Type': 'application/json'
          }),
          body: expect.stringContaining('"event_type":"start_task"')
        })
      );
      expect(response.status).toBe(200);
    });

    it('should handle GitHub API failures', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing',
          task: 'Test task'
        })
      });

      mockFirebaseService.createTask.mockResolvedValue({
        id: 'task-789'
      } as any);

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: jest.fn().mockResolvedValue('GitHub API Error')
      } as any);

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(500);
      expect(result.success).toBe(false);
    });
  });

  describe('Environment Configuration', () => {
    it('should handle missing GitHub configuration', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing',
          task: 'Test task'
        })
      });

      mockFirebaseService.createTask.mockResolvedValue({
        id: 'task-123'
      } as any);

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(500);
      expect(result.error).toBe('GitHub configuration missing');
    });
  });

  describe('Success Response', () => {
    beforeEach(() => {
      process.env.GITHUB_TOKEN = 'test-github-token';
      process.env.GITHUB_REPO_OWNER = 'test-owner';
      process.env.GITHUB_REPO_NAME = 'test-repo';
    });

    afterEach(() => {
      delete process.env.GITHUB_TOKEN;
      delete process.env.GITHUB_REPO_OWNER;
      delete process.env.GITHUB_REPO_NAME;
    });

    it('should return success response with task ID', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing',
          task: 'Create social media campaign'
        })
      });

      mockFirebaseService.createTask.mockResolvedValue({
        id: 'task-success-123'
      } as any);

      (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true });

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(200);
      expect(result).toEqual({
        success: true,
        taskId: 'task-success-123',
        message: 'marketing agent task triggered successfully'
      });
    });

    it('should include default priority when not specified', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'devops',
          task: 'Deploy to production'
        })
      });

      mockFirebaseService.createTask.mockResolvedValue({
        id: 'task-default-priority'
      } as any);

      (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true });

      await POST(request);

      expect(mockFirebaseService.createTask).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: 'medium' // Default priority
        })
      );
    });
  });

  describe('Error Handling', () => {
    it('should handle unexpected errors gracefully', async () => {
      const request = new Request('http://localhost/api/agents/trigger', {
        method: 'POST',
        body: JSON.stringify({
          agentType: 'marketing',
          task: 'Test task'
        })
      });

      mockFirebaseService.createTask.mockImplementationOnce(() => {
        throw new Error('Unexpected error');
      });

      const response = await POST(request);
      const result = await response.json();

      expect(response.status).toBe(500);
      expect(result).toEqual({
        success: false,
        error: 'Internal server error'
      });
    });
  });
});