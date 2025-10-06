# Amazon Reviews → PostgreSQL (RDS) — Category Schema Playbook

A concise, repeatable workflow to load the Amazon Review JSON Lines datasets into a single database (e.g., `amazon_reviews`) with **one schema per category**. Each schema contains:

- `reviews_csv_stage` (TEXT-only staging for CSV loads)
- `reviews` (typed, query‑friendly final table)

You’ll also get reusable SQL helpers:

- `amazon_admin.ensure_category_tables(cat text)` — creates the schema, staging table, and final table + indexes
- `amazon_admin.normalize_from_stage(cat text)` — moves/cleans data from `reviews_csv_stage` → `reviews`

---

## 0) Prerequisites

- RDS PostgreSQL reachable from your machine (Security Group allows your IP).
- `psql` installed locally (or DBeaver for SQL execution + CSV import).
- JSON Lines files downloaded locally (e.g., `All_Beauty_5.json`).

---

## 1) One‑time admin setup (run inside the **amazon\_reviews** database)

Create the admin schema and two helpers (a function to create tables per category, and a procedure to normalize from staging):

```sql
CREATE SCHEMA IF NOT EXISTS amazon_admin;

-- Creates per‑category schema, staging + final tables, and indexes
CREATE OR REPLACE FUNCTION amazon_admin.ensure_category_tables(cat text)
RETURNS void AS $$
BEGIN
  -- 1) schema
  EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I;', cat);

  -- 2) staging: TEXT‑only columns matching your CSV headers
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.reviews_csv_stage (
      asin            text,
      image           text,
      overall         text,
      review_ts       text,
      reviewText      text,
      reviewTime      text,
      reviewerID      text,
      reviewerName    text,
      style           text,
      summary         text,
      unixReviewTime  text,
      verified        text,
      vote            text
    );
  $f$, cat);


  -- 4) final typed table
  EXECUTE format($f$
    CREATE TABLE IF NOT EXISTS %I.reviews (
      review_id       bigserial PRIMARY KEY,
      reviewerID      text,
      reviewerName    text,
      asin            text,
      overall         numeric(2,1),
      review_ts       timestamptz,
      reviewTime      text,          -- raw date string, e.g. "05 3, 2011"
      unixReviewTime  bigint,        -- raw UNIX timestamp
      reviewText      text,
      vote            int,
      verified        boolean,
      style           jsonb,
      image           text[],        -- array of URLs
      summary         text
    );
  $f$, cat);

  -- 5) helpful indexes
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I_reviews_asin_idx ON %I.reviews (asin);', cat||'_asin', cat);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I_reviews_ts_idx   ON %I.reviews (review_ts);', cat||'_ts',   cat);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I_reviews_name_ci  ON %I.reviews ((lower(reviewerName)));', cat||'_name_ci', cat);
  EXECUTE format('CREATE INDEX IF NOT EXISTS %I_reviews_style_gin ON %I.reviews USING gin (style);', cat||'_style_gin', cat);
END;
$$ LANGUAGE plpgsql;

-- Moves/cleans from reviews_csv_stage → reviews (handles blanks/commas/JSON)
CREATE OR REPLACE PROCEDURE amazon_admin.normalize_from_stage(cat text)
LANGUAGE plpgsql AS $$
BEGIN
  EXECUTE format($f$
    INSERT INTO %I.reviews (
      asin, image, overall, reviewText, reviewTime,
      reviewerID, reviewerName, style, summary,
      unixReviewTime, review_ts, verified, vote
    )
    SELECT
      s.asin,
      CASE
        WHEN s.image IS NULL OR btrim(s.image) = '' THEN ARRAY[]::text[]
        WHEN s.image ~ '^\s*\[.*\]\s*$' THEN ARRAY(SELECT jsonb_array_elements_text(s.image::jsonb))
        ELSE ARRAY[s.image]
      END,
      NULLIF(regexp_replace(s.overall, '[^0-9.\-]', '', 'g'), '')::numeric(2,1),
      s.reviewText,
      s.reviewTime,
      s.reviewerID,
      s.reviewerName,
      CASE
        WHEN s.style IS NULL OR btrim(s.style) = '' THEN NULL
        WHEN s.style ~ '^\s*[\{\[].*[\}\]]\s*$' THEN s.style::jsonb
        ELSE NULL
      END,
      s.summary,
      NULLIF(s.unixReviewTime,'')::bigint,
      COALESCE(
        to_timestamp(NULLIF(s.unixReviewTime,'')::bigint),
        CASE WHEN s.review_ts ~ '^\d{10}(\.\d+)?$' THEN to_timestamp(s.review_ts::double precision) END,
        to_timestamp(NULLIF(s.reviewTime,''), 'MM DD, YYYY')
      ),
      CASE
        WHEN lower(s.verified) IN ('true','t','1','yes','y')  THEN TRUE
        WHEN lower(s.verified) IN ('false','f','0','no','n') THEN FALSE
        ELSE NULL
      END,
      NULLIF(regexp_replace(s.vote, '[^0-9\-]', '', 'g'), '')::int
    FROM %I.reviews_csv_stage AS s;
  $f$, cat, cat);
END;
$$;
```

