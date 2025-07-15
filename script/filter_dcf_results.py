import os
import re
import csv
import argparse

def filter_dcf_results(root_dir="saham", min_mos=0.0, max_mos=100.0):
    results = []
    
    # Walk through all subdirectories to find dcf_analysis.txt files
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith("_dcf_analysis.txt"):
                file_path = os.path.join(dirpath, filename)
                ticker = os.path.basename(dirpath) # Ticker is the name of the parent directory
                
                current_mos = None
                current_price = None
                intrinsic_value_per_share = None

                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                        # Regex for Current Margin of Safety
                        mos_match = re.search(r'Current Margin of Safety: (-?[\d\.,]+)%', content)
                        if mos_match:
                            current_mos = float(mos_match.group(1).replace(',', ''))

                        # Regex for Estimated Intrinsic Value Per Share (Current)
                        intrinsic_match = re.search(r'Estimated Intrinsic Value Per Share \(Current\): (-?[\d\.,]+) IDR', content)
                        if intrinsic_match:
                            intrinsic_value_per_share = float(intrinsic_match.group(1).replace(',', ''))

                        # Regex for Current Market Price
                        price_match = re.search(r'Current Market Price: (-?[\d\.,]+) IDR', content)
                        if price_match:
                            current_price = float(price_match.group(1).replace(',', ''))

                except Exception as e:
                    print(f"Error reading or parsing {file_path}: {e}")
                    continue
                
                # Filter based on Current Margin of Safety
                if current_mos is not None and min_mos <= current_mos <= max_mos:
                    results.append({
                        'kode': ticker,
                        'margin of safety': current_mos,
                        'market price': current_price,
                        'intrinsic value per share': intrinsic_value_per_share
                    })

    # Define the output CSV file path
    output_csv_path = os.path.join(".", "filtered_dcf_results.csv")

    if results:
        with open(output_csv_path, 'w', newline='') as csvfile:
            fieldnames = ['kode', 'intrinsic value per share', 'market price', 'margin of safety']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in results:
                writer.writerow(row)
        print(f"Filtered DCF results saved to {output_csv_path}")
    else:
        print(f"No stocks found with Current Margin of Safety between {min_mos}% and {max_mos}%.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter DCF results from a directory.")
    parser.add_argument("--dir", type=str, default="saham", help="Directory to search for ticker folders.")
    parser.add_argument("--min-mos", type=float, default=0.0, help="Minimum Margin of Safety percentage (inclusive).")
    parser.add_argument("--max-mos", type=float, default=100.0, help="Maximum Margin of Safety percentage (inclusive).")
    args = parser.parse_args()
    filter_dcf_results(root_dir=args.dir, min_mos=args.min_mos, max_mos=args.max_mos)