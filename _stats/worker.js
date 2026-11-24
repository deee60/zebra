// zebra beta visit stats (Rod 11/15) — the DukTong admin, without the AI parts.
// Routes (zebrabeta.kr/_z/*):
//   GET  /_z/t.js        the small tracker every page loads
//   POST /_z/hit         a page was opened
//   POST /_z/beat        time on screen · scroll · clicks so far (sent while reading and when leaving)
//   GET  /_z/admin       the admin page (asks for the admin token once)
//   GET  /_z/api/...     admin data (Authorization: Bearer ADMIN_TOKEN)
// Stored: page, title, where from, city-level place from Cloudflare, device/OS/browser, screen, language, time on screen,
// scroll, clicked links. Not stored: IP address, names, e-mails. Rows older than 180 days are deleted every day.
import ADMIN_HTML from './admin.html';
import TRACKER from './t.js.txt';

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS pv (id TEXT PRIMARY KEY, vid TEXT NOT NULL, sid TEXT NOT NULL, ts INTEGER NOT NULL, path TEXT NOT NULL, title TEXT,
    ref_host TEXT, ref_path TEXT, utm_source TEXT, utm_medium TEXT, utm_campaign TEXT, country TEXT, region TEXT, city TEXT, tz TEXT, isp TEXT,
    device TEXT, os TEXT, browser TEXT, lang TEXT, sw INTEGER, sh INTEGER, is_new INTEGER, active_ms INTEGER DEFAULT 0, scroll INTEGER DEFAULT 0,
    clicks TEXT, left_ts INTEGER)`,
  'CREATE INDEX IF NOT EXISTS pv_ts ON pv(ts)',
  'CREATE INDEX IF NOT EXISTS pv_vid ON pv(vid, ts)',
  'CREATE INDEX IF NOT EXISTS pv_sid ON pv(sid, ts)',
  // the curator's own browsers: their visits are thrown away
  'CREATE TABLE IF NOT EXISTS me (vid TEXT PRIMARY KEY, ts INTEGER NOT NULL)',
];
const isMe = async (env, vid) => !!(await env.DB.prepare('SELECT 1 FROM me WHERE vid = ?').bind(vid).first());
async function leaveOut(env, vid) {
  await env.DB.batch([
    env.DB.prepare('INSERT OR IGNORE INTO me (vid, ts) VALUES (?, ?)').bind(vid, Date.now()),
    env.DB.prepare('DELETE FROM pv WHERE vid = ?').bind(vid),
  ]);
}
let ready = false;
async function ensure(env) {
  if (ready) return;
  await env.DB.batch(SCHEMA.map((q) => env.DB.prepare(q)));
  ready = true;
}

const BOT = /bot|crawl|spider|slurp|preview|facebookexternalhit|embedly|quora link|whatsapp|telegram|discord|skype|headless|lighthouse|pingdom|uptime|monitor|curl|wget|python|httpclient|go-http|java\//i;
const ID = /^[a-z0-9]{8,32}$/;
const SITE = /(^|\.)zebrabeta\.kr$/;

function device(ua) {
  if (/ipad|tablet|(android(?!.*mobile))/i.test(ua)) return 'tablet';
  if (/mobi|iphone|ipod|android/i.test(ua)) return 'phone';
  return 'desktop';
}
function os(ua) {
  if (/iphone|ipad|ipod/i.test(ua)) { const m = ua.match(/OS (\d+)[_.](\d+)/); return 'iOS' + (m ? ' ' + m[1] : ''); }
  if (/android/i.test(ua)) { const m = ua.match(/Android (\d+)/); return 'Android' + (m ? ' ' + m[1] : ''); }
  if (/windows nt 10/i.test(ua)) return 'Windows';
  if (/windows/i.test(ua)) return 'Windows (old)';
  if (/mac os x/i.test(ua)) return 'macOS';
  if (/cros/i.test(ua)) return 'ChromeOS';
  if (/linux/i.test(ua)) return 'Linux';
  return 'other';
}
function browser(ua) {
  if (/kakaotalk/i.test(ua)) return 'KakaoTalk (in-app)';
  if (/naver\(inapp|whale/i.test(ua)) return /naver\(inapp/i.test(ua) ? 'Naver (in-app)' : 'Whale';
  if (/instagram/i.test(ua)) return 'Instagram (in-app)';
  if (/fban|fbav/i.test(ua)) return 'Facebook (in-app)';
  if (/line\//i.test(ua)) return 'LINE (in-app)';
  if (/samsungbrowser/i.test(ua)) return 'Samsung Internet';
  if (/edg\//i.test(ua)) return 'Edge';
  if (/opr\/|opera/i.test(ua)) return 'Opera';
  if (/firefox|fxios/i.test(ua)) return 'Firefox';
  if (/crios|chrome/i.test(ua)) return 'Chrome';
  if (/safari/i.test(ua)) return 'Safari';
  return 'other';
}
const cut = (v, n) => (typeof v === 'string' ? v.slice(0, n) : null);
const int = (v, lo, hi) => { const n = Math.round(Number(v)); return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : null; };
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
const ok = () => new Response(null, { status: 204, headers: { 'cache-control': 'no-store' } });

async function body(req) { try { const t = await req.text(); return t.length > 8000 ? null : JSON.parse(t); } catch { return null; } }

async function hit(req, env) {
  const ua = req.headers.get('user-agent') || '';
  if (BOT.test(ua)) return ok();
  const b = await body(req); if (!b || !ID.test(b.id || '') || !ID.test(b.vid || '') || !ID.test(b.sid || '')) return ok();
  const cf = req.cf || {};
  let refHost = null, refPath = null;
  if (b.ref) { try { const u = new URL(b.ref); if (SITE.test(u.hostname)) refPath = cut(u.pathname, 200); else refHost = cut(u.hostname.replace(/^www\./, ''), 100); } catch { /* bad referrer */ } }
  await ensure(env);
  if (await isMe(env, b.vid)) return ok();
  await env.DB.prepare(`INSERT OR IGNORE INTO pv (id, vid, sid, ts, path, title, ref_host, ref_path, utm_source, utm_medium, utm_campaign, country, region, city, tz, isp,
    device, os, browser, lang, sw, sh, is_new, left_ts) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(
    b.id, b.vid, b.sid, Date.now(), cut(b.path, 300) || '/', cut(b.title, 200), refHost, refPath,
    cut(b.us, 80), cut(b.um, 80), cut(b.uc, 120),
    cut(cf.country, 2), cut(cf.region, 80), cut(cf.city, 80), cut(cf.timezone, 60), cut(cf.asOrganization, 100),
    device(ua), os(ua), browser(ua), cut(b.lang, 20), int(b.sw, 0, 10000), int(b.sh, 0, 10000), b.n ? 1 : 0, Date.now(),
  ).run();
  return ok();
}

