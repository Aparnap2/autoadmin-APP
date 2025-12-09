/**
 * API Endpoint for LLM Provider Management
 * Allows runtime switching and management of LLM providers
 */

import { LLMProviderFactory, LLMProviderConfig } from '../../../../services/agents/llm-provider/provider-factory';
import { runTask, createApiResponse } from '../../utils/expo-serverless';

// Initialize the provider system if not already done
let initialized = false;

async function ensureInitialized() {
  if (!initialized) {
    await runTask(async () => {
      try {
        await LLMProviderFactory.initialize();
        initialized = true;
      } catch (error) {
        console.error('Failed to initialize LLM Provider System:', error);
        throw error;
      }
    });
  }
}

export async function GET(request: Request) {
  try {
    await ensureInitialized();

    const { searchParams } = new URL(request.url);
    const action = searchParams.get('action');

    switch (action) {
      case 'status':
        const status = await LLMProviderFactory.getSystemStatus();
        return Response.json({
          success: true,
          data: status
        });

      case 'metrics':
        const metrics = LLMProviderFactory.getMetrics();
        return Response.json({
          success: true,
          data: metrics
        });

      case 'providers':
        const providers = {
          available: LLMProviderFactory.getMetrics(),
          primary: LLMProviderFactory.getPrimaryProvider().getProviderInfo()
        };
        return Response.json({
          success: true,
          data: providers
        });

      default:
        return Response.json({
          success: false,
          error: 'Invalid action. Use: status, metrics, or providers'
        }, { status: 400 });
    }
  } catch (error: any) {
    console.error('LLM Provider API GET error:', error);
    return Response.json({
      success: false,
      error: error.message || 'Internal server error'
    }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    await ensureInitialized();

    const body = await request.json();
    const action = body.action;

    switch (action) {
      case 'switch': {
        const { provider, apiKey, baseUrl, model, temperature, maxTokens } = body;

        if (!provider) {
          return Response.json({
            success: false,
            error: 'Provider name is required'
          }, { status: 400 });
        }

        const newConfig: LLMProviderConfig = {
          provider,
          apiKey: apiKey || process.env[`${provider.toUpperCase()}_API_KEY`] || '',
          model: model || 'default',
          temperature: temperature ?? 0.7,
          maxTokens: maxTokens ?? 2048,
          ...(baseUrl && { baseUrl })
        };

        await LLMProviderFactory.switchProvider(newConfig);

        return Response.json({
          success: true,
          message: `Switched to ${provider} provider`,
          data: {
            provider,
            model: newConfig.model,
            baseUrl: newConfig.baseUrl
          }
        });
      }

      case 'fallback': {
        const { enable, providers } = body;

        // Note: This would require extending the LLMProviderFactory to support runtime fallback configuration
        return Response.json({
          success: false,
          error: 'Fallback configuration changes require server restart'
        }, { status: 501 });
      }

      case 'reset_metrics': {
        const { provider } = body;
        LLMProviderFactory.resetMetrics(provider);

        return Response.json({
          success: true,
          message: provider ? `Reset metrics for ${provider}` : 'Reset all metrics'
        });
      }

      case 'health_check': {
        const primaryProvider = LLMProviderFactory.getPrimaryProvider();
        const isHealthy = await primaryProvider.healthCheck();

        return Response.json({
          success: true,
          data: {
            healthy: isHealthy,
            provider: primaryProvider.getProviderInfo()
          }
        });
      }

      default:
        return Response.json({
          success: false,
          error: 'Invalid action. Use: switch, fallback, reset_metrics, or health_check'
        }, { status: 400 });
    }
  } catch (error: any) {
    console.error('LLM Provider API POST error:', error);
    return Response.json({
      success: false,
      error: error.message || 'Internal server error'
    }, { status: 500 });
  }
}

/**
 * Default export for Expo/Next.js API route compatibility
 * This is needed for proper React component detection
 */
export default function handler() {
  // This is a placeholder export to satisfy Expo/Next.js requirements
  // The actual API functionality is handled by GET/POST methods
  return null;
}