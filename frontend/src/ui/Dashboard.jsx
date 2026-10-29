import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, RefreshCw, Wind } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const fmt = (n, digits = 0) => n == null ? '—' : Number(n).toLocaleString('en-GB', { maximumFractionDigits: digits, minimumFractionDigits: digits });

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [decisionHour, setDecisionHour] = useState(10);
  const [selectedDay, setSelectedDay] = useState('all');

  async function load() {
    setLoading(true); setError('');
    try {
      const response = await fetch(`${API}/api/overview?decision_hour=${decisionHour}`);
      if (!response.ok) throw new Error((await response.json()).detail || `API returned ${response.status}`);
      setData(await response.json());
    } catch (e) { setError(e.message || 'Unable to load Elexon data'); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [decisionHour]);

  const days = useMemo(() => [...new Set((data?.series || []).map(x => x.startTime?.slice(0, 10)))].sort(), [data]);
  const points = useMemo(() => (data?.series || []).filter(x => selectedDay === 'all' || x.startTime?.startsWith(selectedDay)).map(x => ({
    ...x, time: new Date(x.startTime).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London' }),
  })), [data, selectedDay]);
  const m = data?.metrics || {};

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Wind size={22}/></div><div><strong>GRIDWISE</strong><span>PROCUREMENT INTELLIGENCE</span></div></div>
      <div className="nav-label">WORKSPACE</div><div className="nav-item active"><Activity size={17}/> Wind forecast monitor</div>
      <div className="sidebar-bottom"><div className="status-dot"/> Elexon BMRS <span className="live-tag">API</span><p>January 2026 · Great Britain</p></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div><div className="eyebrow">ENERGY TRADING / DAY-AHEAD</div><h1>Wind procurement intelligence</h1><p className="subtitle">Understand forecast availability, quantify error, and make better-informed procurement decisions.</p></div><button className="refresh" onClick={load} disabled={loading}><RefreshCw size={15} className={loading ? 'spin' : ''}/>{loading ? 'Loading data' : 'Refresh data'}</button></header>
      <section className="context-strip"><div><span className="strip-dot"/> <strong>JAN 01 — JAN 31, 2026</strong><span className="muted"> · Hourly intervals · actuals aggregated from half-hourly data</span></div><label>Decision cutoff <select value={decisionHour} onChange={e => setDecisionHour(Number(e.target.value))}>{[8,9,10,11,12].map(h => <option value={h} key={h}>{String(h).padStart(2,'0')}:00 UK time, previous day</option>)}</select></label></section>
      {error && <div className="alert"><AlertTriangle size={18}/><div><strong>Could not load Elexon data</strong><p>{error}. Confirm API availability and try Refresh.</p></div></div>}
      {data?.data_status === 'no_matched_data' && <div className="alert"><AlertTriangle size={18}/><div><strong>No matched forecast/actual intervals</strong><p>{data.message}</p></div></div>}
      <section className="metric-grid">
        <Metric label="Matched intervals" value={fmt(m.matched_intervals)} suffix="periods" note="Forecast eligible at cutoff" icon={<Activity size={18}/>} />
        <Metric label="Mean absolute error" value={fmt(m.mae_mw, 0)} suffix="MW" note="Average absolute forecast miss" icon={<Wind size={18}/>} />
        <Metric label="Root mean squared error" value={fmt(m.rmse_mw, 0)} suffix="MW" note="Penalises larger forecast misses" icon={<AlertTriangle size={18}/>} />
        <Metric label="Forecast bias" value={fmt(m.bias_mw, 0)} suffix="MW" note={m.bias_mw > 0 ? 'Forecast tends to overstate wind' : m.bias_mw < 0 ? 'Forecast tends to understate wind' : 'Average signed error'} icon={m.bias_mw > 0 ? <ArrowUpRight size={18}/> : <ArrowDownRight size={18}/>} />
      </section>
      <section className="chart-grid">
        <div className="panel wide"><div className="panel-head"><div><h2>Forecast vs actual generation</h2><p>National wind output · MW · local UK display time</p></div><select value={selectedDay} onChange={e => setSelectedDay(e.target.value)}><option value="all">All January</option>{days.map(day => <option key={day} value={day}>{day}</option>)}</select></div>
          <div className="chart-area">{loading ? <div className="empty">Fetching Elexon data…</div> : points.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={points} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}><defs><linearGradient id="forecastFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#55c7b5" stopOpacity={0.22}/><stop offset="95%" stopColor="#55c7b5" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="#263246"/><XAxis dataKey="time" minTickGap={50} tick={{ fill: '#8795aa', fontSize: 10 }} axisLine={false} tickLine={false}/><YAxis tick={{ fill: '#8795aa', fontSize: 11 }} axisLine={false} tickLine={false} width={55}/><Tooltip contentStyle={{ background: '#111b2c', border: '1px solid #2b3b52', borderRadius: 10, color: '#eef4ff' }}/><Legend/><Area type="monotone" dataKey="forecast_mw" name="Eligible forecast" stroke="#55c7b5" fill="url(#forecastFill)" strokeWidth={2} dot={false}/><Line type="monotone" dataKey="actual_mw" name="Actual generation" stroke="#e8b45d" strokeWidth={1.8} dot={false} connectNulls={false}/></AreaChart></ResponsiveContainer> : <div className="empty">No chart data available for this selection.</div>}</div>
        </div>
        <div className="panel"><div className="panel-head"><div><h2>Error distribution</h2><p>Forecast minus actual, MW</p></div></div><div className="chart-area small">{points.length ? <ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ top: 10, right: 6, left: -15, bottom: 0 }}><CartesianGrid strokeDasharray="3 3" stroke="#263246"/><XAxis dataKey="time" hide/><YAxis tick={{ fill: '#8795aa', fontSize: 10 }} axisLine={false} tickLine={false}/><Tooltip contentStyle={{ background: '#111b2c', border: '1px solid #2b3b52', borderRadius: 10, color: '#eef4ff' }}/><Line type="monotone" dataKey="error_mw" name="Forecast error (MW)" stroke="#b69aff" strokeWidth={1.5} dot={false}/></LineChart></ResponsiveContainer> : <div className="empty">Waiting for data</div>}</div><div className="bias-row"><span>Overforecast intervals</span><strong>{fmt(m.overforecast_intervals)}</strong></div><div className="bias-row"><span>Underforecast intervals</span><strong>{fmt(m.underforecast_intervals)}</strong></div></div>
      </section>
      <section className="panel table-panel"><div className="panel-head"><div><h2>Latest eligible forecast records</h2><p>Selected publication must be available by the configured cutoff.</p></div><span className="table-count">{fmt(points.length)} rows</span></div><div className="table-wrap"><table><thead><tr><th>Delivery interval (UTC)</th><th>Forecast publish time</th><th>Cutoff (UTC)</th><th>Forecast MW</th><th>Actual MW</th><th>Error MW</th></tr></thead><tbody>{points.slice(0, 20).map((p, i) => <tr key={`${p.startTime}-${i}`}><td>{new Date(p.startTime).toISOString().replace('T',' ').slice(0,16)}</td><td>{p.publishTime ? new Date(p.publishTime).toISOString().replace('T',' ').slice(0,16) : '—'}</td><td>{p.decision_cutoff ? new Date(p.decision_cutoff).toISOString().replace('T',' ').slice(0,16) : '—'}</td><td>{fmt(p.forecast_mw)}</td><td>{fmt(p.actual_mw)}</td><td className={p.error_mw > 0 ? 'positive' : p.error_mw < 0 ? 'negative' : ''}>{fmt(p.error_mw)}</td></tr>)}</tbody></table>{points.length > 20 && <p className="table-foot">Showing first 20 intervals for readability. Accuracy metrics use all matched intervals.</p>}</div></section>
      <section className="method-note"><div className="note-icon"><AlertTriangle size={18}/></div><div><strong>Decision-support, not an automated trading instruction</strong><p>Wind forecast error can inform reserve and thermal procurement assessments, but this pilot does not calculate the exact volume to buy: demand, existing generation, interconnectors, market prices, and operational constraints are outside the supplied data scope.</p></div></section>
      <footer>GRIDWISE · Pilot analytics · Data source: Elexon BMRS FUELHH + WINDFOR</footer>
    </main>
  </div>;
}

function Metric({ label, value, suffix, note, icon }) { return <article className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><div className="metric-value">{value}<small>{suffix}</small></div><p>{note}</p></article>; }
