# Component View

## Core Components

- AIController
  - Handles HTTP requests
  - Input validation
  - Rate limiting
  - Authentication
- AIService
  - Business logic orchestration
  - Model selection
  - Fallback handling
  - Response processing
- Provider Services
  - OpenAIService: OpenAI integration
  - AnthropicService: Anthropic integration
  - Provider-specific error handling
- LangfuseService
  - Prompt management
  - Performance tracking
  - Analytics integration
- Security Components
  - ApiKeyGuard
  - API key validation
  - Request authentication
  - ThrottleGuard
  - Rate limiting
  - Request tracking by API key/IP
- Configuration
  - Environment-based settings
  - Model configurations
  - API credentials