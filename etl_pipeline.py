import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import unicodedata
import random
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class HealthAnalyticsReport(BaseModel):
    executive_summary: str = Field(description="Executive summary of the dataset and analysis")
    top_performing_regions: list[str] = Field(description="List of top performing regions based on total vaccinations")
    data_anomalies_detected: list[str] = Field(description="List of anomalies found in the data or data quality")
    strategic_recommendations: list[str] = Field(description="List of actionable recommendations based on analytics")

def remove_accents(input_str):
    if pd.isna(input_str) or not isinstance(input_str, str):
        return input_str
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def generate_dirty_data(num_rows=300):
    regions = ['Αττική', 'Θεσσαλονίκη', 'Κρήτη', 'Πελοπόννησος', 'Θεσσαλία', 'Ήπειρος']
    dirty_regions = [
        ' Αττική ', 'Αττικη', 'ΑΤΤΙΚΗ', 'αττικη',
        'Θεσσαλονικη  ', '  ΘΕΣΣΑΛΟΝΙΚΗ',
        'Κρήτη ', ' κρητη', 'κρητη'
    ]
    
    statuses = ['COMPLETED', 'PENDING', 'CANCELLED', 'UNKNOWN']
    
    data = []
    base_date = datetime(2023, 1, 1)
    
    for _ in range(num_rows):
        # 80% chance of clean region, 20% dirty
        if random.random() > 0.2:
            region = random.choice(regions)
        else:
            region = random.choice(dirty_regions)
            
        # 10% chance of NaN
        if random.random() < 0.1:
            region = np.nan
            
        date_obj = base_date + timedelta(days=random.randint(0, 150))
        # Mix date formats
        if random.random() < 0.3:
            date_str = date_obj.strftime("%d/%m/%Y")
        elif random.random() < 0.6:
            date_str = date_obj.strftime("%b %d, %Y")
        else:
            date_str = date_obj.strftime("%Y-%m-%d")
            
        if random.random() < 0.05:
            date_str = np.nan
            
        dose_1 = random.randint(100, 5000)
        dose_2 = int(dose_1 * random.uniform(0.5, 0.9))
        total_vaccinations = dose_1 + dose_2
        
        # introduce dirty numbers
        if random.random() < 0.1:
            dose_1 = -abs(dose_1) # negative
        if random.random() < 0.1:
             dose_2 = str(dose_2) # string
        if random.random() < 0.05:
            total_vaccinations = np.nan
            
        status = random.choice(statuses)
        
        data.append({
            'date': date_str,
            'region_el': region,
            'total_vaccinations': total_vaccinations,
            'dose_1': dose_1,
            'dose_2': dose_2,
            'status': status
        })
        
    df = pd.DataFrame(data)
    
    # Introduce duplicate rows (10% duplication)
    duplicates = df.sample(n=int(num_rows * 0.1), replace=True)
    df = pd.concat([df, duplicates], ignore_index=True)
    
    # Add complete random NaN row
    df.loc[len(df)] = [np.nan] * 6
    return df

def clean_data(df):
    metrics = {}
    initial_rows = len(df)
    
    # 1. Deduplicate
    df = df.drop_duplicates().copy()
    metrics['duplicates_dropped'] = initial_rows - len(df)
    
    initial_missing = df.isna().sum().to_dict()
    metrics['missing_before'] = sum(initial_missing.values())
    
    # 2. Standardize Greek region strings
    def clean_region(val):
        if pd.isna(val):
            return val
        val = str(val).strip()
        val = remove_accents(val).upper()
        return val
    
    df['region_el'] = df['region_el'].apply(clean_region)
    df['region_el'] = df['region_el'].fillna('UNKNOWN')
    
    # Handle the string "NAN" from str conversion if it happened
    df.loc[df['region_el'] == 'NAN', 'region_el'] = 'UNKNOWN'
    
    # 3. Clean numeric columns
    for col in ['total_vaccinations', 'dose_1', 'dose_2']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].abs()
        
    # Impute numeric missing values per region median, gracefully fallback to overall median
    for col in ['total_vaccinations', 'dose_1', 'dose_2']:
        region_medians = df.groupby('region_el')[col].transform('median')
        df[col] = df[col].fillna(region_medians)
        overall_median = df[col].median()
        df[col] = df[col].fillna(overall_median)
        df[col] = df[col].astype(int, errors='ignore')
        
    # 4. Standardize Dates
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date']).copy()
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    final_missing = df.isna().sum().to_dict()
    metrics['missing_after'] = sum(final_missing.values())
    metrics['rows_remaining'] = len(df)
    
    return df, metrics, initial_missing, final_missing

