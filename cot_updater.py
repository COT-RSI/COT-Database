import os
import requests
import pandas as pd
from datetime import datetime

# Multi-Market Mapping for Portfolio Scanning
MARKET_MAPPING = {
    "EURO CURRENCY - CHICAGO MERCANTILE EXCHANGE": "EURUSD",
    "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE": "GBPUSD",
    "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "AUDUSD",
    "NEW ZEALAND DOLLAR - CHICAGO MERCANTILE EXCHANGE": "NZDUSD",
    "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE": "USDJPY",
    "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE": "USDCAD",
    "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE": "USDCHF"
}

CSV_FILE_PATH = "cot_master_database.csv"
CFTC_URL = "https://www.cftc.gov/dea/futures/cme_lf.txt"

def auto_update_portfolio_cot():
    print("Initiating Multi-Pair Institutional Data Stream...")
    response = requests.get(CFTC_URL)
    if response.status_code != 200:
        print("CRITICAL: CFTC server connection failed.")
        return
        
    lines = response.text.split('\n')
    if len(lines) < 2:
        return

    headers = [col.strip() for col in lines[0].split(',')]
    rows = []
    for line in lines[1:]:
        if len(line.strip()) < 10:
            continue
        rows.append([val.strip() for val in line.split(',')])
        
    df_cftc = pd.DataFrame(rows, columns=headers)
    
    # Check existing data
    if os.path.exists(CSV_FILE_PATH):
        df_master = pd.read_csv(CSV_FILE_PATH)
    else:
        df_master = pd.DataFrame(columns=['Symbol', 'Date', 'NonCommLong', 'NonCommShort', 'CommLong', 'CommShort', 'OpenInterest'])

    new_records_added = 0
    
    for cftc_name, short_sym in MARKET_MAPPING.items():
        df_market = df_cftc[df_cftc['Market_and_Market_Type'] == cftc_name]
        if df_market.empty:
            continue
            
        latest_row = df_market.iloc[0]
        raw_date = latest_row['Report_Date_as_YYYY-MM-DD']
        formatted_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y.%m.%d")
        
        # Check duplication
        duplicate_check = df_master[(df_master['Symbol'] == short_sym) & (df_master['Date'] == formatted_date)]
        if not duplicate_check.empty:
            continue
            
        new_data = {
            'Symbol': short_sym,
            'Date': formatted_date,
            'NonCommLong': float(latest_row['NonComm_Positions_Long_All']),
            'NonCommShort': float(latest_row['NonComm_Positions_Short_All']),
            'CommLong': float(latest_row['Comm_Positions_Long_All']),
            'CommShort': float(latest_row['Comm_Positions_Short_All']),
            'OpenInterest': float(latest_row['Open_Interest_All'])
        }
        
        df_master = pd.concat([df_master, pd.DataFrame([new_data])], ignore_index=True)
        new_records_added += 1

    if new_records_added > 0:
        df_master.to_csv(CSV_FILE_PATH, index=False)
        print(f"Portfolio database updated with {new_records_added} new tracking blocks.")
    else:
        print("Database is already up to date with latest CFTC release.")

if __name__ == "__main__":
    auto_update_portfolio_cot()