async function beat(req, env) {
  const b = await body(req); if (!b || !ID.test(b.id || '')) return ok();
  const clicks = Array.isArray(b.c) ? JSON.stringify(b.c.slice(0, 20).map((x) => cut(String(x), 200))) : null;
  await ensure(env);
  // only grows: a late or repeated signal never lowers time or scroll
  await env.DB.prepare(`UPDATE pv SET active_ms = MAX(active_ms, ?), scroll = MAX(scroll, ?), clicks = COALESCE(?, clicks), left_ts = ?
    WHERE id = ? AND ts > ?`).bind(int(b.a, 0, 6 * 3600e3) || 0, int(b.s, 0, 100) || 0, clicks, Date.now(), b.id, Date.now() - 12 * 3600e3).run();
  return ok();
}

// the curator's own browser asks to be left out: delete everything recorded under its own id
async function forget(req, env) {
  const b = await body(req); if (!b || !ID.test(b.vid || '')) return ok();
  await ensure(env);
  await leaveOut(env, b.vid);
  return ok();
}

// ---------- admin ----------
function authed(req, env) {
  const t = (req.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!env.ADMIN_TOKEN || t.length < 16 || t.length !== env.ADMIN_TOKEN.length) return false;
  let d = 0; for (let i = 0; i < t.length; i++) d |= t.charCodeAt(i) ^ env.ADMIN_TOKEN.charCodeAt(i);
  return d === 0;
}
function range(url) {
  const to = Number(url.searchParams.get('to')) || Date.now();
  const from = Number(url.searchParams.get('from')) || to - 24 * 3600e3;
  return [Math.max(0, from), to];
}
const all = async (env, q, ...a) => (await env.DB.prepare(q).bind(...a).all()).results || [];

