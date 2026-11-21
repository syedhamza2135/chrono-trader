import pyarrow.parquet as pq, pyarrow as pa, pyarrow.compute as pc, datetime, os
S = "D:/chrono-data/store/"
DISTINCT = {"bars": ["entity_id", "symbol"], "opens": ["entity_id"], "labels": ["entity_id"],
            "stories": ["story_id"], "story_entities": ["story_id", "entity_id"],
            "membership": ["entity_id"], "identity": ["entity_id", "symbol"]}
for name in DISTINCT:
    p = S + name + ".parquet"
    f = pq.ParquetFile(p)
    t = pq.read_table(p)
    print("##", name, "rows", f.metadata.num_rows, "mtime",
          datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M:%S"))
    for c in DISTINCT[name]:
        print("  distinct", c, pc.count_distinct(t[c]).as_py())
    for fld in t.schema:
        col = t[fld.name]
        s = f"  {fld.name} ({fld.type}, nulls {col.null_count})"
        if pa.types.is_temporal(fld.type):
            mm = pc.min_max(col)
            s += f" min {mm['min'].as_py()} max {mm['max'].as_py()}"
        elif pa.types.is_boolean(fld.type):
            s += f" true {pc.sum(col).as_py()}"
        elif name in ("identity",) and fld.name in ("valid_from", "valid_to"):
            s += " (string)"
        print(s)
