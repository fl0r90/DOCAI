'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Users, Folder, FileText, Activity, 
  LogOut, LayoutDashboard, Database,
  Cpu, HardDrive, Terminal, Zap, Thermometer, Clock, Server, Brain, RefreshCw, X,
  Sun, Moon
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
          <div className="px-4 py-3 bg-indigo-600/10 border border-indigo-600/20 rounded-xl text-indigo-600 dark:text-indigo-400 flex items-center gap-3 font-bold text-sm">
            <Activity className="w-4 h-4" /> Starea Sistemului
          </div>
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
          <div className="mb-12">
            <h1 className="text-4xl font-black text-slate-900 dark:text-white uppercase tracking-tight mb-2 tracking-tighter italic">Panou de Control</h1>
            <p className="text-slate-500 font-medium italic">Monitorizarea infrastructurii de analiză forensic.</p>
          </div>

          {/* HARDWARE GRID */}
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
              {/* OPERATIVE FLUX (NEW) */}
              <div className="p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-indigo-500/20 rounded-3xl shadow-xl dark:shadow-indigo-900/10 transition-all">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xs font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-[0.2em] flex items-center gap-2">
                    <Terminal className="w-4 h-4" /> Flux Operativ Consolidat
                  </h3>
                  <div className="flex items-center gap-2">
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
        </div>
      </div>

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