> Run once; these utilities are reusable for every category (`all_beauty`, `books`, etc.).

---

## 2) For each category (repeatable loop)

### A) Create schema + tables

```sql
SELECT amazon_admin.ensure_category_tables('all_beauty');
-- SELECT amazon_admin.ensure_category_tables('books');
-- SELECT amazon_admin.ensure_category_tables('grocery_and_gourmet_food');
```

### B) Convert JSON → CSV (on your machine)

Use your current Python notebook/script (keeps **all** JSON keys; nested are JSON strings in the CSV):

```python
import json
import pandas as pd

input_file = "/Users/Yash/Research/agent-database-crawler/data/All_Beauty_5.json"
output_file = "/Users/Yash/Research/agent-database-crawler/data/All_Beauty_5_full.csv"

records = []
all_keys = set()

# Pass 1: load objects and collect all keys
with open(input_file, "r", encoding="utf-8") as infile:
    for line in infile:
        obj = json.loads(line)
        records.append(obj)
        all_keys.update(obj.keys())

# Pass 2: normalize into DataFrame with all keys as columns
df = pd.DataFrame(records, columns=sorted(all_keys))

# Convert nested dicts/lists to JSON strings (so CSV can store them)
for col in df.columns:
    df[col] = df[col].apply(
        lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
    )

# Save to CSV
df.to_csv(output_file, index=False, encoding="utf-8")

print(f"Saved {len(df)} rows with {len(df.columns)} columns to {output_file}")
```

> The staging table expects the following headers (case‑sensitive recommended): `asin,image,overall,review_ts,reviewText,reviewTime,reviewerID,reviewerName,style,summary,unixReviewTime,verified,vote`
>
> If your CSV has extra columns, that’s fine—either drop them before import or add TEXT columns to `reviews_csv_stage` and the procedure.

### C) Load CSV into the staging table

**psql**:

```sql
\copy all_beauty.reviews_csv_stage
  (asin,image,overall,review_ts,reviewText,reviewTime,reviewerID,reviewerName,style,summary,unixReviewTime,verified,vote)
FROM '/Users/Yash/Research/agent-database-crawler/data/All_Beauty_5_full.csv'
CSV HEADER
NULL ''
QUOTE '"'
ESCAPE '"'
ENCODING 'UTF8';
```

**DBeaver**: Data Transfer → Import from CSV → target `all_beauty.reviews_csv_stage` → map the columns above → set **NULL string** to empty.

### D) Normalize into the final table

```sql
CALL amazon_admin.normalize_from_stage('all_beauty');
```

### E) (Optional) Index refresh & sanity checks

```sql
VACUUM ANALYZE all_beauty.reviews;

SELECT count(*) FROM all_beauty.reviews;
SELECT asin, overall, review_ts, left(summary,60) AS summary
FROM all_beauty.reviews
ORDER BY review_ts DESC
LIMIT 10;
```

---

## 3) Repeat for additional categories

For each new category, replace `'all_beauty'` with the schema name, run **A→E**. You can also build a small driver script to loop across categories.

---

## 4) Notes & gotchas

- **Numbers with commas** (e.g., `vote = "1,341"`) are sanitized by the procedure via `regexp_replace` before casting.
- **Blank JSON** fields (e.g., `style = ''`) become `NULL` (valid), not invalid JSON.
- ``: JSON array → parsed to `text[]`; blank → empty array; any other string → single‑element array.
- **Timestamps**: `review_ts` prefers `unixReviewTime` (epoch). If not present, tries a UNIX value in the `review_ts` CSV column, then falls back to parsing `reviewTime` using the format `MM DD, YYYY`.
- If your CSV headers differ, alter the `reviews_csv_stage` definition and procedure accordingly.

---

## 5) Optional: Direct JSON path (skip CSV entirely)

If you ever want to load JSON Lines directly, use `%I.reviews_raw` and insert from there. The `ensure_category_tables` function already creates `reviews_raw` for you.

```bash
zcat All_Beauty_5.json.gz | jq -c . | psql "host=<RDS> port=5432 dbname=amazon_reviews user=<USER> sslmode=require" \
  -c "\\copy all_beauty.reviews_raw (doc) FROM STDIN"
```

Then write an `INSERT ... SELECT` from `reviews_raw` into `reviews` similar to the normalization above (mapping JSON fields appropriately).

---

**End of playbook.** This document is ready to reuse per category; swap `'all_beauty'` with your next schema name and repeat A→E.

