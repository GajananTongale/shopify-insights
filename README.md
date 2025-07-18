# Shopify Insights Fetcher API

A robust FastAPI application that extracts comprehensive insights from Shopify stores and e-commerce websites using web scraping and AI-powered analysis.

## Features

### Mandatory Features ✅
- **Product Catalog Extraction**: Complete product listings with details
- **Hero Products**: Featured products from homepage
- **Privacy & Refund Policies**: Automated policy extraction
- **FAQs**: AI-powered FAQ extraction and structuring
- **Social Media Handles**: Instagram, Facebook, Twitter, TikTok, etc.
- **Contact Details**: Email addresses and phone numbers
- **Brand Context**: About us and brand story extraction
- **Important Links**: Order tracking, contact us, blogs, etc.

### Bonus Features 🎯
- **Competitor Analysis**: AI-powered competitor identification and analysis
- **MySQL Database**: Persistent storage for all insights
- **Similarity Scoring**: Calculate similarity between brands
- **Historical Data**: Track and retrieve past analyses

## Technology Stack

- **Backend**: FastAPI with Python 3.11+
- **Database**: MySQL 8.0 with SQLAlchemy ORM
- **AI/ML**: Google Gemini AI for content structuring
- **Web Scraping**: httpx + BeautifulSoup4
- **Validation**: Pydantic models
- **Deployment**: Docker & Docker Compose

## Installation

### Prerequisites
- Python 3.11+
- MySQL 8.0
- Google AI API Key

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd shopify-insights-fetcher
```

2. **Create virtual environment**
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
# Edit .env with your configuration
```

5. **Run with Docker (Recommended)**
```bash
docker-compose up --build
```

6. **Or run locally**
```bash
# Start MySQL database
# Update DATABASE_URL in .env
uvicorn main:app --reload
```

## API Endpoints

### Core Endpoints

#### 1. Extract Brand Insights
```bash
POST /api/v1/insights
Content-Type: application/json

{
  "website_url": "https://memy.co.in",
  "include_competitors": false
}
```

**Response**: Complete brand insights including products, policies, FAQs, etc.

#### 2. Competitor Analysis (Bonus)
```bash
POST /api/v1/insights/competitors
Content-Type: application/json

{
  "website_url": "https://memy.co.in"
}
```

**Response**: Brand insights + competitor analysis with similarity scores

#### 3. Get Insights History
```bash
GET /api/v1/insights/history?limit=10
```

#### 4. Get Specific Insight
```bash
GET /api/v1/insights/{insight_id}
```

#### 5. Health Check
```bash
GET /api/v1/health
```

## API Documentation

Once running, access interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Using Postman
1. Import the API collection (create from OpenAPI spec at `/openapi.json`)
2. Test with sample Shopify stores:
   - `https://memy.co.in`
   - `https://hairoriginals.com`
   - `https://colourpop.com`

### Using curl
```bash
# Test basic insights extraction
curl -X POST "http://localhost:8000/api/v1/insights" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'

# Test competitor analysis
curl -X POST "http://localhost:8000/api/v1/insights/competitors" \
  -H "Content-Type: application/json" \
  -d '{"website_url": "https://memy.co.in"}'
```

## Architecture

### Project Structure
```
├── app/
│   ├── api/v1/endpoints/     # API route handlers
│   ├── core/                 # Configuration, database, exceptions
│   ├── models/               # Pydantic schemas
│   └── services/             # Business logic
├── docker-compose.yml        # Docker setup
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
└── main.py                  # FastAPI application
```

### Key Components

1. **WebScraper**: Handles HTTP requests and HTML parsing
2. **LLMService**: AI-powered content extraction and structuring
3. **InsightsService**: Orchestrates the complete extraction process
4. **CompetitorService**: Bonus feature for competitor analysis

## Best Practices Implemented

- **SOLID Principles**: Single responsibility, dependency injection
- **Clean Architecture**: Separated concerns with clear layers
- **Error Handling**: Comprehensive exception handling
- **Logging**: Structured logging throughout the application
- **Validation**: Pydantic models for data validation
- **Async/Await**: Non-blocking operations for better performance
- **Database Persistence**: MySQL with SQLAlchemy ORM
- **Docker Support**: Easy deployment and scaling

## Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Required for AI-powered extraction
- `DATABASE_URL`: MySQL connection string
- `ENVIRONMENT`: development/production
- `HTTP_TIMEOUT`: Request timeout (default: 30s)
- `LLM_TIMEOUT`: AI processing timeout (default: 60s)

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `404`: Website not found
- `422`: Validation error
- `500`: Internal server error

## Rate Limiting

Built-in rate limiting to prevent abuse:
- 100 requests per hour per IP (configurable)
- Graceful degradation on rate limit exceeded

## Future Enhancements

- [ ] Redis caching for improved performance
- [ ] Background job processing with Celery
- [ ] Advanced competitor analysis algorithms
- [ ] Real-time updates and webhooks
- [ ] Multi-language support
- [ ] Advanced analytics dashboard

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for detailed error information
3. Create an issue in the repository 