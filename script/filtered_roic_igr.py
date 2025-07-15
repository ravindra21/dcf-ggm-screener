import csv
import os
import argparse
import json

def parse_csv(file_path):
    data = {}
    try:
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            years = [h for h in headers if h.startswith('20')] # Extract year columns
            
            for row in reader:
                metric_name = row[0]
                for i, year_str in enumerate(years):
                    year = year_str.split('-')[0] # Get just the year
                    if year not in data:
                        data[year] = {}
                    try:
                        # Handle empty strings or non-numeric values
                        value = float(row[i + 1]) if row[i + 1] else 0.0
                    except ValueError:
                        value = 0.0 # Default to 0.0 if conversion fails
                    data[year][metric_name] = value
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return {}, []
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return {}, []
    return data, years

def calculate_roic_igr_for_ticker(ticker, base_dir, min_roic, min_igr):
    base_path = os.path.join(base_dir, ticker)
    financials_file = os.path.join(base_path, f"{ticker}_financials.csv")
    balance_sheet_file = os.path.join(base_path, f"{ticker}_balance_sheet.csv")
    cashflow_file = os.path.join(base_path, f"{ticker}_cashflow.csv")

    financials_data, _ = parse_csv(financials_file)
    balance_sheet_data, _ = parse_csv(balance_sheet_file)
    cashflow_data, _ = parse_csv(cashflow_file)

    if not financials_data or not balance_sheet_data or not cashflow_data:
        return None # Cannot proceed without all data

    years = sorted(financials_data.keys())
    
    all_years_meet_criteria = True
    historical_data = {}

    # Iterate through years, starting from the second year to have a previous year for invested capital
    for i in range(1, len(years)):
        current_year = years[i]
        previous_year = years[i-1]

        # Extract data for current and previous year
        current_fin = financials_data.get(current_year, {})
        prev_bal = balance_sheet_data.get(previous_year, {})
        current_bal = balance_sheet_data.get(current_year, {})

        # NOPAT Calculation
        ebit = current_fin.get('EBIT')
        tax_rate = current_fin.get('Tax Rate For Calcs')

        if ebit is None or tax_rate is None:
            all_years_meet_criteria = False
            break # Cannot calculate for this year, so break
        
        nopat = ebit * (1 - tax_rate)

        # Invested Capital (Beginning of Period)
        invested_capital_beginning = prev_bal.get('Invested Capital')
        if invested_capital_beginning is None or invested_capital_beginning == 0:
            # This year cannot be evaluated for ROIC/IGR, but doesn't fail the whole ticker
            continue

        # ROIC Calculation
        roic = nopat / invested_capital_beginning

        # Reinvestment Rate Calculation
        invested_capital_current = current_bal.get('Invested Capital')
        if invested_capital_current is None:
            all_years_meet_criteria = False
            break

        delta_invested_capital = invested_capital_current - invested_capital_beginning

        if nopat != 0:
            reinvestment_rate = delta_invested_capital / nopat
        else:
            reinvestment_rate = 0.0

        # Internal Growth Rate (g) Calculation
        igr = roic * reinvestment_rate

        # Check criteria
        if not (roic * 100 >= min_roic and igr * 100 >= min_igr):
            all_years_meet_criteria = False
            break
        
        historical_data[current_year] = {'roic': round(roic * 100, 2), 'igr': round(igr * 100, 2)}

    if all_years_meet_criteria and historical_data:
        return {'ticker': ticker, 'historical_data': historical_data}
    else:
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter stocks based on historical ROIC and IGR.")
    parser.add_argument("input_csv", type=str, default="filtered_dcf_results.csv", help="Input CSV file containing ticker symbols.")
    parser.add_argument("--dir", type=str, default="saham", help="Base directory containing ticker folders (e.g., nasdaq_100, s_and_p_500).")
    parser.add_argument("--min-roic", type=float, default=10.0, help="Minimum acceptable ROIC percentage.")
    parser.add_argument("--min-igr", type=float, default=2.5, help="Minimum acceptable Internal Growth Rate percentage.")
    

    args = parser.parse_args()

    input_csv_path = args.input_csv
    base_data_dir = args.dir
    min_roic_threshold = args.min_roic
    min_igr_threshold = args.min_igr

    filtered_tickers = []

    try:
        with open(input_csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row['kode'] # Assuming 'kode' column contains ticker symbol
                print(f"Processing {ticker}...")
                result = calculate_roic_igr_for_ticker(ticker, base_data_dir, min_roic_threshold, min_igr_threshold)
                if result:
                    filtered_tickers.append(result)
    except FileNotFoundError:
        print(f"Error: Input CSV file not found at {input_csv_path}")
        exit(1)

    output_json_path = "filtered_roic_igr.json"
    if filtered_tickers:
        with open(output_json_path, 'w') as jsonfile:
            json.dump(filtered_tickers, jsonfile, indent=4)
        print(f"Filtered results saved to {output_json_path}")
    else:
        print("No tickers met the specified ROIC and IGR criteria.")
