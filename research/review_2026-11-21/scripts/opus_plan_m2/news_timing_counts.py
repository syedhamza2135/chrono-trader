# Counts only. Reads three timestamp/id columns of stories and story_id of story_entities. No headline is read.
import pyarrow.parquet as pq, pandas as pd
S = "D:/chrono-data/store/"
st = pq.read_table(S + "stories.parquet", columns=["story_id", "created_at", "updated_at"]).to_pandas()
se = pq.read_table(S + "story_entities.parquet", columns=["story_id"]).to_pandas().drop_duplicates()
NY = "America/New_York"
lag = st.updated_at - st.created_at
print("stories", len(st))
print("updated_at < created_at", int((lag < pd.Timedelta(0)).sum()))
print("lag > 3 days (should be 0 in store)", int((lag > pd.Timedelta(days=3)).sum()))
avail = st.updated_at + pd.Timedelta(minutes=15)
cy = st.created_at.dt.tz_convert(NY).dt.year
ay = avail.dt.tz_convert(NY).dt.year
x = st[st.story_id.isin(se.story_id)].assign(cy=cy, ay=ay)
print("story_entities stories", len(x))
print("created NY year 2015, available NY year 2016", int(((x.cy == 2015) & (x.ay == 2016)).sum()))
print("created year != available year (any)", int((x.cy != x.ay).sum()))
print("created NY year by year:", x.cy.value_counts().sort_index().to_dict())
ad = avail.dt.tz_convert(NY)
print("story_entities stories available 09:00-09:30 NY on their day (after the cut, before the open)",
      int(((ad[x.index].dt.hour == 9) & (ad[x.index].dt.minute < 30)).sum()))
neg = st[lag < pd.Timedelta(0)].assign(lag=lag[lag < pd.Timedelta(0)])
neg = neg.assign(in_se=neg.story_id.isin(se.story_id), avail_before_created=(neg.updated_at + pd.Timedelta(minutes=15)) < neg.created_at,
                 ny_created=neg.created_at.dt.tz_convert(NY).dt.date)
print(neg[["story_id", "ny_created", "lag", "in_se", "avail_before_created"]].to_string(index=False))
