# Counts only. Reads id, date and flag columns of bars; no price column is read.
import pyarrow.parquet as pq
b = pq.read_table("D:/chrono-data/store/bars.parquet", columns=["entity_id", "share_class", "date", "member", "incomplete"]).to_pandas()
m = b[b.member]
print("member bar rows (company, class, day)", len(m))
print("distinct member (company, day)", len(m[["entity_id", "date"]].drop_duplicates()))
print("member days in a company's second class", len(m) - len(m[["entity_id", "date"]].drop_duplicates()))
print("companies with two classes on a member day", m.groupby(["entity_id", "date"]).size().pipe(lambda s: s[s > 1]).reset_index().entity_id.nunique())
print("member rows to 2026-10-28", int((m.date <= "2026-10-28").sum()))
print("incomplete: all", int(b.incomplete.sum()), "member", int((b.incomplete & b.member).sum()))
inc = b[b.incomplete & b.member].date.dt.date.astype(str).value_counts()
print("incomplete member bars by date", inc.to_dict())
