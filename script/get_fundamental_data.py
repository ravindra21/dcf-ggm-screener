import yfinance as yf
import argparse
import pandas as pd
from datetime import datetime
import os

# Set up argument parser
parser = argparse.ArgumentParser(description='Fetch fundamental and historical data for a stock ticker.')
parser.add_argument('ticker_symbol', type=str, help='The ticker symbol of the stock (e.g., SIDO.JK)')
parser.add_argument('--dir', type=str, default='saham', help='The base directory to save the output files.')

# Parse command-line arguments
args = parser.parse_args()
ticker_symbol = args.ticker_symbol.upper()
base_output_dir = args.dir

# Define the output directory for the ticker
output_dir = os.path.join(base_output_dir, ticker_symbol)

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Create a Ticker object
stock = yf.Ticker(ticker_symbol)

# --- Get and Save Fundamental Data ---

# Get fundamental data
company_info = stock.info
balance_sheet = stock.balance_sheet
financials = stock.financials
cashflow = stock.cashflow

# Save Company Info to CSV
# Convert dictionary to DataFrame for easier saving
info_df = pd.DataFrame.from_dict(company_info, orient='index', columns=['Value'])
info_filename = os.path.join(output_dir, f"{ticker_symbol}_company_info.csv")
info_df.to_csv(info_filename)
print(f"Company info saved to {info_filename}")

# Save Balance Sheet to CSV
balance_sheet_filename = os.path.join(output_dir, f"{ticker_symbol}_balance_sheet.csv")
balance_sheet.to_csv(balance_sheet_filename)
print(f"Balance sheet saved to {balance_sheet_filename}")

# Save Financials to CSV
financials_filename = os.path.join(output_dir, f"{ticker_symbol}_financials.csv")
financials.to_csv(financials_filename)
print(f"Financials saved to {financials_filename}")

# Save Cash Flow to CSV
cashflow_filename = os.path.join(output_dir, f"{ticker_symbol}_cashflow.csv")
cashflow.to_csv(cashflow_filename)
print(f"Cash flow saved to {cashflow_filename}")

# --- Get and Save Historical Price Data ---

# Define start and end dates for historical data (e.g., last 5 years)
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - pd.DateOffset(years=5)).strftime("%Y-%m-%d")

# Get historical price data
historical_data = stock.history(start=start_date, end=end_date)

# Define desired columns, and check if 'Dividends' and 'Stock Splits' exist
desired_columns = ['Close', 'Volume']
if 'Dividends' in historical_data.columns:
    desired_columns.append('Dividends')
if 'Stock Splits' in historical_data.columns:
    desired_columns.append('Stock Splits')

# Select only desired columns that exist in the DataFrame
historical_data_filtered = historical_data[desired_columns]

# Save Historical Price Data to CSV
historical_filename = os.path.join(output_dir, f"{ticker_symbol}_historical_prices.csv")
historical_data_filtered.to_csv(historical_filename)
print(f"Historical price data saved to {historical_filename}")