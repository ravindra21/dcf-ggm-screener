import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_command(command, description):
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, Exception) as e:
        # print(f"Error running command for {description}: {e}", file=sys.stderr)
        return False

def calculate_dcf_for_ticker(ticker_folder):
    script_dir = "script"
    calculate_dcf_script = os.path.join(script_dir, "calculate_dcf.py")

    ticker_with_suffix = ticker_folder # The folder name already includes .JK

    success_dcf = run_command(["python", calculate_dcf_script, ticker_with_suffix], f"calculate_dcf for {ticker_with_suffix}")
    return ticker_with_suffix, success_dcf

if __name__ == "__main__":
    saham_dir = "saham"

    if not os.path.exists(saham_dir):
        print(f"Error: Directory {saham_dir} not found.", file=sys.stderr)
        sys.exit(1)

    all_ticker_folders = [d for d in os.listdir(saham_dir) if os.path.isdir(os.path.join(saham_dir, d))]

    if not all_ticker_folders:
        print("No ticker folders found in saham directory.", file=sys.stderr)
        sys.exit(0)

    num_to_process = None
    if len(sys.argv) > 1:
        try:
            num_to_process = int(sys.argv[1])
        except ValueError:
            pass

    if num_to_process is not None and num_to_process > 0:
        tickers_to_process = all_ticker_folders[:num_to_process]
    else:
        tickers_to_process = all_ticker_folders

    with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
        future_to_ticker = {executor.submit(calculate_dcf_for_ticker, ticker): ticker for ticker in tickers_to_process}
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker_result, success = future.result()
                status = "Done" if success else "Fail"
                print(f"{ticker_result}: {status}")
            except Exception as exc:
                print(f"{ticker}: Fail (Exception: {exc})", file=sys.stderr)
