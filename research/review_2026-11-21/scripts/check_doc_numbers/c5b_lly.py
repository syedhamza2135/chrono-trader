import pandas as pd
off = pd.read_parquet("D:/chrono-data/auctions/official.parquet")
x = off[(off.symbol == "LLY") & (off.date == "2019-08-12")]
print(x[["symbol","asof","date","listing_exchange","open_size","open_time","n_open_prints","close_size","n_close_prints"]].to_string(index=False))
m = pd.read_csv("research/audit/auctions_missing_opens.csv")
print("missing list rows", len(m), "LLY rows", m[m.symbol=="LLY"].date.tolist())
print("missing by date top", m.date.value_counts().head(4).to_dict())
