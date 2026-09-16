'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Users, Folder, FileText, Activity, 
  LogOut, LayoutDashboard, Database,
  Cpu, HardDrive, Terminal, Zap, Thermometer, Clock, Server, Brain, RefreshCw, X,
  Sun, Moon, Bug, Play, Pause, Download, Filter, Search, ChevronRight, CheckCircle,
  AlertTriangle, AlertCircle, Info, Code, Eye, Copy, Check
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import { useTheme } from '../../lib/ThemeProvider';

export default function Dashboard() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [containers, setContainers] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [operativeLogs, setOperativeLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedLogs, setSelectedLogs] = useState<string | null>(null);
  const [containerLogs, setContainerLogs] = useState<string>('');
  const [debugLogs, setDebugLogs] = useState<{ logs: any[]; total: number; has_more: boolean }>({ logs: [], total: 0, has_more: false });
  const [selectedLogLevel, setSelectedLogLevel] = useState<string | null>(null);
  const [selectedLogService, setSelectedLogService] = useState<string | null>(null);
  const [isDebugLogsOpen, setIsDebugLogsOpen] = useState(false);
  const [selectedLogItem, setSelectedLogItem] = useState<any | null>(null);
  const [debugSearchTerm, setDebugSearchTerm] = useState<string>('');
  const [autoRefreshDebug, setAutoRefreshDebug] = useState<boolean>(true);
  const [copiedTraceId, setCopiedTraceId] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const userRes = await api.get('/auth/me');
      setUser(userRes.data);

      if (userRes.data.role === 'ADMIN') {
        // Apeluri paralele cu protectie individuala
        const fetchMetrics = api.get('/system/metrics').then(res => setMetrics(res.data)).catch(() => console.error("Metrics fail"));
        const fetchContainers = api.get('/system/docker/containers').then(res => setContainers(res.data)).catch(() => console.error("Containers fail"));
        const fetchAudit = api.get('/system/audit?limit=10').then(res => setAudit(res.data)).catch(() => console.error("Audit fail"));
        const fetchLiveLogs = api.get('/system/logs/live').then(res => setOperativeLogs(res.data)).catch(() => console.error("Live logs fail"));

        await Promise.allSettled([fetchMetrics, fetchContainers, fetchAudit, fetchLiveLogs]);

        if (metrics) {
          setHistory(prev => {
            const newPoint = {
              cpu: metrics.cpu?.usage || 0,
              gpu: metrics.gpu?.usage || 0,
              ram: metrics.ram?.percent || 0
            };
            return [...prev, newPoint].slice(-60);
          });
        }
      } else {
        router.push('/cases');
      }
    } catch (err) {
      console.error("Dashboard error", err);
    } finally {
      setIsLoading(false);
    }
  };

  // LIVE LOGS POLLING
  useEffect(() => {
    if (!selectedLogs) return;
    const fetchLiveLogs = async () => {
      try {
        const res = await api.get(`/system/docker/logs/${selectedLogs}`);
        setContainerLogs(res.data.logs);
      } catch (err) { console.error("Logs polling error"); }
    };
    fetchLiveLogs();
    const logInterval = setInterval(fetchLiveLogs, 3000); // Update la 3 secunde
    return () => clearInterval(logInterval);
  }, [selectedLogs]);

  // TELEMETRIE & DEBUG LOGS POLLING (Rulează DOAR când panoul este deschis)
  useEffect(() => {
    if (!isDebugLogsOpen || !autoRefreshDebug) return;
    const fetchDebugLogs = async () => {
      try {
        let url = `/system/debug-logs?limit=250`;
        if (selectedLogLevel) url += `&level=${selectedLogLevel}`;
        if (selectedLogService) url += `&service=${selectedLogService}`;
        const res = await api.get(url);
        setDebugLogs(res.data);
      } catch (err) {
        console.error("Debug logs polling error", err);
      }
    };
    fetchDebugLogs();
    const debugLogInterval = setInterval(fetchDebugLogs, 3000);
    return () => clearInterval(debugLogInterval);
  }, [isDebugLogsOpen, autoRefreshDebug, selectedLogLevel, selectedLogService]);

  const refreshDebugLogsNow = async () => {
    try {
      let url = `/system/debug-logs?limit=250`;
      if (selectedLogLevel) url += `&level=${selectedLogLevel}`;
      if (selectedLogService) url += `&service=${selectedLogService}`;
      const res = await api.get(url);
      setDebugLogs(res.data);
    } catch (err) {
      console.error("Manual debug logs refresh error", err);
    }
  };

  const downloadDebugLogs = () => {
    if (!debugLogs.logs || debugLogs.logs.length === 0) return;
    const content = debugLogs.logs.map(l => JSON.stringify(l)).join('\n');
    const blob = new Blob([content], { type: 'application/x-ndjson' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `docai-telemetry-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.jsonl`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyTrace = (traceId: string) => {
    if (!traceId) return;
    navigator.clipboard.writeText(traceId);
    setCopiedTraceId(traceId);
    setTimeout(() => setCopiedTraceId(null), 2000);
  };

  useEffect(() => {
    const token = Cookies.get('token');
    if (!token) { router.push('/login'); return; }
    
    fetchData();
    const interval = setInterval(fetchData, 5000); 
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    Cookies.remove('token');
    Cookies.remove('role');
    router.push('/login');
  };

  if (isLoading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center"><Activity className="w-12 h-12 text-blue-500 animate-spin" /></div>;

  const MiniGraph = ({ data, color, dataKey }: { data: any[], color: string, dataKey: string }) => (
    <div className="h-16 w-full mt-4 opacity-50">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
          <YAxis hide domain={[0, 100]} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className="h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-200 font-sans flex overflow-hidden transition-colors duration-300">
      {/* SIDEBAR */}
      <div className="w-72 bg-slate-100 dark:bg-slate-900 border-r border-slate-200 dark:border-white/5 p-6 flex flex-col flex-shrink-0">
        <div className="flex items-center gap-3 mb-12 px-2">
          <div className="p-2 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-900/40">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="text-xl font-black tracking-tighter text-slate-900 dark:text-white uppercase block leading-none italic">DocAI Admin</span>
            <span title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-[9px] font-black text-indigo-500 uppercase tracking-[0.2em] mt-1 block">v0.7.0 BETA</span>
          </div>
        </div>

        <nav className="flex-1 space-y-2">
          <button 
            onClick={() => setIsDebugLogsOpen(false)}
            className={`w-full px-4 py-3 rounded-xl flex items-center gap-3 font-bold text-sm transition-all text-left ${
              !isDebugLogsOpen 
                ? 'bg-indigo-600/10 border border-indigo-600/20 text-indigo-600 dark:text-indigo-400' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
            }`}
          >
            <Activity className="w-4 h-4" /> Starea Sistemului
          </button>
          <button 
            onClick={() => setIsDebugLogsOpen(true)}
            className={`w-full px-4 py-3 rounded-xl flex items-center gap-3 font-bold text-sm transition-all text-left ${
              isDebugLogsOpen 
                ? 'bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 shadow-sm' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
            }`}
          >
            <Bug className="w-4 h-4" /> Telemetrie & Debug
          </button>
          <button onClick={() => router.push('/dashboard/llm')} className="w-full px-4 py-3 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl text-slate-500 dark:text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <Brain className="w-4 h-4" /> Configurație LLM
          </button>
          <button onClick={() => router.push('/dashboard/updates')} className="w-full px-4 py-3 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl text-slate-500 dark:text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <RefreshCw className="w-4 h-4" /> Actualizări & Backup
          </button>
          <button onClick={() => router.push('/users')} className="w-full px-4 py-3 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl text-slate-500 dark:text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <Users className="w-4 h-4" /> Management Useri
          </button>
          <button onClick={() => router.push('/cases')} className="w-full px-4 py-3 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl text-slate-500 dark:text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left border-t border-slate-200 dark:border-white/5 pt-6 mt-4">
            <Folder className="w-4 h-4" /> Dosare Criminalistice
          </button>
        </nav>

        <div className="mt-auto pt-6 border-t border-slate-200 dark:border-white/5 space-y-2">
          <button onClick={toggleTheme} className="w-full px-4 py-3 bg-slate-200 dark:bg-white/5 hover:bg-slate-300 dark:hover:bg-white/10 rounded-xl text-slate-700 dark:text-slate-300 flex items-center gap-3 font-bold text-sm transition-all text-left">
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {theme === 'dark' ? 'Tema Luminoasă' : 'Tema Întunecată'}
          </button>
          <button onClick={handleLogout} className="w-full px-4 py-3 hover:bg-red-500/10 rounded-xl text-slate-500 hover:text-red-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <LogOut className="w-4 h-4" /> Deconectare
          </button>
        </div>
      </div>

      {/* CONTENT AREA WITH SCROLLING */}
      <div className="flex-1 overflow-y-auto custom-scrollbar bg-white dark:bg-slate-950 transition-colors duration-300">
        <div className="p-12 max-w-[1600px] mx-auto">
          {/* HEADER */}
          <div className="mb-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-4xl font-black text-slate-900 dark:text-white uppercase tracking-tight mb-2 tracking-tighter italic">
                {isDebugLogsOpen ? 'Telemetrie & Debug Forensic' : 'Panou de Control'}
              </h1>
              <p className="text-slate-500 font-medium italic">
                {isDebugLogsOpen 
                  ? 'Audit structurat JSONL, latență operațiuni, recall hibrid și diagnostic criminalistic pe subsisteme.'
                  : 'Monitorizarea infrastructurii de analiză forensic.'}
              </p>
            </div>
            {isDebugLogsOpen && (
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setAutoRefreshDebug(!autoRefreshDebug)}
                  className={`px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 border transition-all ${
                    autoRefreshDebug 
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 shadow-sm' 
                      : 'bg-slate-500/10 border-slate-500/30 text-slate-500 hover:bg-slate-500/20'
                  }`}
                >
                  {autoRefreshDebug ? (
                    <>
                      <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <Pause className="w-3.5 h-3.5" /> Live Stream
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" /> Reia Stream
                    </>
                  )}
                </button>
                <button
                  onClick={refreshDebugLogsNow}
                  className="px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-indigo-600/10 border border-indigo-600/20 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-600/20 transition-all shadow-sm"
                  title="Reîmprospătează imediat"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Reîmprospătează
                </button>
                <button
                  onClick={downloadDebugLogs}
                  className="px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all border border-slate-200 dark:border-white/5 shadow-sm"
                  title="Descarcă logurile curente în format JSONL"
                >
                  <Download className="w-3.5 h-3.5" /> Export JSONL
                </button>
                <button
                  onClick={() => setIsDebugLogsOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 bg-slate-200 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-300 dark:hover:bg-white/10 transition-all"
                >
                  Înapoi
                </button>
              </div>
            )}
          </div>

          {isDebugLogsOpen ? (
            /* TELEMETRIE & DEBUG FORENSIC CONSOLE */
            <div className="space-y-6 pb-20">
              {/* KPI COUNTERS */}
              <div className="grid grid-cols-5 gap-4">
                <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                    <Database className="w-3 h-3" /> Evenimente Încărcate
                  </p>
                  <span className="text-3xl font-black text-slate-900 dark:text-white leading-none">
                    {debugLogs.logs?.length || 0}
                  </span>
                  <span className="text-[10px] text-slate-500 font-bold block mt-1">din ultimele 5GB loguri</span>
                </div>

                <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm">
                  <p className="text-[10px] font-black text-rose-400 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                    <AlertCircle className="w-3 h-3" /> Erori Critice
                  </p>
                  <span className="text-3xl font-black text-rose-500 leading-none">
                    {(debugLogs.logs || []).filter(l => l.level === 'ERROR' || l.level === 'CRITICAL').length}
                  </span>
                  <span className="text-[10px] text-slate-500 font-bold block mt-1">necesită investigație</span>
                </div>

                <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm">
                  <p className="text-[10px] font-black text-amber-400 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                    <AlertTriangle className="w-3 h-3" /> Avertismente
                  </p>
                  <span className="text-3xl font-black text-amber-500 leading-none">
                    {(debugLogs.logs || []).filter(l => l.level === 'WARNING').length}
                  </span>
                  <span className="text-[10px] text-slate-500 font-bold block mt-1">fallback / degradare</span>
                </div>

                <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm">
                  <p className="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                    <Info className="w-3 h-3" /> Informații
                  </p>
                  <span className="text-3xl font-black text-blue-500 leading-none">
                    {(debugLogs.logs || []).filter(l => l.level === 'INFO').length}
                  </span>
                  <span className="text-[10px] text-slate-500 font-bold block mt-1">stare operațională</span>
                </div>

                <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm">
                  <p className="text-[10px] font-black text-purple-400 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                    <Bug className="w-3 h-3" /> Debug Detaliat
                  </p>
                  <span className="text-3xl font-black text-purple-500 leading-none">
                    {(debugLogs.logs || []).filter(l => l.level === 'DEBUG').length}
                  </span>
                  <span className="text-[10px] text-slate-500 font-bold block mt-1">payloads & sub-apeluri</span>
                </div>
              </div>

              {/* FILTERS & SEARCH BAR */}
              <div className="p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-2xl shadow-sm flex flex-wrap items-center justify-between gap-4">
                {/* LEVEL BUTTONS */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1">
                    <Filter className="w-3.5 h-3.5" /> Nivel:
                  </span>
                  {[
                    { label: 'TOATE', value: null },
                    { label: 'DEBUG', value: 'DEBUG' },
                    { label: 'INFO', value: 'INFO' },
                    { label: 'WARN', value: 'WARN' },
                    { label: 'ERROR', value: 'ERROR' },
                  ].map((lvl) => (
                    <button
                      key={lvl.label}
                      onClick={() => setSelectedLogLevel(lvl.value)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-black tracking-wider uppercase transition-all ${
                        selectedLogLevel === lvl.value
                          ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-sm'
                          : 'bg-slate-100 dark:bg-white/5 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10'
                      }`}
                    >
                      {lvl.label}
                    </button>
                  ))}
                </div>

                {/* SERVICE DROPDOWN */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black text-slate-400 uppercase tracking-wider">Serviciu:</span>
                  <select
                    value={selectedLogService || ''}
                    onChange={(e) => setSelectedLogService(e.target.value ? e.target.value : null)}
                    className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/10 text-xs font-bold rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Toate Serviciile</option>
                    <option value="worker">worker (Ingestie & Pipeline Tasks)</option>
                    <option value="ocr">ocr_service (Docling Multithreaded)</option>
                    <option value="chat">chat_service (Hybrid Recall & Tools)</option>
                    <option value="llm">llm_client (Ollama / LM Studio)</option>
                    <option value="system">system (Sistem & API)</option>
                  </select>
                </div>

                {/* SEARCH INPUT */}
                <div className="relative min-w-[280px]">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Filtrează mesaj, trace_id, event..."
                    value={debugSearchTerm}
                    onChange={(e) => setDebugSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-8 py-2 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-xs font-medium text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  {debugSearchTerm && (
                    <button
                      onClick={() => setDebugSearchTerm('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>

              {/* LOG STREAM TABLE */}
              <div className="bg-slate-900 dark:bg-black/90 border border-slate-800 dark:border-white/10 rounded-3xl overflow-hidden shadow-2xl">
                <div className="px-6 py-4 bg-slate-950/80 border-b border-white/5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Terminal className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-300">
                      Flux Telemetrie Criminalistică (Ultimele {debugLogs.logs?.length || 0} evenimente)
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500">
                    <span>Buffer Tail: 64KB Blocks</span>
                    <span>•</span>
                    <span className="text-emerald-400 font-bold">Zero-RAM Seek</span>
                  </div>
                </div>

                <div className="p-4 max-h-[700px] overflow-y-auto custom-scrollbar font-mono text-[11px] divide-y divide-white/5">
                  {(debugLogs.logs || [])
                    .filter(log => {
                      if (!debugSearchTerm) return true;
                      const term = debugSearchTerm.toLowerCase();
                      const msg = (log.message || '').toLowerCase();
                      const evt = (log.event || log.action || '').toLowerCase();
                      const trace = (log.trace_id || '').toLowerCase();
                      const srv = (log.service || '').toLowerCase();
                      const caller = (log.caller || '').toLowerCase();
                      const dataStr = typeof log.data === 'object' ? JSON.stringify(log.data).toLowerCase() : String(log.data || '').toLowerCase();
                      return msg.includes(term) || evt.includes(term) || trace.includes(term) || srv.includes(term) || caller.includes(term) || dataStr.includes(term);
                    })
                    .map((log, index) => {
                      const levelColor =
                        log.level === 'ERROR' || log.level === 'CRITICAL'
                          ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                          : log.level === 'WARNING' || log.level === 'WARN'
                          ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          : log.level === 'INFO'
                          ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                          : 'bg-purple-500/15 text-purple-400 border-purple-500/30';

                      const serviceBadgeColor =
                        log.service === 'chat_service'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : log.service === 'llm_client'
                          ? 'bg-fuchsia-500/15 text-fuchsia-400'
                          : log.service === 'ocr_service'
                          ? 'bg-cyan-500/15 text-cyan-400'
                          : (log.service === 'worker' || log.service === 'worker_tasks')
                          ? 'bg-indigo-500/15 text-indigo-400'
                          : 'bg-slate-500/15 text-slate-300';

                      const timeFormatted = log.timestamp ? log.timestamp.split('T')[1]?.slice(0, 12) || log.timestamp : 'N/A';
                      const eventName = log.event || log.action || 'EVENT';
                      const messageText = log.message || (typeof log.data === 'string' ? log.data : log.data?.stage ? `Etapă: ${log.data.stage} (${log.data.status || 'OK'})` : log.error?.message || eventName);

                      return (
                        <div
                          key={index}
                          className="py-2.5 px-3 hover:bg-white/[0.04] transition-colors rounded-xl flex items-start gap-4 group cursor-pointer"
                          onClick={() => setSelectedLogItem(log)}
                        >
                          {/* TIMESTAMP */}
                          <div className="flex-shrink-0 text-slate-500 font-semibold select-none text-[10px] w-20 pt-0.5">
                            {timeFormatted}
                          </div>

                          {/* LEVEL BADGE */}
                          <div className="flex-shrink-0 w-20">
                            <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-wider border block text-center ${levelColor}`}>
                              {log.level}
                            </span>
                          </div>

                          {/* SERVICE BADGE */}
                          <div className="flex-shrink-0 w-28">
                            <span className={`px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-wider block text-center truncate ${serviceBadgeColor}`} title={log.service}>
                              {log.service}
                            </span>
                          </div>

                          {/* EVENT BADGE */}
                          <div className="flex-shrink-0 w-32">
                            <span className="text-[10px] font-bold text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/5 block text-center truncate" title={eventName}>
                              {eventName}
                            </span>
                          </div>

                          {/* MESSAGE & DURATION */}
                          <div className="flex-1 min-w-0 flex items-center justify-between gap-4">
                            <div className="truncate">
                              <span className="text-slate-200 group-hover:text-white transition-colors font-medium">
                                {messageText}
                              </span>
                              {log.trace_id && (
                                <span
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleCopyTrace(log.trace_id);
                                  }}
                                  className="ml-2 px-1.5 py-0.5 text-[9px] bg-slate-800 hover:bg-slate-700 text-slate-400 rounded cursor-pointer transition-colors"
                                  title="Click pentru copiere Trace ID"
                                >
                                  {copiedTraceId === log.trace_id ? 'Copiat!' : `trace:${log.trace_id.slice(0, 8)}`}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-3 flex-shrink-0">
                              {log.duration_ms !== undefined && log.duration_ms !== null && (
                                <span className="text-[10px] font-black text-amber-400/90 bg-amber-500/10 px-1.5 py-0.5 rounded flex items-center gap-1">
                                  ⚡ {log.duration_ms.toFixed(0)}ms
                                </span>
                              )}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedLogItem(log);
                                }}
                                className="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 text-[9px] font-black uppercase tracking-widest flex items-center gap-1"
                              >
                                <Code className="w-3 h-3" /> Payload
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}

                  {(!debugLogs.logs || debugLogs.logs.length === 0) && (
                    <div className="py-20 text-center text-slate-500">
                      <Bug className="w-10 h-10 mx-auto mb-3 opacity-30 text-indigo-400" />
                      <p className="font-black uppercase tracking-widest text-xs">Nicio înregistrare de telemetrie disponibilă.</p>
                      <p className="text-[10px] text-slate-600 mt-1">Asigură-te că DEBUG_LOGGING_ENABLED=true și că serviciile generează activitate.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            /* HARDWARE GRID & DASHBOARD REGULAR */
            <>
              <div className="grid grid-cols-4 gap-6 mb-12">
                {/* CPU */}
                <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl group relative overflow-hidden flex flex-col transition-all">
                  <div className="relative z-10">
                    <div className="flex justify-between items-start mb-4">
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2"><Cpu className="w-3 h-3"/> CPU</p>
                      <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded flex items-center gap-1">
                        <Thermometer className="w-2.5 h-2.5" />{metrics?.cpu?.temp || 0}°C
                      </span>
                    </div>
                    <div className="flex items-end gap-2 mb-2">
                      <span className="text-5xl font-black text-slate-900 dark:text-white leading-none">{(metrics?.cpu?.usage || 0).toFixed(1)}%</span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase truncate mb-4" title={metrics?.cpu?.name || 'N/A'}>{metrics?.cpu?.name || 'Procesor'}</p>
                  </div>
                  <MiniGraph data={history} color="#3b82f6" dataKey="cpu" />
                  <div className="absolute bottom-0 left-0 h-1 bg-blue-500 transition-all duration-1000" style={{width: `${metrics?.cpu?.usage || 0}%`}} />
                </div>

                {/* RAM */}
                <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl group relative overflow-hidden flex flex-col transition-all">
                  <div className="relative z-10">
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2"><Server className="w-3 h-3"/> RAM</p>
                    <div className="flex items-end gap-2 mb-2">
                      <span className="text-5xl font-black text-slate-900 dark:text-white leading-none">{(metrics?.ram?.percent || 0).toFixed(1)}%</span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mb-4">{metrics?.ram?.free || 0}GB Liberi / {metrics?.ram?.total || 0}GB Total</p>
                  </div>
                  <MiniGraph data={history} color="#10b981" dataKey="ram" />
                  <div className="absolute bottom-0 left-0 h-1 bg-emerald-500 transition-all duration-1000" style={{width: `${metrics?.ram?.percent || 0}%`}} />
                </div>

                {/* GPU */}
                <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl group relative overflow-hidden flex flex-col transition-all">
                  <div className="relative z-10">
                    <div className="flex justify-between items-start mb-4">
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2"><Zap className="w-3 h-3"/> GPU</p>
                      <span className="text-[10px] font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded flex items-center gap-1">
                        <Thermometer className="w-2.5 h-2.5" />{metrics?.gpu?.temp || 0}°C
                      </span>
                    </div>
                    <div className="flex items-end gap-2 mb-2">
                      <span className="text-5xl font-black text-slate-900 dark:text-white leading-none">{(metrics?.gpu?.usage || 0).toFixed(1)}%</span>
                    </div>
                    <div className="flex flex-col mb-4">
                      <p className="text-[10px] text-slate-500 font-bold uppercase truncate" title={metrics?.gpu?.name || 'N/A'}>{metrics?.gpu?.name || 'Placă Video'}</p>
                      <p className="text-[10px] text-indigo-400 font-black uppercase tracking-widest mt-1">VRAM: {metrics?.gpu?.memory_used || 0}GB / {metrics?.gpu?.memory_total || 0}GB</p>
                    </div>
                  </div>
                  <MiniGraph data={history} color="#6366f1" dataKey="gpu" />
                  <div className="absolute bottom-0 left-0 h-1 bg-indigo-500 transition-all duration-1000" style={{width: `${metrics?.gpu?.usage || 0}%`}} />
                </div>

                {/* STORAGE */}
                <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl group relative overflow-hidden flex flex-col transition-all">
                  <div className="relative z-10">
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2"><HardDrive className="w-3 h-3"/> Stocare</p>
                    <div className="flex items-end gap-2 mb-2">
                      <span className="text-5xl font-black text-slate-900 dark:text-white leading-none">{(metrics?.disk?.percent || 0).toFixed(1)}%</span>
                    </div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase mb-4">{metrics?.disk?.free || 0}GB Disponibili / {metrics?.disk?.total || 0}GB</p>
                  </div>
                  <div className="absolute bottom-0 left-0 h-1 bg-red-500 transition-all duration-1000" style={{width: `${metrics?.disk?.percent || 0}%`}} />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-8 pb-20">
                <div className="col-span-2 space-y-6">
                  {/* OPERATIVE FLUX */}
                  <div className="p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-indigo-500/20 rounded-3xl shadow-xl dark:shadow-indigo-900/10 transition-all">
                    <div className="flex justify-between items-center mb-6">
                      <h3 className="text-xs font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-[0.2em] flex items-center gap-2">
                        <Terminal className="w-4 h-4" /> Flux Operativ Consolidat
                      </h3>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => setIsDebugLogsOpen(true)}
                          className="text-[10px] font-black text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 uppercase tracking-widest flex items-center gap-1 transition-all"
                        >
                          Telemetrie Detaliată <ChevronRight className="w-3 h-3" />
                        </button>
                        <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse" />
                        <span className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase">Live Stream</span>
                      </div>
                    </div>
                    <div className="bg-slate-50 dark:bg-black/60 rounded-2xl p-6 font-mono text-[10px] h-[300px] overflow-y-auto custom-scrollbar border border-slate-200 dark:border-white/5 shadow-inner">
                      {operativeLogs.length > 0 ? operativeLogs.map((log, i) => (
                        <div key={i} className="mb-1.5 flex gap-3 group">
                          <span className={`flex-shrink-0 font-black px-1.5 py-0.5 rounded-[4px] text-[9px] ${
                            log.service === 'WORKER' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' :
                            log.service === 'LLM' ? 'bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400' :
                            'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                          }`}>
                            {log.service}
                          </span>
                          <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-200 transition-colors font-medium">{log.message}</span>
                        </div>
                      )) : (
                        <div className="h-full flex items-center justify-center text-slate-300 dark:text-slate-700 font-black uppercase tracking-widest italic text-center">
                          Așteptare date din infrastructură...
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl shadow-sm transition-all">
                    <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                      <Terminal className="w-4 h-4" /> Servicii Docker
                    </h3>
                    <div className="space-y-3">
                      {containers.map((c, i) => (
                        <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-white/5 hover:border-slate-300 dark:hover:border-white/10 transition-all group">
                          <div className="flex items-center gap-4">
                            <div className={`w-2 h-2 rounded-full ${c.status === 'running' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
                            <div>
                              <p className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">{c.name}</p>
                              <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">{c.image}</p>
                            </div>
                          </div>
                          <button onClick={() => setSelectedLogs(c.name)} className="px-3 py-1.5 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-white/10 rounded-lg text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400 transition-all opacity-0 group-hover:opacity-100">Live Logs</button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl shadow-sm transition-all">
                    <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                      <Clock className="w-4 h-4" /> Audit Securitate
                    </h3>
                    <div className="space-y-4">
                      {audit.map((log, i) => (
                        <div key={i} className="flex flex-col gap-1 pb-4 border-b border-slate-100 dark:border-white/5 last:border-0">
                          <div className="flex justify-between items-center">
                            <span className="text-[10px] font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-widest">{log.action}</span>
                            <span className="text-[9px] font-bold text-slate-400 dark:text-slate-600">{new Date(log.created_at).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-xs font-bold text-slate-800 dark:text-slate-300">{log.username}</p>
                          <p className="text-[10px] text-slate-500 italic line-clamp-1 pr-4">
                            {typeof log.details === 'object' ? JSON.stringify(log.details) : log.details}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* PAYLOAD INSPECTION MODAL */}
      {selectedLogItem && (
        <div className="fixed inset-0 z-[110] bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-6 animate-in fade-in duration-200">
          <div className="max-w-[900px] w-full bg-slate-900 border border-slate-700/60 rounded-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
            <div className="p-6 bg-slate-950 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl">
                  <Code className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-black text-white uppercase tracking-tight flex items-center gap-2">
                    Inspectare Detaliu Eveniment
                    <span className="text-xs px-2 py-0.5 rounded bg-white/10 text-slate-300 font-mono">
                      {selectedLogItem.event}
                    </span>
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                    {selectedLogItem.timestamp} • {selectedLogItem.service} • {selectedLogItem.level}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedLogItem(null)}
                className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto custom-scrollbar space-y-4 font-mono text-xs">
              {/* METADATA BAR */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-black/40 border border-white/5 rounded-xl">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Trace ID</span>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-300 truncate mr-2" title={selectedLogItem.trace_id || 'N/A'}>
                      {selectedLogItem.trace_id || 'N/A'}
                    </span>
                    {selectedLogItem.trace_id && (
                      <button
                        onClick={() => handleCopyTrace(selectedLogItem.trace_id)}
                        className="text-slate-400 hover:text-white p-1"
                        title="Copiază Trace ID"
                      >
                        {copiedTraceId === selectedLogItem.trace_id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    )}
                  </div>
                </div>

                <div className="p-3 bg-black/40 border border-white/5 rounded-xl">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Latență</span>
                  <span className="text-amber-400 font-black">
                    {selectedLogItem.duration_ms !== undefined && selectedLogItem.duration_ms !== null
                      ? `${selectedLogItem.duration_ms.toFixed(2)} ms`
                      : 'N/A'}
                  </span>
                </div>

                <div className="p-3 bg-black/40 border border-white/5 rounded-xl">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Caller Code</span>
                  <span className="text-indigo-300 truncate block" title={selectedLogItem.caller || 'N/A'}>
                    {selectedLogItem.caller || 'N/A'}
                  </span>
                </div>
              </div>

              {/* MESSAGE */}
              <div className="p-4 bg-black/40 border border-white/5 rounded-xl">
                <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Mesaj descriptiv</span>
                <p className="text-slate-200 leading-relaxed font-sans text-sm">
                  {selectedLogItem.message}
                </p>
              </div>

              {/* DATA JSON PAYLOAD */}
              <div className="p-4 bg-black/60 border border-white/10 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] text-indigo-400 uppercase font-bold flex items-center gap-1.5">
                    <Terminal className="w-3 h-3" /> Payload Structurat (Data)
                  </span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(selectedLogItem.data || {}, null, 2));
                      alert("Payload copiat în clipboard!");
                    }}
                    className="text-[10px] text-slate-400 hover:text-white uppercase font-bold flex items-center gap-1 transition-colors"
                  >
                    <Copy className="w-3 h-3" /> Copiază JSON
                  </button>
                </div>
                <pre className="p-4 bg-black/80 rounded-lg text-emerald-400 text-[11px] overflow-x-auto custom-scrollbar border border-white/5 leading-relaxed max-h-[300px]">
                  {JSON.stringify(selectedLogItem.data || {}, null, 2)}
                </pre>
              </div>
            </div>

            <div className="p-4 bg-slate-950 border-t border-white/5 flex justify-end">
              <button
                onClick={() => setSelectedLogItem(null)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-black text-xs uppercase tracking-wider transition-colors"
              >
                Închide
              </button>
            </div>
          </div>
        </div>
      )}

      {/* LOGS MODAL (LIVE) */}
      {selectedLogs && (
        <div className="fixed inset-0 z-[100] bg-slate-950/90 backdrop-blur-md flex flex-col p-8 animate-in fade-in duration-300">
          <div className="max-w-[1200px] mx-auto w-full flex-1 flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-black text-white uppercase tracking-tighter flex items-center gap-3 italic">
                  <Terminal className="w-6 h-6 text-indigo-400" />
                  Terminal Live: {selectedLogs}
                </h2>
                <p className="text-[10px] text-indigo-500 font-black uppercase tracking-widest mt-1 animate-pulse">Streaming activ • Update la 3s</p>
              </div>
              <button onClick={() => setSelectedLogs(null)} className="p-3 bg-white/5 hover:bg-white/10 rounded-full transition-colors text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="flex-1 bg-black/80 border border-white/10 rounded-2xl p-6 font-mono text-[11px] overflow-y-auto custom-scrollbar text-emerald-500/80 leading-relaxed shadow-2xl relative" style={{ maxHeight: 'calc(100vh - 250px)' }}>
              <div className="absolute top-0 right-0 p-4 opacity-20 pointer-events-none">
                <Terminal className="w-32 h-32" />
              </div>
              <div className="relative z-10">
                {containerLogs ? containerLogs.split('\n').map((line, i) => (
                  <div key={i} className="mb-1 hover:bg-white/5 border-l border-emerald-500/20 pl-4 transition-colors">
                    <span className="text-emerald-900 mr-2">[{i+1}]</span>{line}
                  </div>
                )) : <div className="text-slate-600 animate-pulse font-black uppercase">Se conectează la stream-ul Docker...</div>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
