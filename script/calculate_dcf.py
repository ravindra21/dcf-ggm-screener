import pandas as pd
import sys
import os
from datetime import datetime


def calculate_dcf(ticker_symbol):
    discount_rate = 0.10  # 10%
    terminal_growth_rate = 0.025  # Conservative 5%
    # Define the base output directory
    base_output_dir = "saham"

    # Define the output directory for the ticker
    output_dir = os.path.join(base_output_dir, ticker_symbol)
    output_filename = os.path.join(output_dir, f"{ticker_symbol}_dcf_analysis.txt")

    output_messages = [] # List to store all messages

    def append_message(message):
        output_messages.append(message)

    append_message(f"\n--- DCF Calculation for {ticker_symbol} ---")
    append_message(f"Discount Rate: {discount_rate*100}%")
    append_message(f"Terminal Growth Rate: {terminal_growth_rate*100}%")

    # Update file paths to reflect the new directory structure
    cashflow_file = os.path.join(output_dir, f"{ticker_symbol}_cashflow.csv")
    historical_prices_file = os.path.join(output_dir, f"{ticker_symbol}_historical_prices.csv")
    balance_sheet_file = os.path.join(output_dir, f"{ticker_symbol}_balance_sheet.csv")
    company_info_file = os.path.join(output_dir, f"{ticker_symbol}_company_info.csv")

    if not os.path.exists(cashflow_file):
        append_message(f"Error: Cash flow data not found for {ticker_symbol} at {cashflow_file}")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        return
    if not os.path.exists(historical_prices_file):
        append_message(f"Error: Historical prices data not found for {ticker_symbol} at {historical_prices_file}")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        return
    if not os.path.exists(balance_sheet_file):
        append_message(f"Error: Balance sheet data not found for {ticker_symbol} at {balance_sheet_file}")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        return
    if not os.path.exists(company_info_file):
        append_message(f"Error: Company info data not found for {ticker_symbol} at {company_info_file}")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        return

    try:
        df_cashflow = pd.read_csv(cashflow_file, index_col=0)
        df_historical_prices = pd.read_csv(historical_prices_file, index_col=0)
        df_historical_prices.index = pd.to_datetime(df_historical_prices.index, utc=True)
        df_balance_sheet = pd.read_csv(balance_sheet_file, index_col=0)
        df_company_info = pd.read_csv(company_info_file, index_col=0)
    except Exception as e:
        append_message(f"Error reading data files: {e}")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        sys.exit(1)

    if 'Free Cash Flow' not in df_cashflow.index:
        append_message(f"Error: 'Free Cash Flow' row not found in {cashflow_file}")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        sys.exit(1)

    fcf_series = df_cashflow.loc['Free Cash Flow'].dropna()

    if fcf_series.empty:
        append_message("No Free Cash Flow data available.")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        return

    # Convert index to datetime for proper sorting and year calculation
    fcf_series.index = pd.to_datetime(fcf_series.index)
    fcf_series = fcf_series.sort_index()

    # Get shares outstanding data
    shares_outstanding_map = {}
    if 'Ordinary Shares Number' in df_balance_sheet.index:
        shares_data = df_balance_sheet.loc['Ordinary Shares Number'].dropna()
        for col_date, shares_num in shares_data.items():
            try:
                year = pd.to_datetime(col_date).year
                shares_outstanding_map[year] = shares_num
            except ValueError:
                # Handle cases where column name might not be a valid date
                pass
    
    # Fallback: if no historical shares data, try to get from company info or use a default
    if not shares_outstanding_map:
        try:
            if 'sharesOutstanding' in df_company_info.index:
                latest_shares = df_company_info.loc['sharesOutstanding', 'Value']
                # Use the latest shares for all years if no historical data
                for year in fcf_series.index.year.unique():
                    shares_outstanding_map[year] = latest_shares
                append_message(f"Warning: Using latest sharesOutstanding ({latest_shares:,.0f}) for all historical DCF calculations due to lack of historical data.")
        except Exception as e:
            append_message(f"Warning: Could not retrieve sharesOutstanding from company info: {e}")
            append_message("Cannot calculate historical intrinsic value per share without shares outstanding data.")
            with open(output_filename, 'w') as f:
                f.write('\n'.join(output_messages))
            return # Exit if no shares data at all


    # Get the last available Free Cash Flow for the simple Gordon Growth Model
    if fcf_series.empty:
        append_message("No Free Cash Flow data available for Gordon Growth Model calculation.")
        with open(output_filename, 'w') as f:
            f.write('\n'.join(output_messages))
        return

    last_fcf = fcf_series.iloc[-1]
    append_message(f"\nLatest Free Cash Flow (FCF) used for Gordon Growth Model: {last_fcf:,.0f} IDR")

    intrinsic_value_total = 0
    if discount_rate <= terminal_growth_rate:
        append_message("Warning: Discount rate must be greater than terminal growth rate for Gordon Growth Model. Cannot calculate intrinsic value.")
    else:
        # Simple Gordon Growth Model (Buffett-like)
        # Intrinsic Value = FCF_next_year / (Discount_Rate - Growth_Rate)
        # FCF_next_year = Last_FCF * (1 + Growth_Rate)
        intrinsic_value_total = last_fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        append_message(f"\nEstimated Intrinsic Value (using Simple Gordon Growth Model): {intrinsic_value_total:,.0f} IDR")
    
    # Get latest shares outstanding for current intrinsic value per share
    latest_year_fcf = fcf_series.index.year[-1]
    current_shares_outstanding = shares_outstanding_map.get(latest_year_fcf, None)
    if current_shares_outstanding is None:
        # Try to get from company info if not found in balance sheet for latest year
        try:
            if 'sharesOutstanding' in df_company_info.index:
                current_shares_outstanding = df_company_info.loc['sharesOutstanding', 'Value']
        except Exception:
            pass

    current_market_price = None
    if 'currentPrice' in df_company_info.index:
        try:
            current_market_price = float(df_company_info.loc['currentPrice', 'Value'])
        except ValueError:
            append_message("Warning: Could not convert currentPrice to float.")
            current_market_price = None

    if current_shares_outstanding is not None and current_shares_outstanding > 0:
        intrinsic_value_per_share = intrinsic_value_total / current_shares_outstanding
        append_message(f"\nTotal Estimated Intrinsic Value (Current): {intrinsic_value_total:,.0f} IDR")
        append_message(f"Estimated Intrinsic Value Per Share (Current): {intrinsic_value_per_share:,.2f} IDR")
        
        if current_market_price is not None:
            current_margin_of_safety = ((intrinsic_value_per_share - current_market_price) / current_market_price) * 100
            append_message(f"Current Market Price: {current_market_price:,.2f} IDR")
            append_message(f"Current Margin of Safety: {current_margin_of_safety:,.2f}%")
        else:
            append_message("Current market price not available for Margin of Safety calculation.")
    else:
        append_message(f"\nTotal Estimated Intrinsic Value (Current): {intrinsic_value_total:,.0f} IDR")
        append_message("Cannot calculate current intrinsic value per share: Shares outstanding data not available or is zero.")

    append_message("\n--- Historical DCF Analysis ---")
    append_message(f"{"Year":<6} {"Total Intrinsic Value":<25} {"Intrinsic Value Per Share":<30} {"Market Price":<15} {"Margin of Safety":<18}")
    append_message(f"{"-"*6:<6} {"-"*25:<25} {"-"*30:<30} {"-"*15:<15} {"-"*18:<18}")

    # Iterate through historical FCF data
    for date, fcf in fcf_series.items():
        year = date.year
        historical_intrinsic_value_total = 0
        if discount_rate > terminal_growth_rate:
            historical_intrinsic_value_total = fcf * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
        
        historical_shares_outstanding = shares_outstanding_map.get(year)
        
        historical_intrinsic_value_per_share = 0
        if historical_shares_outstanding is not None and historical_shares_outstanding > 0:
            historical_intrinsic_value_per_share = historical_intrinsic_value_total / historical_shares_outstanding
        
        # Get historical market price for the year
        # Assuming historical_prices has a 'Close' column and is indexed by date
        market_price_for_year = None
        # Find the closest market price for the year
        if not df_historical_prices.empty:
            # Filter prices for the current year
            prices_in_year = df_historical_prices[df_historical_prices.index.year == year]
            if not prices_in_year.empty:
                # Get the last closing price of the year
                market_price_for_year = prices_in_year['Close'].iloc[-1]

        historical_margin_of_safety = "N/A"
        if market_price_for_year is not None and historical_intrinsic_value_per_share > 0:
            historical_margin_of_safety = ((historical_intrinsic_value_per_share - market_price_for_year) / market_price_for_year) * 100
            historical_margin_of_safety = f"{historical_margin_of_safety:,.2f}%"
        
        append_message(f"{year:<6} {historical_intrinsic_value_total:<25,.0f} {historical_intrinsic_value_per_share:<30,.2f} {(f'{market_price_for_year:,.2f}' if market_price_for_year is not None else 'N/A'):<15} {historical_margin_of_safety:<18}")

    # Write all collected messages to the file at once
    with open(output_filename, 'w') as f:
        f.write('\n'.join(output_messages))

    print(f"DCF analysis saved to {output_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calculate_dcf.py <TICKER_SYMBOL>")
        print("Example: python calculate_dcf.py SIDO.JK")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    calculate_dcf(ticker)