# AI Service Architecture Documentation

## Table of Contents
1. [System Context](#system-context)
2. [Container View](#container-view)
3. [Component View](#component-view)
4. [Code View](#code-view)

## System Context

Our AI Service acts as a middleware between client applications and various AI providers (OpenAI, Anthropic). It provides:
- Unified API access to multiple AI models
- Fallback mechanisms
- Rate limiting and security
- Observability through Langfuse

### Key Users
- Client Applications
- API Consumers
- System Administrators

### External Dependencies
- OpenAI API
- Anthropic API
- Langfuse Analytics

[View Context Diagram](./diagrams/context.md) 