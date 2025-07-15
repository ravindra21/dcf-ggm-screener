import csv
import os
import argparse

def parse_csv(file_path):
    data = {}
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
    return data, years

def calculate_roic_igr(ticker, financials_data, balance_sheet_data, cashflow_data, r_expected, g_expected):
    years = sorted(financials_data.keys())
    
    print(f"Calculating ROIC and IGR for {ticker} with r_expected={r_expected*100:.2f}% and g_expected={g_expected*100:.2f}%")
    print("-" * 60)

    results = {}

    # Iterate through years, starting from the second year to have a previous year for invested capital
    for i in range(1, len(years)):
        current_year = years[i]
        previous_year = years[i-1]

        print(f"Year: {current_year}")

        # Extract data for current and previous year
        current_fin = financials_data.get(current_year, {})
        prev_bal = balance_sheet_data.get(previous_year, {})
        current_bal = balance_sheet_data.get(current_year, {})
        current_cf = cashflow_data.get(current_year, {})

        # NOPAT Calculation
        ebit = current_fin.get('EBIT')
        tax_rate = current_fin.get('Tax Rate For Calcs')

        if ebit is None or tax_rate is None:
            print(f"  Skipping {current_year}: Missing EBIT or Tax Rate.")
            continue
        
        nopat = ebit * (1 - tax_rate)
        print(f"  NOPAT: {nopat:,.2f}")

        # Invested Capital (Beginning of Period)
        invested_capital_beginning = prev_bal.get('Invested Capital')
        if invested_capital_beginning is None:
            print(f"  Skipping {current_year}: Missing Invested Capital for previous year ({previous_year}).")
            continue
        print(f"  Invested Capital (Beginning of Period): {invested_capital_beginning:,.2f}")

        # ROIC Calculation
        if invested_capital_beginning != 0:
            roic = nopat / invested_capital_beginning
            print(f"  ROIC: {roic*100:.2f}%")
        else:
            roic = 0.0
            print(f"  ROIC: Cannot calculate (Invested Capital is zero).")

        # Reinvestment Rate Calculation
        invested_capital_current = current_bal.get('Invested Capital')
        if invested_capital_current is None:
            print(f"  Skipping {current_year}: Missing Invested Capital for current year ({current_year}).")
            continue

        delta_invested_capital = invested_capital_current - invested_capital_beginning
        print(f"  Delta Invested Capital: {delta_invested_capital:,.2f}")

        if nopat != 0:
            reinvestment_rate = delta_invested_capital / nopat
            print(f"  Reinvestment Rate: {reinvestment_rate*100:.2f}%")
        else:
            reinvestment_rate = 0.0
            print(f"  Reinvestment Rate: Cannot calculate (NOPAT is zero).")

        # Internal Growth Rate (g) Calculation
        igr = roic * reinvestment_rate
        print(f"  Internal Growth Rate (g): {igr*100:.2f}%")

        # Comparison with expectations
        print(f"  Expected ROIC (implied by GGM): {r_expected*100:.2f}% (This is the discount rate, not a direct ROIC expectation)")
        print(f"  Expected Internal Growth Rate (g): {g_expected*100:.2f}%")
        
        if igr >= g_expected:
            print(f"  Internal Growth Rate ({igr*100:.2f}%) meets or exceeds expectation ({g_expected*100:.2f}%).")
        else:
            print(f"  Internal Growth Rate ({igr*100:.2f}%) is below expectation ({g_expected*100:.2f}%).")
        
        print("-" * 60)
        results[current_year] = {'ROIC': roic, 'IGR': igr}
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate ROIC and Internal Growth Rate for a given ticker.")
    parser.add_argument("ticker", type=str, help="Stock ticker symbol (e.g., GOOG, META).")
    parser.add_argument("--dir", type=str, default="nasdaq_100", help="Base directory containing ticker folders.")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    base_path = os.path.join(args.dir, ticker)

    financials_file = os.path.join(base_path, f"{ticker}_financials.csv")
    balance_sheet_file = os.path.join(base_path, f"{ticker}_balance_sheet.csv")
    cashflow_file = os.path.join(base_path, f"{ticker}_cashflow.csv")

    financials_data, _ = parse_csv(financials_file)
    balance_sheet_data, _ = parse_csv(balance_sheet_file)
    cashflow_data, _ = parse_csv(cashflow_file)

    # Expected values for GGM
    r_expected = 0.10 # 10%
    g_expected = 0.0225 # 2.25%

    calculate_roic_igr(ticker, financials_data, balance_sheet_data, cashflow_data, r_expected, g_expected)
