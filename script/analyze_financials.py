import pandas as pd
import os
import sys
import argparse

def analyze_ticker_financials(ticker_symbol, base_dir="saham"):
    ticker_dir = os.path.join(base_dir, ticker_symbol)

    balance_sheet_file = os.path.join(ticker_dir, f"{ticker_symbol}_balance_sheet.csv")
    financials_file = os.path.join(ticker_dir, f"{ticker_symbol}_financials.csv")
    cashflow_file = os.path.join(ticker_dir, f"{ticker_symbol}_cashflow.csv")

    results = {
        "ticker": ticker_symbol,
        "der_ok": False,
        "profit_ok": False,
        "fcf_ok": False,
        "der_value": "N/A",
        "net_income_status": "N/A",
        "fcf_status": "N/A",
        "error": None
    }

    if not all(os.path.exists(f) for f in [balance_sheet_file, financials_file, cashflow_file]):
        results["error"] = "Missing one or more required financial files."
        return results

    try:
        df_balance_sheet = pd.read_csv(balance_sheet_file, index_col=0)
        df_financials = pd.read_csv(financials_file, index_col=0)
        df_cashflow = pd.read_csv(cashflow_file, index_col=0)
    except Exception as e:
        results["error"] = f"Error reading financial files: {e}"
        return results

    # Criteria 1: Rasio DER < 1
    if 'Total Liabilities Net Minority Interest' in df_balance_sheet.index and 'Stockholders Equity' in df_balance_sheet.index:
        # Identify date columns and sort them to find the latest
        date_columns_with_names = []
        for col in df_balance_sheet.columns:
            try:
                date_columns_with_names.append((pd.to_datetime(col), col))
            except ValueError:
                continue
        
        # Sort dates in descending order to get the latest first
        date_columns_with_names.sort(key=lambda x: x[0], reverse=True)
        
        latest_year_col = None
        if date_columns_with_names:
            latest_year_col = date_columns_with_names[0][1] # Get the original column name

        if latest_year_col:
            latest_total_liabilities = df_balance_sheet.loc['Total Liabilities Net Minority Interest', latest_year_col]
            latest_total_equity = df_balance_sheet.loc['Stockholders Equity', latest_year_col]
            
            # Handle potential NaN values if the latest column has missing data for these rows
            if pd.isna(latest_total_liabilities):
                latest_total_liabilities = 0
            if pd.isna(latest_total_equity):
                latest_total_equity = 0
        else:
            latest_total_liabilities = 0
            latest_total_equity = 0

        if latest_total_equity > 0:
            latest_der = latest_total_liabilities / latest_total_equity
            results["der_value"] = f"{latest_der:.2f}"
            if latest_der < 1:
                results["der_ok"] = True
        else:
            results["der_value"] = "Equity Zero/Negative"
    else:
        results["der_value"] = "Data Missing"

    # Criteria 2: Laba positif dan bertumbuh
    if 'Net Income' in df_financials.index:
        net_income_series = df_financials.loc['Net Income'].dropna()
        net_income_series.index = pd.to_datetime(net_income_series.index)
        net_income_series = net_income_series.sort_index()
        if not net_income_series.empty:
            # Debug print
            # print(f"Debug: {ticker_symbol} Net Income Series after dropna(): {net_income_series.to_string()}")
            if (net_income_series > 0).all():
                if len(net_income_series) >= 2:
                    if net_income_series.iloc[-1] > net_income_series.iloc[-2]:
                        results["profit_ok"] = True
                        results["net_income_status"] = "Positive & Growing"
                    else:
                        results["net_income_status"] = "Positive but Not Growing"
                elif len(net_income_series) == 1 and net_income_series.iloc[-1] > 0:
                    results["profit_ok"] = True
                    results["net_income_status"] = "Positive (Single Data Point)"
                else:
                    results["net_income_status"] = "Not Positive"
            else:
                results["net_income_status"] = "Contains Non-Positive Values"
        else:
            results["net_income_status"] = "No Data"
    else:
        results["net_income_status"] = "Data Missing"

    # Criteria 3: History free cashflow tidak ada minus atau bertumbuh
    if 'Free Cash Flow' in df_cashflow.index:
        fcf_series = df_cashflow.loc['Free Cash Flow'].dropna()
        fcf_series.index = pd.to_datetime(fcf_series.index)
        fcf_series = fcf_series.sort_index()
        if not fcf_series.empty:
            # Debug print
            # print(f"Debug: {ticker_symbol} FCF Series after dropna(): {fcf_series.to_string()}")
            if (fcf_series >= 0).all():
                if len(fcf_series) >= 2:
                    if fcf_series.iloc[-1] > fcf_series.iloc[-2]:
                        results["fcf_ok"] = True
                        results["fcf_status"] = "Non-Negative & Growing"
                    else:
                        results["fcf_status"] = "Non-Negative but Not Growing"
                elif len(fcf_series) == 1 and fcf_series.iloc[-1] >= 0:
                    results["fcf_ok"] = True
                    results["fcf_status"] = "Non-Negative (Single Data Point)"
                else:
                    results["fcf_status"] = "Contains Negative Values"
            else:
                results["fcf_status"] = "Contains Negative Values"
        else:
            results["fcf_status"] = "No Data"
    else:
        results["fcf_status"] = "Data Missing"

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze financials of stocks from a filtered list.")
    parser.add_argument("--dir", type=str, default="saham", help="Directory where ticker data is stored.")
    args = parser.parse_args()

    filtered_dcf_results_file = "filtered_dcf_results.csv"
    output_file_path = "filtered_financial_analysis.txt"

    if not os.path.exists(filtered_dcf_results_file):
        print(f"Error: {filtered_dcf_results_file} not found.", file=sys.stderr)
        sys.exit(1)

    try:
        df_filtered_dcf = pd.read_csv(filtered_dcf_results_file)
        if 'kode' not in df_filtered_dcf.columns:
            print(f"Error: 'kode' column not found in {filtered_dcf_results_file}.", file=sys.stderr)
            sys.exit(1)
        tickers_to_check = df_filtered_dcf['kode'].dropna().astype(str).tolist()
    except Exception as e:
        print(f"Error reading {filtered_dcf_results_file}: {e}", file=sys.stderr)
        sys.exit(1)

    all_analysis_results = []
    for ticker in tickers_to_check:
        all_analysis_results.append(analyze_ticker_financials(ticker, base_dir=args.dir))

    good_financial_stocks_details = []
    for result in all_analysis_results:
        if result["error"] is None and result["der_ok"] and result["profit_ok"] and result["fcf_ok"]:
            good_financial_stocks_details.append(result)

    with open(output_file_path, 'w') as f:
        f.write("--- Detail Analisis Keuangan Saham yang Lolos Screening ---\n")
        if good_financial_stocks_details:
            f.write(f'{"Ticker":<8} {"DER < 1":<10} {"Laba Positif & Tumbuh":<25} {"FCF Non-Neg & Tumbuh":<25} {"DER Value":<12} {"Net Income Status":<30} {"FCF Status":<30}\n')
            f.write(f'{"-"*8:<8} {"-"*10:<10} {"-"*25:<25} {"-"*25:<25} {"-"*12:<12} {"-"*30:<30} {"-"*30:<30}\n')
            for result in good_financial_stocks_details:
                f.write(f'{result["ticker"]:<8} {str(result["der_ok"]):<10} {str(result["profit_ok"]):<25} {str(result["fcf_ok"]):<25} {result["der_value"]:<12} {result["net_income_status"]:<30} {result["fcf_status"]:<30}\n')
        else:
            f.write("Tidak ada saham yang memenuhi semua kriteria keuangan yang bagus.\n")

        f.write("\n--- Ringkasan ---\n")
        if good_financial_stocks_details:
            f.write("Saham dengan keuangan yang bagus berdasarkan semua kriteria:\n")
            for result in good_financial_stocks_details:
                f.write(f'{result["ticker"]}\n')
        else:
            f.write("Tidak ada saham yang memenuhi semua kriteria keuangan yang bagus.\n")

    print(f"Hasil analisis disimpan ke: {output_file_path}")