async function api(path, url, env) {
  await ensure(env);
  const [from, to] = range(url);
  const W = 'ts >= ? AND ts < ?';
  if (path === 'summary') {
    const [t] = await all(env, `SELECT COUNT(*) pv, COUNT(DISTINCT vid) visitors, COUNT(DISTINCT sid) visits, SUM(active_ms) active,
      COUNT(DISTINCT CASE WHEN is_new = 1 THEN vid END) new_visitors FROM pv WHERE ${W}`, from, to);
    const [b] = await all(env, `SELECT COUNT(*) one FROM (SELECT sid FROM pv WHERE ${W} GROUP BY sid HAVING COUNT(*) = 1)`, from, to);
    const [live] = await all(env, 'SELECT COUNT(DISTINCT vid) n FROM pv WHERE left_ts > ?', Date.now() - 5 * 60e3);
    // time series: hour buckets up to 3 days, else day buckets (KST)
    const span = to - from; const step = span <= 3 * 864e5 ? 3600e3 : 864e5;
    const series = await all(env, `SELECT ((ts + 32400000) / CAST(? AS INTEGER)) * CAST(? AS INTEGER) - 32400000 AS t, COUNT(*) pv, COUNT(DISTINCT vid) visitors FROM pv WHERE ${W} GROUP BY 1 ORDER BY 1`, step, step, from, to);
    return { ...t, bounce_visits: b ? b.one : 0, live: live ? live.n : 0, step, series };
  }
  if (path === 'pages') return all(env, `SELECT path, MAX(title) title, COUNT(*) views, COUNT(DISTINCT vid) visitors, AVG(active_ms) avg_ms, AVG(scroll) avg_scroll,
    SUM(CASE WHEN scroll >= 90 THEN 1 ELSE 0 END) read_to_end FROM pv WHERE ${W} GROUP BY path ORDER BY views DESC LIMIT 200`, from, to);
  if (path === 'sources') return all(env, `SELECT COALESCE(utm_source, ref_host, '(direct / app)') src, COUNT(DISTINCT sid) visits, COUNT(DISTINCT vid) visitors
    FROM pv p WHERE ${W} AND ts = (SELECT MIN(ts) FROM pv q WHERE q.sid = p.sid) GROUP BY src ORDER BY visits DESC LIMIT 100`, from, to);
  if (path === 'places') return all(env, `SELECT country, region, city, COUNT(DISTINCT vid) visitors, COUNT(*) views, AVG(active_ms) avg_ms FROM pv WHERE ${W}
    GROUP BY country, region, city ORDER BY visitors DESC LIMIT 200`, from, to);
  if (path === 'tech') {
    const g = (col) => all(env, `SELECT ${col} k, COUNT(DISTINCT vid) visitors FROM pv WHERE ${W} GROUP BY ${col} ORDER BY visitors DESC LIMIT 30`, from, to);
    const [dev, oss, br, lang, isp, scr] = await Promise.all([g('device'), g('os'), g('browser'), g('lang'), g('isp'),
      all(env, `SELECT sw || '×' || sh k, COUNT(DISTINCT vid) visitors FROM pv WHERE ${W} AND sw > 0 GROUP BY k ORDER BY visitors DESC LIMIT 15`, from, to)]);
    return { device: dev, os: oss, browser: br, lang, isp, screen: scr };
  }
  if (path === 'clicks') {
    const rows = await all(env, `SELECT path, clicks FROM pv WHERE ${W} AND clicks IS NOT NULL AND clicks != '[]'`, from, to);
    const m = new Map();
    for (const r of rows) { let l = []; try { l = JSON.parse(r.clicks); } catch { /* */ } for (const c of l) { const k = c; m.set(k, (m.get(k) || 0) + 1); } }
    return [...m].map(([link, n]) => ({ link, n })).sort((a, b) => b.n - a.n).slice(0, 100);
  }
  if (path === 'visitors') return all(env, `SELECT vid, MIN(ts) first_ts, MAX(COALESCE(left_ts, ts)) last_ts, COUNT(DISTINCT sid) visits, COUNT(*) views, SUM(active_ms) active,
    MAX(city) city, MAX(region) region, MAX(country) country, MAX(device) device, MAX(os) os, MAX(browser) browser,
    (SELECT COALESCE(utm_source, ref_host, '(direct / app)') FROM pv f WHERE f.vid = pv.vid ORDER BY ts LIMIT 1) first_src,
    (SELECT MIN(ts) FROM pv a WHERE a.vid = pv.vid) ever_first
    FROM pv WHERE ${W} GROUP BY vid ORDER BY last_ts DESC LIMIT 500`, from, to);
  if (path === 'people') {
    // one row per visitor (browser): everything about them in this window, merged
    const rows = await all(env, `SELECT vid, sid, ts, left_ts, path, title, ref_host, ref_path, utm_source, utm_medium, country, region, city, isp, device, os, browser, lang, sw, sh,
      active_ms, scroll, clicks FROM pv WHERE ${W} ORDER BY ts LIMIT 30000`, from, to);
    const ef = await all(env, `SELECT vid, MIN(ts) ef FROM pv WHERE vid IN (SELECT DISTINCT vid FROM pv WHERE ${W}) GROUP BY vid`, from, to);
    const first = new Map(ef.map((r) => [r.vid, r.ef]));
    const m = new Map(); const now = Date.now();
    for (const r of rows) {
      let p = m.get(r.vid);
      if (!p) {
        p = { vid: r.vid, first_ts: r.ts, last_ts: r.ts, ever_first: first.get(r.vid) || r.ts, sids: new Set(), views: 0, active: 0, scroll_sum: 0,
          country: r.country, region: r.region, city: r.city, isp: r.isp, device: r.device, os: r.os, browser: r.browser, lang: r.lang, sw: r.sw, sh: r.sh,
          sources: [], flow: [], clicks: [], cities: [] };
        m.set(r.vid, p);
      }
      const isStart = !p.sids.has(r.sid); p.sids.add(r.sid);
      if (isStart) {
        const src = r.utm_source ? 'utm:' + r.utm_source : r.ref_host ? r.ref_host : r.ref_path ? null : '직접 · 앱';
        if (src && !p.sources.includes(src)) p.sources.push(src);
      }
      p.last_ts = Math.max(p.last_ts, r.left_ts || r.ts); p.views++; p.active += r.active_ms || 0; p.scroll_sum += r.scroll || 0;
      p.flow.push({ ts: r.ts, path: r.path, title: r.title, ms: r.active_ms || 0, sc: r.scroll || 0, new_visit: isStart });
      if (r.city && !p.cities.includes(r.city)) p.cities.push(r.city);
      if (r.clicks && r.clicks !== '[]') { try { for (const c of JSON.parse(r.clicks)) if (!p.clicks.includes(c)) p.clicks.push(c); } catch { /* */ } }
      p.city = r.city || p.city; p.region = r.region || p.region; p.country = r.country || p.country; p.isp = r.isp || p.isp;
    }
    return [...m.values()].map((p) => ({ ...p, sids: undefined, visits: p.sids.size, avg_scroll: p.views ? Math.round(p.scroll_sum / p.views) : 0, scroll_sum: undefined,
      live: now - p.last_ts < 5 * 60e3, flow: p.flow.slice(-60) })).sort((a, b) => b.last_ts - a.last_ts).slice(0, 500);
  }
  if (path === 'visitor') {
    const vid = url.searchParams.get('vid') || ''; if (!ID.test(vid)) return [];
    return all(env, `SELECT id, sid, ts, path, title, ref_host, ref_path, utm_source, utm_medium, utm_campaign, country, region, city, tz, isp, device, os, browser, lang, sw, sh,
      is_new, active_ms, scroll, clicks, left_ts FROM pv WHERE vid = ? ORDER BY ts LIMIT 2000`, vid);
  }
  if (path === 'leave') {
    const vid = url.searchParams.get('vid') || ''; if (!ID.test(vid)) return { ok: false };
    await leaveOut(env, vid); return { ok: true };
  }
  if (path === 'export') return all(env, `SELECT * FROM pv WHERE ${W} ORDER BY ts LIMIT 50000`, from, to);
  return null;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url); const p = url.pathname;
    try {
      if (p === '/_z/t.js') return new Response(TRACKER, { headers: { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'public, max-age=600' } });
      if (p === '/_z/hit' && req.method === 'POST') return await hit(req, env);
      if (p === '/_z/beat' && req.method === 'POST') return await beat(req, env);
      if (p === '/_z/forget' && req.method === 'POST') return await forget(req, env);
      if (p === '/_z/admin' || p === '/_z/admin/') return new Response(ADMIN_HTML, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex', 'referrer-policy': 'no-referrer' } });
      if (p.startsWith('/_z/api/')) {
        if (!authed(req, env)) return json({ error: 'auth' }, 401);
        const r = await api(p.slice(8), url, env);
        return r === null ? json({ error: 'not found' }, 404) : json(r);
      }
      return new Response('not found', { status: 404 });
    } catch (e) {
      return p.startsWith('/_z/api/') ? json({ error: 'server' }, 500) : ok(); // never break a reader's page
    }
  },
  async scheduled(_ev, env) {
    await ensure(env);
    await env.DB.prepare('DELETE FROM pv WHERE ts < ?').bind(Date.now() - 180 * 864e5).run();
  },
};
