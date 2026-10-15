# The News Analysost 📈

**The News Analysost** is a "Goated" AI-powered business intelligence dashboard built with Streamlit. it transforms complex newsletters, articles, and PDF reports into high-signal actionable intelligence.

## 🌟 Key Features

- **Multi-Source Input**: Paste raw text, enter article URLs, or upload PDF/TXT files.
- **AI-Powered Analysis**: Uses Google Gemini (`gemini-flash-latest`) to extract:
  - Importance Score (1-10)
  - Executive Summary & Market Impact
  - Key Highlights & Industry Builders
- **Specialized Industry Intel**: Automatically extracts targeted insights for **Interior Designers, Architects, and Luxury Real Estate** players.
- **Live Market Intelligence**: Proactively scans the global web via NewsAPI to find related latest and historical news to provide a 360-degree view.
- **Dynamic Configuration**: Securely manage your API keys directly from the dashboard or via environment variables.

## 🛠️ Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SKsiddhant/newsletter-analysis.git
   cd newsletter-analysis/streamlit_app
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Keys**:
   Create a `.env` file in the `streamlit_app` directory:
   ```env
   GEMINI_API_KEY=your_key_here
   NEWS_API_KEY=your_key_here
   ```
   *Note: You can also enter these keys directly in the dashboard sidebar.*

4. **Run the App**:
   ```bash
   streamlit run app.py
   ```

## 🏗️ Project Structure
- `app.py`: The main unified Streamlit application.
- `helpers.py`: Pure helper functions (HTML escaping, URL validation, response parsing).
- `tests/`: `pip install -r requirements-dev.txt && pytest` (offline; Gemini and NewsAPI are faked).
- `requirements.txt`: Python dependencies.
- `.env`: (Local only) API key storage.

## 🛡️ Security
Model output and NewsAPI fields are HTML-escaped before display, article URLs must resolve to public addresses, and the NewsAPI key is sent in a header. This project uses `.env` files and Streamlit session state to manage secrets. Never commit your `.env` file to public repositories.
