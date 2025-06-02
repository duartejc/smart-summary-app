# Smart Summary Backend (FastAPI)

A high-performance backend service for the Smart Summary application, built with FastAPI and supporting multiple AI providers.

## Features

- 🚀 FastAPI for high-performance API endpoints
- 🔒 JWT-based authentication
- 🛡️ Rate limiting and API key protection
- 🤖 Support for multiple AI providers (OpenAI, Anthropic, Gemini)
- 📊 Usage tracking and analytics
- 🗄️ MongoDB for data persistence
- 📝 Langfuse integration for prompt management and analytics

## Prerequisites

- Python 3.8+
- MongoDB (local or remote)
- Python virtual environment (recommended)
- API keys for the AI providers you want to use

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/duartejc/smart-summary-app.git
   cd smart-summary-app/backend
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Then edit the `.env` file with your configuration.

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access the API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication

- `POST /api/auth/token` - Get an access token
- `GET /api/auth/me` - Get current user info

### AI Services

- `POST /api/ai/generate` - Generate AI response

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secret key for JWT token signing | - |
| `ALGORITHM` | Algorithm for JWT | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | 1440 (24h) |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `GEMINI_API_KEY` | Google Gemini API key | - |

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
```

### Linting

```bash
flake8
```

## Deployment

### Using Docker

```bash
docker build -t smart-summary-backend .
docker run -d -p 8000:8000 --env-file .env smart-summary-backend
```

### Production Deployment

For production deployment, consider using:

- Gunicorn with Uvicorn workers
- Reverse proxy (Nginx, Traefik)
- Process manager (systemd, Supervisor)
- Container orchestration (Kubernetes, Docker Swarm)

## License

MIT