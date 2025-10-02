# AI Content Intelligence Platform

> An intelligent content analysis platform that detects misinformation, assesses risk levels, and provides comprehensive verification through external APIs and human review workflows.

## 🚀 Features

- **Content Analysis**: Advanced AI-powered content parsing and categorization
- **Risk Assessment**: Dynamic risk scoring using LLM-based evaluation
- **External Verification**: Integration with NewsAPI and Google Fact Check APIs
- **Interactive Workflow**: Visual pipeline representation using LangGraph
- **Export Capabilities**: Download analysis results in JSON format
- **Real-time Processing**: Streamlit-based interactive interface

## 📋 Prerequisites

- Python 3.8+
- OpenRouter API key (for LLM access)
- NewsAPI key (optional, for related articles)
- Google Fact Check API key (optional, for claim verification)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-content-intelligence.git
   cd ai-content-intelligence
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Required
   OPENROUTER_API_KEY=sk-or-v1-your-key-here

   # Optional (for enhanced features)
   NEWS_API_KEY=your-newsapi-key
   GOOGLE_API_KEY=your-google-api-key

   # App Settings
   ENVIRONMENT=development
   DEBUG_MODE=true
   ```

## 🎯 Quick Start

1. **Run the application**
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to `http://localhost:8501`

3. **Paste content** for analysis in the text area

4. **Review results** including risk assessment and verification data

## 📊 How It Works

The platform processes content through a structured pipeline:

1. **Content Ingestion** - Text input and initial processing
2. **AI Analysis** - LLM-powered content categorization and entity extraction
3. **Risk Assessment** - Dynamic risk scoring based on content patterns
4. **External Verification** - Cross-reference with news sources and fact-checkers
5. **Report Generation** - Comprehensive analysis output with export options

## 🔑 API Keys Setup

### NewsAPI
1. Visit [newsapi.org](https://newsapi.org)
2. Register for a free account
3. Copy your API key to `.env`

### Google Fact Check API
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create/select a project
3. Enable "Fact Check Tools API"
4. Create an API key (not OAuth client)
5. Add key to `.env`

### OpenRouter
1. Visit [openrouter.ai](https://openrouter.ai)
2. Sign up and get your API key
3. Add to `.env` file

## 📁 Project Structure

```
ai-content-intelligence/
├── app.py                 # Main Streamlit application
├── src/
│   ├── nodes.py          # Processing pipeline nodes
│   ├── config.py         # Configuration and API clients
│   ├── utils.py          # Utility functions
│   ├── error_handler.py  # Error handling utilities
│   └── debug_tools.py    # Performance monitoring
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables (create this)
└── README.md           # This file
```

## 🛠️ Configuration

The application supports various configuration options through environment variables:

- `OPENROUTER_API_KEY`: Required for LLM functionality
- `NEWS_API_KEY`: Optional, enables related article fetching
- `GOOGLE_API_KEY`: Optional, enables fact-checking features
- `DEBUG_MODE`: Enables detailed logging and error reporting
- `ENVIRONMENT`: Set to 'production' for production deployments

## 📝 Usage Examples

### Basic Analysis
1. Launch the app
2. Paste content in the text area
3. Click "Analyze Content"
4. Review the generated risk assessment and categorization

### With External APIs
1. Configure API keys in `.env`
2. Run analysis as above
3. Additional verification data will appear automatically
4. Export results using the download button

## 🔍 Troubleshooting

### Common Issues

**"LLM unavailable" error**
- Check your OpenRouter API key
- Verify internet connection
- Check rate limits

**"API Issues" warnings**
- Verify API keys are correct format
- Check API quotas haven't been exceeded
- Ensure APIs are enabled in respective consoles

**Export not working**
- Refresh the page and try again
- Check browser download settings
- Verify analysis completed successfully

### Getting Help

1. Check the console output for error messages
2. Verify all API keys are properly configured
3. Ensure you're using supported Python version (3.8+)

## 🔗 Links

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [NewsAPI Documentation](https://newsapi.org/docs)
- [Google Fact Check API](https://developers.google.com/fact-check/tools/api)
- [Streamlit Documentation](https://docs.streamlit.io)

---
