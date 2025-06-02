#Code Structure

## Directory Layout

src/
├── app.module.ts
├── main.ts
├── services/
│ ├── ai.service.ts
│ ├── anthropic.service.ts
│ ├── openai.service.ts
│ └── langfuse.service.ts
├── guards/
│ ├── api-key.guard.ts
│ └── throttle.guard.ts
├── controllers/
│ └── ai.controller.ts
├── types/
│ └── ai-provider.types.ts
├── config/
│ └── ai-models.config.ts

## Key Interfaces

### AIModelConfig
```typescript
interface AIModelConfig {
  provider: AIProvider;
  model: string;
  apiKey: string;
  maxTokens?: number;
  temperature?: number;
  reasoningEffort?: 'low' | 'medium' | 'high';
}
```

### Provider Configuration
```typescript
interface ProviderConfig {
  primary: AIModelConfig;
  fallback?: AIModelConfig;
}
```

## Security Implementation

Rate Limiting:
```typescript
@UseGuards(ApiKeyGuard, CustomThrottlerGuard)
@Throttle({ default: { limit: 10, ttl: 60000 } })
```

## Environment Configuration
Required environment variables:
```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
API_KEY=
```



