import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import PyPDF2
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import io

# Load environment variables
load_dotenv()

# --- API Key Management ---
if "GEMINI_API_KEY" not in st.session_state:
    st.session_state.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or ""
if "NEWS_API_KEY" not in st.session_state:
    st.session_state.NEWS_API_KEY = os.getenv("NEWS_API_KEY") or ""

def check_api_keys():
    with st.sidebar.expander("⚙️ API Settings", expanded=False):
        st.markdown("Configure your keys here if not set in `.env`")
        
        # Gemini Key
        temp_gemini = st.text_input(
            "Google Gemini API Key", 
            value=st.session_state.GEMINI_API_KEY, 
            type="password",
            help="Get it from Google AI Studio"
        )
        if temp_gemini != st.session_state.GEMINI_API_KEY:
            st.session_state.GEMINI_API_KEY = temp_gemini
            st.rerun()

        # NewsAPI Key
        temp_news = st.text_input(
            "NewsAPI Key", 
            value=st.session_state.NEWS_API_KEY, 
            type="password",
            help="Get it from newsapi.org"
        )
        if temp_news != st.session_state.NEWS_API_KEY:
            st.session_state.NEWS_API_KEY = temp_news
            st.rerun()

    if st.session_state.GEMINI_API_KEY:
        genai.configure(api_key=st.session_state.GEMINI_API_KEY)
    
    return bool(st.session_state.GEMINI_API_KEY)

# --- Utility Functions ---

def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = "\n".join([p.get_text() for p in paragraphs])
        return text
    except Exception as e:
        st.error(f"Error fetching URL: {e}")
        return None

