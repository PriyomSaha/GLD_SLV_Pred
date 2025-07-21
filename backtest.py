import yfinance as yf
import pandas as pd

print("📥 Fetching historical data...\n")

# Define tickers you want to fetch
tickers = {
    "nifty": "^NSEI",
    "vix": "^INDIAVIX",
    "crude": "CL=F",
    "usdinr": "USDINR=X",
    "dxy": "DX-Y.NYB",
    "us10y": "^TNX",
    "gold": "GC=F",
    "silver": "SI=F"
}

data = {}

# Fetch and process each ticker
for name, ticker in tickers.items():
    print(f"→ Fetching {name} ({ticker}) ...")
    df_yf = yf.download(ticker, period="10y", interval="1d", progress=False)

    if not df_yf.empty:
        # Check if the DataFrame has MultiIndex columns
        if isinstance(df_yf.columns, pd.MultiIndex):
            series = df_yf.xs("Close", axis=1, level=0).squeeze().dropna()
        else:
            series = df_yf["Close"].dropna()

        if not series.empty:
            print(f"✅ Got {len(series)} data points. Saving type: {type(series)}")
            data[name] = series
        else:
            print(f"⚠️ Warning: Close series empty for {name}")
    else:
        print(f"⚠️ Warning: no data for {name}")

# Print summary
print("\n📊 Summary of fetched data:")
for k, v in data.items():
    print(f"{k}: type={type(v)}, length={len(v)}")

# Combine into single DataFrame
df_list = []
cols = []

for name, series in data.items():
    print(f"🔍 Checking {name}: type={type(series)}, length={len(series)}")
    if isinstance(series, pd.Series) and not series.empty:
        df_list.append(series)
        cols.append(name)
    else:
        print(f"⚠️ Skipped {name} (empty or wrong type)")

if df_list:
    # Join='inner' to keep only dates that exist in all series
    df = pd.concat(df_list, axis=1, join="inner")
    df.columns = cols

    # ✅ Name the index so Excel shows it as "Date" column
    df.index.name = "Date"

    print("\n✅ Combined DataFrame created successfully!")
    print(df.head())

    # 📤 Save to Excel
    output_filename = "historical_data.xlsx"
    df.to_excel(output_filename)
    print(f"\n📁 Data saved to {output_filename}")

else:
    print("⚠️ No valid data to concatenate.")
