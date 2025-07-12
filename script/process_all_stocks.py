import pandas as pd
import subprocess
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_command(command, description):
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, Exception):
        return False

def process_ticker(ticker):
    script_dir = "script"
    get_fundamental_script = os.path.join(script_dir, "get_fundamental_data.py")
    calculate_dcf_script = os.path.join(script_dir, "calculate_dcf.py")

    ticker_with_suffix = f"{ticker}.jk"
    success_fundamental = run_command(["python", get_fundamental_script, ticker_with_suffix], f"get_fundamental_data for {ticker}")
    if success_fundamental:
        success_dcf = run_command(["python", calculate_dcf_script, ticker_with_suffix], f"calculate_dcf for {ticker}")
        if success_dcf:
            filter_dcf_script = os.path.join(script_dir, "filter_dcf_results.py")
            success_filter = run_command(["python", filter_dcf_script], "filter_dcf_results")
            return ticker, success_filter
        return ticker, False
    return ticker, False

if __name__ == "__main__":
    excel_file_path = "Daftar saham.xlsx"

    if not os.path.exists(excel_file_path):
        sys.exit(1)

    try:
        df = pd.read_excel(excel_file_path)
        if 'Kode' not in df.columns:
            sys.exit(1)
        all_tickers = df['Kode'].dropna().astype(str).tolist()
    except Exception:
        sys.exit(1)

    if not all_tickers:
        sys.exit(0)

    num_to_process = None
    if len(sys.argv) > 1:
        try:
            num_to_process = int(sys.argv[1])
        except ValueError:
            pass

    if num_to_process is not None and num_to_process > 0:
        tickers = all_tickers[:num_to_process]
    else:
        tickers = all_tickers

    
    with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
        future_to_ticker = {executor.submit(process_ticker, ticker): ticker for ticker in tickers}
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker_result, success = future.result()
                status = "Done" if success else "Fail"
                print(f"{ticker_result}: {status}", flush=True)
            except Exception as exc:
                ticker = future_to_ticker[future]
                print(f"{ticker}: Fail", flush=True)