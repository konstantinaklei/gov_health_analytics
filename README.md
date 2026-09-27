# Greek Public Health Analytics & ETL Pipeline (gov_health_analytics)

Data analytics & ETL pipeline based in open data from goverment (emvoliasmoi data.gov.gr). This project includes automated data cleaning with Pandas, analytical visualizations with Seaborn/Matplotlib and Executive Report with Google Gemini API.

---

The pipeline addresses real-world data quality issues (dirty open data scaffolding), applies cleaning and normalization rules, and automatically extracts executive insights:
1. Data Ingestion & Dirty Data Scaffolding: Simulates real-world open data anomalies (duplicate entries, missing values, mixed encodings/accents, unstandardized date formats).
2. Automated Cleaning Pipeline:
   - Deduplication.
   - Missing value handling.
   - Character normalization and accent removal (Unicode NFKD normalization).
   - Standardization of timestamps to ISO 8601.
3. Exploratory Data Analysis & Visual Analytics:
   - Data cleaning evaluation chart.
   - Regional vaccination trend analysis over time.
4. AI Executive Reporting Google Gemini API:
   - Structured schema extraction Pydantic schema validation.
   - Automated report generation in Markdown executive_report.md.

---

## Tech Stack

- Python 3.10+
- Pandas & NumPy: Data manipulation, cleaning, and aggregation.
- Matplotlib & Seaborn: Statistical visualization and visual asset export.
- Google GenAI SDK: LLM integration with structured JSON/schema generation.
- Pydantic: Strict schema validation for AI reporting.
- Python-dotenv: Environment variable security and management.

---

## Setup & Execution

### Clone the Repository
```bash
git clone [https://github.com/konstantinakle/gov_health_analytics.git](https://github.com/konstantinakle/gov_health_analytics.git)
cd gov_health_analytics
```
### Virtual Environment
```bash
python -m venv .venv
# Windows (cmd):
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```
### Install Dependencies
```bash
pip install -r requirements.txt
```
### Configure Environment Variables
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```
### Run the Pipeline
```bash
python etl_pipeline.py
```
