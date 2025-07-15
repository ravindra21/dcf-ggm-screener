import pandas as pd
import subprocess
import os
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_command(command, description):
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, Exception) as e:
        return False

def process_ticker(ticker, base_dir, raw_ticker=False):
    script_dir = "script"
    get_fundamental_script = os.path.join(script_dir, "get_fundamental_data.py")
    calculate_dcf_script = os.path.join(script_dir, "calculate_dcf.py")

    if raw_ticker:
        ticker_to_use = ticker
    else:
        ticker_to_use = f"{ticker}.jk"
    
    # Step 1: Get Fundamental Data
    success_fundamental = run_command(
        ["python", get_fundamental_script, ticker_to_use, "--dir", base_dir],
        f"get_fundamental_data for {ticker}"
    )
    
    if not success_fundamental:
        return ticker, False

    # Step 2: Calculate DCF
    success_dcf = run_command(
        ["python", calculate_dcf_script, ticker_to_use, "--dir", base_dir],
        f"calculate_dcf for {ticker}"
    )
    
    return ticker, success_dcf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process all stocks from a list, including data fetching and DCF calculation.")
    parser.add_argument("--dir", type=str, default="saham", help="The base directory for ticker data.")
    parser.add_argument("--file", type=str, default="Daftar saham.xlsx", help="The input file (CSV or XLSX) containing the list of stock tickers.")
    parser.add_argument("--raw", action="store_true", help="If set, ticker symbols will be used as-is without appending \".jk\".")
    parser.add_argument("num_to_process", type=int, nargs='?', default=None, help="Optional: Number of tickers to process.")
    args = parser.parse_args()

    base_dir = args.dir
    input_file_path = args.file
    raw_ticker_flag = args.raw

    if not os.path.exists(input_file_path):
        print(f"Error: Input file not found at '{input_file_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        file_extension = os.path.splitext(input_file_path)[1].lower()
        if file_extension == '.csv':
            df = pd.read_csv(input_file_path)
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(input_file_path)
        else:
            print(f"Error: Unsupported file format '{file_extension}'. Please use a CSV or XLSX file.", file=sys.stderr)
            sys.exit(1)

        if 'Kode' not in df.columns:
            print(f"Error: 'Kode' column not found in '{input_file_path}'.", file=sys.stderr)
            sys.exit(1)
        all_tickers = df['Kode'].dropna().astype(str).tolist()
    except Exception as e:
        print(f"Error reading or processing file '{input_file_path}': {e}", file=sys.stderr)
        sys.exit(1)

    if not all_tickers:
        print(f"No tickers found in the '{input_file_path}'.", file=sys.stderr)
        sys.exit(0)

    num_to_process = args.num_to_process
    if num_to_process is not None and num_to_process > 0:
        tickers = all_tickers[:num_to_process]
    else:
        tickers = all_tickers

    print(f"Processing {len(tickers)} tickers from '{input_file_path}' into directory '{base_dir}'...")
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
        future_to_ticker = {executor.submit(process_ticker, ticker, base_dir, raw_ticker_flag): ticker for ticker in tickers}
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker_result, success = future.result()
                status = "Done" if success else "Fail"
                print(f"{ticker_result}: {status}", flush=True)
            except Exception as exc:
                print(f"{ticker}: Fail (Exception: {exc})", flush=True)

    # Step 3: Filter DCF results after all tickers are processed
    print("\nAll tickers processed. Filtering DCF results...")
    script_dir = "script"
    filter_dcf_script = os.path.join(script_dir, "filter_dcf_results.py")
    success_filter = run_command(
        ["python", filter_dcf_script, "--dir", base_dir],
        "filter_dcf_results"
    )

    if success_filter:
        print("DCF results filtered successfully.")
    else:
        print("Failed to filter DCF results.", file=sys.stderr)