def analyze_news(text):
    if not st.session_state.GEMINI_API_KEY:
        st.error("Gemini API Key is missing!")
        return None

    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = f"""
    You are an expert business and lifestyle analyst. Analyze the following news/newsletter text and extract key information.
    
    Requirements:
    1. Rate the importance of this news for a business platform on a scale of 1-10.
    2. Provide a concise summary.
    3. Describe the potential market impact.
    4. List the key builders, companies, and industries mentioned.
    5. List 3-5 key highlights.
    6. Generate 3-5 highly relevant search keywords/phrases to find related latest or historical news.
    7. EXTRACT SPECIALIZED INTEL for Interior Designers, Architects, and Luxury Real Estate players. 
       - Look for premium housing launches, architectural trends, furniture/decor industry moves, and art ecosystem shifts.

    Format your response ONLY as a JSON object with the following structure:
    {{
      "importanceScore": number,
      "summary": "string",
      "marketImpact": "string",
      "buildersAndIndustries": ["string"],
      "keyHighlights": ["string"],
      "searchKeywords": ["string"],
      "designAndRealEstateIntel": {{
          "opportunities": ["string"],
          "trends": ["string"],
          "keyProjects": ["string"]
      }}
    }}

    Text to analyze:
    ---
    {text}
    ---
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Robust JSON extraction
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            st.error("Could not find JSON in AI response.")
            st.code(content)
            return None
    except Exception as e:
        st.error(f"Analysis failed: {e}")
        return None

def fetch_related_news(keywords):
    if not st.session_state.NEWS_API_KEY:
        st.sidebar.info("ℹ️ NewsAPI Key missing. External news fetching disabled.")
        return []
    
    query = " OR ".join(keywords)
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=relevancy&pageSize=5&apiKey={st.session_state.NEWS_API_KEY}&language=en"
    
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") == "ok":
            return data.get("articles", [])
        return []
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return []

# --- Streamlit UI ---

st.set_page_config(page_title="BizPulse Analyst", page_icon="📈", layout="wide")

# Custom CSS for a modern look
st.markdown("""
    <style>
    .main {
        background-color: #f4f7f6;
    }
    .stButton>button {
        width: 100%;
        background-color: #004a99;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 0.5rem;
    }
    .stButton>button:hover {
        background-color: #003366;
        color: white;
    }
    .importance-badge {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .high { background-color: #fee2e2; color: #991b1b; }
    .med { background-color: #fef3c7; color: #92400e; }
    .low { background-color: #dcfce7; color: #166534; }
    
    .news-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 5px solid #004a99;
    }
    .tag {
        background-color: #e0f2fe;
        color: #0369a1;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        margin-right: 5px;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 BizPulse Analyst")
st.subheader("AI-powered business insights from any news source")

# Setup Keys
keys_ready = check_api_keys()

# Input Section
with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        input_type = st.radio("Choose Input Method:", ["Paste Text", "Article URL", "Upload File"], horizontal=True)
        
        input_data = None
        if input_type == "Paste Text":
            input_data = st.text_area("Paste your newsletter or news text here:", height=250)
        elif input_type == "Article URL":
            url = st.text_input("Enter article URL:")
            if url:
                with st.spinner("Extracting text..."):
                    input_data = extract_text_from_url(url)
        else:
            uploaded_file = st.file_uploader("Upload PDF or TXT file:", type=["pdf", "txt"])
            if uploaded_file:
                if uploaded_file.type == "application/pdf":
                    input_data = extract_text_from_pdf(uploaded_file)
                else:
                    input_data = uploaded_file.read().decode("utf-8")

    with col2:
        st.info("💡 **Tips:**\n- Paste a whole newsletter for a full industry breakdown.\n- Use URLs from sites like Bloomberg or TechCrunch.\n- Upload complex PDF reports for deep analysis.")
        if st.button("Analyze News", disabled=not keys_ready):
            if not input_data:
                st.warning("Please provide some input first!")
            else:
                st.session_state.analysis_requested = True
                st.session_state.input_text = input_data

# Results Section
if keys_ready and "analysis_requested" in st.session_state and st.session_state.analysis_requested:
    with st.spinner("Our AI is scanning the markets..."):
        result = analyze_news(st.session_state.input_text)
        
        if result:
            st.divider()
            
            # Importance Score
            score = result['importanceScore']
            score_class = "high" if score >= 8 else "med" if score >= 5 else "low"
            st.markdown(f'<div class="importance-badge {score_class}">Importance Score: {score}/10</div>', unsafe_allow_html=True)
            
            # Summary & Highlights
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("### 📝 Executive Summary")
                st.write(result['summary'])
                
                st.markdown("### 🚀 Market Impact")
                st.write(result['marketImpact'])
                
            with col_b:
                st.markdown("### ✨ Key Highlights")
                for highlight in result['keyHighlights']:
                    st.markdown(f"- {highlight}")
                
                st.markdown("### 🏗️ Builders & Industries")
                html_tags = "".join([f'<span class="tag">{tag}</span>' for tag in result['buildersAndIndustries']])
                st.markdown(html_tags, unsafe_allow_html=True)

            # Specialized Design & Real Estate Section
            if 'designAndRealEstateIntel' in result:
                st.divider()
                st.markdown("### 🏠 Design & Real Estate Intelligence")
                
                d_col1, d_col2, d_col3 = st.columns(3)
                
                with d_col1:
                    st.markdown("#### 🎯 Opportunities")
                    for opp in result['designAndRealEstateIntel'].get('opportunities', []):
                        st.markdown(f"- {opp}")
                
                with d_col2:
                    st.markdown("#### 📈 Industry Trends")
                    for trend in result['designAndRealEstateIntel'].get('trends', []):
                        st.markdown(f"- {trend}")
                        
                with d_col3:
                    st.markdown("#### 🏗️ Key Projects")
                    for proj in result['designAndRealEstateIntel'].get('keyProjects', []):
                        st.markdown(f"- {proj}")

            # Related Market Intel
            st.divider()
            st.header("🌐 Related Market Intel")
            st.caption("Latest and relevant news from around the web")
            
            with st.spinner("Fetching global market data..."):
                related_news = fetch_related_news(result['searchKeywords'])
                
                if related_news:
                    for article in related_news:
                        with st.container():
                            st.markdown(f"""
                                <div class="news-card">
                                    <div style="font-size: 0.8rem; color: #00a8cc; font-weight: bold; text-transform: uppercase;">{article['source']['name'] if isinstance(article['source'], dict) else article['source']}</div>
                                    <div style="font-size: 1.1rem; font-weight: bold; color: #004a99; margin: 5px 0;">{article['title']}</div>
                                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 10px;">{article['description'][:200] if article['description'] else 'No description available'}...</div>
                                    <a href="{article['url']}" target="_blank" style="color: #004a99; text-decoration: none; font-weight: bold;">Read Full Article →</a>
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No related external news found at this time.")
        
        st.session_state.analysis_requested = False

st.sidebar.markdown("---")
st.sidebar.markdown("### About BizPulse")
st.sidebar.write("Developed to help you stay ahead of the market by distilling complex newsletters into actionable intelligence.")
st.sidebar.info("Using Gemini 1.5 Flash & NewsAPI")
