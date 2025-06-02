# System Context Diagram

```mermaid
graph TD
Client[Client Applications] -->|REST API| AIS[AI Service]
AIS -->|API Calls| OAI[OpenAI]
AIS -->|API Calls| ANT[Anthropic]
AIS -->|Analytics| LF[Langfuse]
style AIS fill:#f9f,stroke:#333,stroke-width:4px
```
