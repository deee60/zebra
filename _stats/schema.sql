-- zebra beta visit log (Rod 11/15). No IP, no name, no e-mail. Rows older than 180 days are deleted daily.
CREATE TABLE IF NOT EXISTS pv (
  id TEXT PRIMARY KEY,          -- page view id (made in the browser)
  vid TEXT NOT NULL,            -- visitor id: random, kept in the browser (localStorage)
  sid TEXT NOT NULL,            -- visit id: new after 30 min without activity
  ts INTEGER NOT NULL,          -- opened (ms, UTC)
  path TEXT NOT NULL, title TEXT,
  ref_host TEXT, ref_path TEXT, -- where they came from (another site: host; inside the site: path)
  utm_source TEXT, utm_medium TEXT, utm_campaign TEXT,
  country TEXT, region TEXT, city TEXT, tz TEXT, isp TEXT,
  device TEXT, os TEXT, browser TEXT, lang TEXT,
  sw INTEGER, sh INTEGER,       -- screen size
  is_new INTEGER,               -- first visit of this browser
  active_ms INTEGER DEFAULT 0,  -- time the page was actually on screen
  scroll INTEGER DEFAULT 0,     -- deepest scroll, %
  clicks TEXT,                  -- links clicked on this page (JSON list, max 20)
  left_ts INTEGER               -- last signal
);
CREATE INDEX IF NOT EXISTS pv_ts ON pv(ts);
CREATE INDEX IF NOT EXISTS pv_vid ON pv(vid, ts);
CREATE INDEX IF NOT EXISTS pv_sid ON pv(sid, ts);