def generate_visualizations(df, initial_missing, final_missing):
    sns.set_theme(style="whitegrid")
    
    # Visualization 1: Data Cleaning Impact
    fig, ax = plt.subplots(figsize=(10, 6))
    categories = list(initial_missing.keys())
    before_vals = [initial_missing[c] for c in categories]
    after_vals = [final_missing.get(c, 0) for c in categories]
    
    x = np.arange(len(categories))
    width = 0.35
    
    ax.bar(x - width/2, before_vals, width, label='Before Cleaning', color='salmon')
    ax.bar(x + width/2, after_vals, width, label='After Cleaning', color='skyblue')
    
    ax.set_ylabel('Missing Values Count')
    ax.set_title('Impact of Data Cleaning Pipeline')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha="right")
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('data_cleaning_impact.png', dpi=300)
    plt.close()
    
    # Visualization 2: Vaccination Trends
    fig, ax = plt.subplots(figsize=(12, 6))
    top_regions = df.groupby('region_el')['total_vaccinations'].sum().nlargest(5).index
    df_top = df[df['region_el'].isin(top_regions)].copy()
    df_top['date'] = pd.to_datetime(df_top['date'])
    
    # Using errorbar=None due to deprecation of ci=None
    sns.lineplot(data=df_top, x='date', y='total_vaccinations', hue='region_el', marker='o', errorbar=None, ax=ax)
    
    ax.set_title('Vaccination Trends over Time (Top 5 Regions)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Total Vaccinations')
    
    plt.tight_layout()
    plt.savefig('vaccination_trends.png', dpi=300)
    plt.close()

def generate_ai_report(df, metrics):
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n⚠️ Warning: GEMINI_API_KEY environment variable not set. Skipping AI report generation.")
        return
         
    client = genai.Client(
        vertexai=True,
        project="586740474009",
        location="us-central1"
    )
    
    summary_data = {
        "metrics": metrics,
        "total_records": len(df),
        "total_vaccinations_sum": int(df['total_vaccinations'].sum()),
        "top_regions_summary": df.groupby('region_el')['total_vaccinations'].sum().to_dict(),
        "date_range": f"{df['date'].min()} to {df['date'].max()}"
    }
    
    prompt = f"""
    You are a Data Analyst for the Greek Ministry of Health.
    Analyze the following health data summary from our latest ETL pipeline run and provide an executive report.
    
    Data Summary:
    {json.dumps(summary_data, indent=2)}
    
    Identify any anomalies (e.g., in data cleaning metrics or unexpected values) and provide strategic recommendations for improving data collection or vaccination efforts.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=HealthAnalyticsReport,
                temperature=0.2,
            ),
        )
        
        report_data = json.loads(response.text)
        report = HealthAnalyticsReport(**report_data)
        
        with open('executive_report.md', 'w', encoding='utf-8') as f:
            f.write("# Greek Open Health Data - Executive Analytics Report\n\n")
            f.write("## Executive Summary\n")
            f.write(f"{report.executive_summary}\n\n")
            f.write("## Top Performing Regions\n")
            for r in report.top_performing_regions:
                f.write(f"- {r}\n")
            f.write("\n")
            f.write("## Data Anomalies Detected\n")
            for a in report.data_anomalies_detected:
                f.write(f"- {a}\n")
            f.write("\n")
            f.write("## Strategic Recommendations\n")
            for s in report.strategic_recommendations:
                f.write(f"- {s}\n")
                
        print("✅ Successfully generated executive_report.md")
    except Exception as e:
        print(f"Failed to generate AI report: {e}")

if __name__ == "__main__":
    print("🚀 Starting Greek Health Data ETL Pipeline...")
    
    # 1. Ingest/Scaffold Dirty Data
    print("1️⃣ Generating dirty data scaffolding...")
    df_dirty = generate_dirty_data()
    print(f"   Generated {len(df_dirty)} rows of data with varying degrees of realism/inconsistencies.")
    
    # 2. Clean Data
    print("2️⃣ Cleaning dataset (Pandas)...")
    df_clean, metrics, initial_missing, final_missing = clean_data(df_dirty)
    print(f"   Cleaning Complete. Pipeline Metrics: {metrics}")
    
    # 3. Create Visualizations
    print("3️⃣ Generating visual analytics (Matplotlib/Seaborn)...")
    generate_visualizations(df_clean, initial_missing, final_missing)
    print("   Created 'data_cleaning_impact.png' and 'vaccination_trends.png'.")
    
    # 4. Generate AI Report
    print("4️⃣ Generating AI Executive Report via Google Gemini...")
    generate_ai_report(df_clean, metrics)
    
    print("🎉 ETL Pipeline execution complete.")
