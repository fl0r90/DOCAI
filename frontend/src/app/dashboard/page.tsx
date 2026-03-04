'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Users, Folder, FileText, Activity, 
  LogOut, LayoutDashboard, Database,
  Cpu, HardDrive, Terminal, Zap, Thermometer, Clock, Server, Brain, RefreshCw, X
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [containers, setContainers] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedLogs, setSelectedLogs] = useState<string | null>(null);
  const [containerLogs, setContainerLogs] = useState<string>('');

  const fetchData = async () => {
    try {
      const userRes = await api.get('/auth/me');
      setUser(userRes.data);

      if (userRes.data.role === 'ADMIN') {
        const [mRes, cRes, aRes] = await Promise.all([
          api.get('/system/metrics'),
          api.get('/system/docker/containers'),
          api.get('/system/audit?limit=10')
        ]);
        setMetrics(mRes.data);
        setContainers(cRes.data);
        setAudit(aRes.data);

        setHistory(prev => {
          const newPoint = {
            cpu: mRes.data?.cpu?.usage || 0,
            gpu: mRes.data?.gpu?.usage || 0,
            ram: mRes.data?.ram?.percent || 0
          };
          return [...prev, newPoint].slice(-60);
        });
      } else {
        router.push('/cases');
      }
    } catch (err) {
      console.error("Dashboard error", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const token = Cookies.get('token');
    if (!token) { router.push('/login'); return; }
    
    fetchData();
    const interval = setInterval(fetchData, 5000); 
    return () => clearInterval(interval);
  }, []);

  const fetchLogs = async (name: string) => {
    try {
      const res = await api.get(`/system/docker/logs/${name}`);
      setContainerLogs(res.data.logs);
      setSelectedLogs(name);
    } catch (err) { alert("Eroare loguri."); }
  };

  const handleLogout = () => {
    Cookies.remove('token');
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
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans">
      {/* SIDEBAR */}
      <div className="fixed left-0 top-0 bottom-0 w-72 bg-slate-900 border-r border-white/5 p-6 flex flex-col">
        <div className="flex items-center gap-3 mb-12 px-2">
          <div className="p-2 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-900/40">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <span className="text-xl font-black tracking-tighter text-white uppercase block leading-none">DocAI Admin</span>
            <span className="text-[9px] font-black text-indigo-500 uppercase tracking-[0.2em] mt-1 block">v0.1 BETA</span>
          </div>
        </div>

        <nav className="flex-1 space-y-2">
          <div className="px-4 py-3 bg-indigo-600/10 border border-indigo-600/20 rounded-xl text-indigo-400 flex items-center gap-3 font-bold text-sm">
            <Activity className="w-4 h-4" /> System Health
          </div>
          <button onClick={() => router.push('/dashboard/llm')} className="w-full px-4 py-3 hover:bg-white/5 rounded-xl text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <Brain className="w-4 h-4" /> Configurație LLM
          </button>
          <button onClick={() => router.push('/dashboard/updates')} className="w-full px-4 py-3 hover:bg-white/5 rounded-xl text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <RefreshCw className="w-4 h-4" /> Actualizări & Backup
          </button>
          <button onClick={() => router.push('/users')} className="w-full px-4 py-3 hover:bg-white/5 rounded-xl text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <Users className="w-4 h-4" /> Management Useri
          </button>
        </nav>

        <div className="mt-auto pt-6 border-t border-white/5">
          <button onClick={handleLogout} className="w-full px-4 py-3 hover:bg-red-500/10 rounded-xl text-slate-500 hover:text-red-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <LogOut className="w-4 h-4" /> Deconectare
          </button>
        </div>
      </div>

      {/* CONTENT */}
      <div className="ml-72 p-12 max-w-[1600px]">
        <div className="mb-12">
          <h1 className="text-4xl font-black text-white uppercase tracking-tight mb-2 tracking-tighter">Panou de Control</h1>
          <p className="text-slate-500 font-medium italic">Starea sistemului în timp real.</p>
        </div>

        {/* HARDWARE GRID */}
        <div className="grid grid-cols-4 gap-6 mb-12">
          {/* CPU */}
          <div className="p-8 bg-slate-900/50 border border-white/5 rounded-3xl group relative overflow-hidden flex flex-col">
            <div className="relative z-10">
              <div className="flex justify-between items-start mb-4">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2"><Cpu className="w-3 h-3"/> CPU</p>
                <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded flex items-center gap-1">
                  <Thermometer className="w-2.5 h-2.5" />{metrics?.cpu?.temp || 0}°C
                </span>
              </div>
              <div className="flex items-end gap-2 mb-2">
                <span className="text-5xl font-black text-white leading-none">{(metrics?.cpu?.usage || 0).toFixed(1)}%</span>
              </div>
              <p className="text-[10px] text-slate-500 font-bold uppercase truncate mb-4" title={metrics?.cpu?.name || 'N/A'}>{metrics?.cpu?.name || 'Procesor'}</p>
            </div>
            <MiniGraph data={history} color="#3b82f6" dataKey="cpu" />
            <div className="absolute bottom-0 left-0 h-1 bg-blue-500 transition-all duration-1000" style={{width: `${metrics?.cpu?.usage || 0}%`}} />
          </div>

          {/* RAM */}
          <div className="p-8 bg-slate-900/50 border border-white/5 rounded-3xl group relative overflow-hidden flex flex-col">
            <div className="relative z-10">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2"><Server className="w-3 h-3"/> RAM</p>
              <div className="flex items-end gap-2 mb-2">
                <span className="text-5xl font-black text-white leading-none">{(metrics?.ram?.percent || 0).toFixed(1)}%</span>
              </div>
              <p className="text-[10px] text-slate-500 font-bold uppercase mb-4">{metrics?.ram?.free || 0}GB Liberi / {metrics?.ram?.total || 0}GB Total</p>
            </div>
            <MiniGraph data={history} color="#10b981" dataKey="ram" />
            <div className="absolute bottom-0 left-0 h-1 bg-emerald-500 transition-all duration-1000" style={{width: `${metrics?.ram?.percent || 0}%`}} />
          </div>

          {/* GPU */}
          <div className="p-8 bg-slate-900/50 border border-white/5 rounded-3xl group relative overflow-hidden flex flex-col">
            <div className="relative z-10">
              <div className="flex justify-between items-start mb-4">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2"><Zap className="w-3 h-3"/> GPU</p>
                <span className="text-[10px] font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded flex items-center gap-1">
                  <Thermometer className="w-2.5 h-2.5" />{metrics?.gpu?.temp || 0}°C
                </span>
              </div>
              <div className="flex items-end gap-2 mb-2">
                <span className="text-5xl font-black text-white leading-none">{(metrics?.gpu?.usage || 0).toFixed(1)}%</span>
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
          <div className="p-8 bg-slate-900/50 border border-white/5 rounded-3xl group relative overflow-hidden flex flex-col">
            <div className="relative z-10">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2"><HardDrive className="w-3 h-3"/> Stocare</p>
              <div className="flex items-end gap-2 mb-2">
                <span className="text-5xl font-black text-white leading-none">{(metrics?.disk?.percent || 0).toFixed(1)}%</span>
              </div>
              <p className="text-[10px] text-slate-500 font-bold uppercase mb-4">{metrics?.disk?.free || 0}GB Disponibili / {metrics?.disk?.total || 0}GB</p>
            </div>
            <div className="absolute bottom-0 left-0 h-1 bg-red-500 transition-all duration-1000" style={{width: `${metrics?.disk?.percent || 0}%`}} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-8">
          <div className="col-span-2 space-y-6">
            <div className="p-8 bg-slate-900/50 border border-white/5 rounded-3xl">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                <Terminal className="w-4 h-4" /> Servicii Docker
              </h3>
              <div className="space-y-3">
                {containers.map((c, i) => (
                  <div key={i} className="flex items-center justify-between p-4 bg-slate-950 rounded-2xl border border-white/5 hover:border-white/10 transition-all group">
                    <div className="flex items-center gap-4">
                      <div className={`w-2 h-2 rounded-full ${c.status === 'running' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
                      <div>
                        <p className="text-sm font-black text-white uppercase tracking-tight">{c.name}</p>
                        <p className="text-[10px] text-slate-500 font-bold uppercase">{c.image}</p>
                      </div>
                    </div>
                    <button onClick={() => fetchLogs(c.name)} className="px-3 py-1.5 bg-slate-800 hover:bg-white/10 rounded-lg text-[10px] font-black uppercase tracking-widest text-slate-400 transition-all opacity-0 group-hover:opacity-100">Loguri</button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="p-8 bg-slate-900/50 border border-white/5 rounded-3xl">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2">
                <Clock className="w-4 h-4" /> Audit Securitate
              </h3>
              <div className="space-y-4">
                {audit.map((log, i) => (
                  <div key={i} className="flex flex-col gap-1 pb-4 border-b border-white/5 last:border-0">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">{log.action}</span>
                      <span className="text-[9px] font-bold text-slate-600">{new Date(log.created_at).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-xs font-bold text-slate-300">{log.username}</p>
                    <p className="text-[10px] text-slate-500 italic line-clamp-1 pr-4">{log.details}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* LOGS MODAL */}
      {selectedLogs && (
        <div className="fixed inset-0 z-[100] bg-slate-950/90 backdrop-blur-md flex flex-col p-8 animate-in fade-in duration-300">
          <div className="max-w-[1200px] mx-auto w-full flex-1 flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-black text-white uppercase tracking-tighter flex items-center gap-3">
                  <Terminal className="w-6 h-6 text-indigo-400" />
                  Terminal: {selectedLogs}
                </h2>
              </div>
              <button onClick={() => setSelectedLogs(null)} className="p-3 bg-white/5 hover:bg-white/10 rounded-full transition-colors text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="flex-1 bg-black border border-white/10 rounded-2xl p-6 font-mono text-[11px] overflow-y-auto custom-scrollbar text-emerald-500/80 leading-relaxed shadow-2xl">
              {containerLogs.split('\n').map((line, i) => <div key={i} className="mb-1 hover:bg-white/5">{line}</div>)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
