"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, Building2, User, Database, Landmark, AlertTriangle, Loader2, ScrollText, History, Clock, FileText, ArrowRight, Plus, X, Sun, Moon, LogOut } from 'lucide-react';
import api from '../lib/api';
import Cookies from 'js-cookie';
import { useTheme } from '../lib/ThemeProvider';

export default function ForensicDashboard() {
  const { theme, toggleTheme } = useTheme();
  const [entities, setEntities] = useState([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [activityLogs, setActivityLogs] = useState<any[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [queueStatus, setQueueStatus] = useState<any>(null);
  const [mounted, setMounted] = useState(false);
  
  const [isCreating, setIsCreating] = useState(false);
  const [newCase, setNewCase] = useState({ name: '', description: '' });
  
  const router = useRouter();

  const token = Cookies.get('token');
  const role = Cookies.get('role');

  // Primul check: Dacă nu există token, zburăm la login imediat
  useEffect(() => {
    if (mounted && (!token || !role)) {
      router.push('/login');
    }
  }, [mounted, token, role, router]);

  const refreshData = async () => {
    if (!token) return;
    try {
      const cRes = await api.get('/cases/');
      setCases(cRes.data);

      if (!currentUser) {
        const uRes = await api.get('/auth/me');
        setCurrentUser(uRes.data);
      }

      const qRes = await api.get('/system/queue/status');
      setQueueStatus(qRes.data);

      if (selectedCaseId) {
        const [eRes, dRes, aRes] = await Promise.all([
          api.get(`/cases/${selectedCaseId}/entities`),
          api.get(`/cases/${selectedCaseId}/documents`),
          api.get(`/system/audit?limit=10`)
        ]);
        setEntities(eRes.data);
        setDocs(dRes.data);
        setActivityLogs(aRes.data);
      } else {
        setEntities([]);
        setDocs([]);
        setActivityLogs([]);
      }
    } catch (err) { 
      console.error("Eroare API", err);
      // Dacă primim 401, înseamnă că tokenul e expirat
      if ((err as any).response?.status === 401) {
        Cookies.remove('token');
        Cookies.remove('role');
        router.push('/login');
      }
    }
  };

  useEffect(() => {
    setMounted(true);
    if (token) {
      refreshData();
      const interval = setInterval(refreshData, 3000);
      const timeInterval = setInterval(() => setCurrentTime(new Date()), 1000);
      return () => {
        clearInterval(interval);
        clearInterval(timeInterval);
      };
    }
  }, [selectedCaseId, token]);

  // Nu afișăm interfața până nu suntem siguri că suntem logați
  if (!mounted || !token || !role) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  const handleUpload = async (e: any) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    if (!selectedCaseId) {
      alert("Te rugăm să selectezi un dosar înainte de încărcare!");
      e.target.value = null;
      return;
    }

    setUploading(true);
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    formData.append('case_id', selectedCaseId);

    try {
      await api.post('/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    } catch (err) {
      alert("Eroare la încărcare.");
    } finally {
      setUploading(false);
      e.target.value = null;
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post('/cases', newCase);
      setNewCase({ name: '', description: '' });
      setIsCreating(false);
      refreshData();
      setSelectedCaseId(res.data.id.toString());
    } catch (err) {
      alert("Eroare la crearea dosarului.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 p-8 font-sans animate-in fade-in duration-500 transition-colors duration-300">
      <nav className="flex justify-between items-center mb-12 border-b border-slate-200 dark:border-slate-800 pb-6">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-500" />
          <h1 className="text-2xl font-black tracking-tighter uppercase text-slate-900 dark:text-white">Doc<span className="text-blue-500">AI</span></h1>
          <span title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-[10px] font-black text-blue-500/50 uppercase tracking-widest mt-1 ml-2">v0.7.0 BETA</span>
        </div>
        <div className="text-right hidden md:block">
          {currentUser && (
            <p className="text-sm font-bold text-slate-600 dark:text-slate-300">
              Bun venit, <span className="text-blue-600 dark:text-blue-400">@{currentUser.username}</span>!
            </p>
          )}
          <p className="text-[10px] font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest">
            {currentTime.toLocaleDateString('ro-RO')} | {currentTime.toLocaleTimeString('ro-RO')}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <button 
            onClick={toggleTheme}
            className="p-2.5 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-lg text-slate-600 dark:text-slate-400 transition-all"
            title="Schimbă Tema"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          {(role === 'MASTER' || role === 'ADMIN') && (
            <>
              <button 
                onClick={() => setIsCreating(true)}
                className="bg-blue-600 text-white hover:bg-blue-500 px-4 py-2 rounded-lg text-sm font-bold shadow-lg shadow-blue-600/20 transition-all flex items-center gap-2"
              >
                <Plus className="w-4 h-4" /> Dosar Nou
              </button>
              <button 
                onClick={() => router.push('/cases')}
                className="bg-purple-600/10 text-purple-500 hover:bg-purple-600/20 px-4 py-2 rounded-lg text-sm font-bold border border-purple-500/20 transition-all"
              >
                Dosare
              </button>
            </>
          )}
          {role === 'ADMIN' && (
            <button 
              onClick={() => router.push('/dashboard')}
              className="bg-blue-600/10 text-blue-500 hover:bg-blue-600/20 px-4 py-2 rounded-lg text-sm font-bold border border-blue-500/20 transition-all"
            >
              System
            </button>
          )}
          <button 
            onClick={() => { Cookies.remove('token'); Cookies.remove('role'); router.push('/login'); }} 
            className="flex items-center gap-2 bg-red-500/10 text-red-500 px-4 py-2 rounded-lg text-sm font-bold border border-red-500/20 hover:bg-red-500/20 transition-all ml-2"
            title="Deconectare din cont"
          >
            <LogOut className="w-4 h-4" /> Ieșire
          </button>
        </div>
      </nav>

      <div className="mb-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col md:flex-row gap-4 items-end">
        <div className="flex-1 w-full">
          <h2 className="text-sm font-bold text-slate-400 dark:text-slate-500 mb-4 tracking-widest uppercase">Dosar de lucru</h2>
          <select 
            value={selectedCaseId} 
            onChange={e => setSelectedCaseId(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:border-blue-500 text-sm appearance-none cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
          >
            <option value="">-- Alege un dosar pentru a adăuga probe --</option>
            {cases.map((c: any) => (
              <option key={c.id} value={c.id}>Dosar #{c.id} - {c.name}</option>
            ))}
          </select>
        </div>
        {selectedCaseId && (
          <button 
            onClick={() => router.push(`/cases/${selectedCaseId}`)}
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-xl font-bold text-sm transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20 shrink-0"
          >
            Deschide Investigația <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {selectedCaseId && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          <label className="border-2 border-dashed border-slate-200 dark:border-slate-800 p-10 rounded-2xl flex flex-col items-center hover:border-blue-500 transition-all cursor-pointer bg-white dark:bg-slate-900/30 group">
            <Landmark className="mb-4 text-slate-400 dark:text-slate-500 group-hover:text-blue-500 transition-colors w-10 h-10" />
            <span className="text-xs font-mono text-slate-400 dark:text-slate-500 group-hover:text-blue-600 dark:group-hover:text-blue-400 tracking-widest font-bold">ÎNCARCĂ DOCUMENTE FISCALE</span>
            <input type="file" multiple className="hidden" onChange={handleUpload} disabled={uploading} />
          </label>
          
          <label className="border-2 border-dashed border-slate-200 dark:border-slate-800 p-10 rounded-2xl flex flex-col items-center hover:border-emerald-500 transition-all cursor-pointer bg-white dark:bg-slate-900/30 group">
            <Database className="mb-4 text-slate-400 dark:text-slate-500 group-hover:text-emerald-500 transition-colors w-10 h-10" />
            <span className="text-xs font-mono text-slate-400 dark:text-slate-500 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 tracking-widest font-bold">ÎNCARCĂ DOSAR COMPLET</span>
            {/* @ts-ignore */}
            <input type="file" webkitdirectory="" directory="" multiple className="hidden" onChange={handleUpload} disabled={uploading} />
          </label>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {queueStatus && queueStatus.queue_total > 0 && (
            <section className="animate-in slide-in-from-top-4 duration-500">
              <div className={`border rounded-2xl p-6 flex flex-col md:flex-row justify-between items-center gap-6 shadow-2xl ${queueStatus.is_llm_active ? 'bg-orange-500/5 border-orange-500/20' : 'bg-blue-500/5 border-blue-500/20'}`}>
                <div className="flex items-center gap-4">
                  <div className={`p-4 rounded-2xl ${queueStatus.is_llm_active ? 'bg-orange-500/10 text-orange-500' : 'bg-blue-500/10 text-blue-500'}`}>
                    {queueStatus.is_llm_active ? <AlertTriangle className="w-8 h-8 animate-pulse" /> : <Clock className="w-8 h-8" />}
                  </div>
                  <div>
                    <h3 className="text-lg font-black uppercase tracking-tighter">
                      {queueStatus.is_llm_active ? 'Procesare în Pauză' : 'Coadă Procesare'}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                      {queueStatus.is_llm_active ? 'Se eliberează resursele GPU pentru interogare LLM...' : 'Documentele sunt procesate în ordinea priorității.'}
                    </p>
                  </div>
                </div>
                
                <div className="flex gap-8 text-center border-l border-slate-200 dark:border-slate-800 pl-8 h-full items-center">
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase mb-1">Poziția Ta</p>
                    <p className="text-2xl font-black text-slate-900 dark:text-white">{queueStatus.position || '-'}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase mb-1">Total Coadă</p>
                    <p className="text-2xl font-black text-slate-500 dark:text-slate-400">{queueStatus.queue_total}</p>
                  </div>
                  <div className="bg-white dark:bg-slate-950 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-800 shadow-inner">
                    <p className="text-[10px] font-bold text-blue-600 dark:text-blue-500 uppercase mb-1">ETA Estimativ</p>
                    <p className="text-xl font-black text-slate-900 dark:text-white">~{queueStatus.eta_minutes} <span className="text-[10px] text-slate-400 dark:text-slate-500">min</span></p>
                  </div>
                </div>
              </div>
            </section>
          )}

          {docs.some(d => d.status !== 'COMPLETED' && d.status !== 'FAILED') && (
            <section>
              <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase mb-4 tracking-widest">Procesare Live</h2>
              <div className="space-y-2">
                {docs.filter(d => d.status !== 'COMPLETED' && d.status !== 'FAILED').map(doc => (
                  <div key={doc.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-3 rounded-lg flex justify-between items-center">
                    <span className="text-sm font-mono truncate max-w-md text-slate-700 dark:text-slate-300">{doc.filename}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-blue-600 dark:text-blue-400 font-bold animate-pulse">{doc.status}</span>
                      <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase mb-6 tracking-widest">Entități Identificate în Dosar</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {entities.length === 0 && <p className="text-xs text-slate-400 dark:text-slate-600 italic">Nicio entitate extrasă încă.</p>}
              {entities.map((e: any) => (
                <div key={e.id} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl group hover:border-blue-500 transition-all border-l-4 border-l-blue-500/30 shadow-lg shadow-blue-500/5">
                  <div className="flex justify-between items-start mb-4">
                    {e.entity_type === 'FIRMA' ? <Building2 className="text-emerald-500 dark:text-emerald-400" /> : <User className="text-sky-500 dark:text-sky-400" />}
                    <span className="text-[10px] font-mono text-slate-400 dark:text-slate-600">ID: {e.id}</span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{e.official_name}</h3>
                  <p className="text-xs font-mono text-slate-500 mb-6">{e.cui_cif_cnp || 'Identificator lipsă'}</p>
                  <div className="flex items-center gap-3">
                    <div className="h-1 flex-1 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-red-600" style={{ width: `${e.risk_score || 5}%` }}></div>
                    </div>
                    <span className="text-[10px] font-black text-red-600 dark:text-red-500">{e.risk_score || 0}% RISK</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-8">
          {selectedCaseId && (
            <section>
              <h2 className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase mb-4 tracking-widest flex items-center gap-2">
                <History className="w-4 h-4" /> Activitate Recentă
              </h2>
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 max-h-[500px] overflow-y-auto space-y-3 shadow-2xl">
                {activityLogs.length === 0 && <p className="text-xs text-slate-400 dark:text-slate-600 text-center py-4 italic">Nicio activitate.</p>}
                {activityLogs.map(log => (
                  <div key={log.id} className="flex justify-between items-start border-b border-slate-100 dark:border-slate-800/50 pb-3 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/10 transition-colors px-1 pt-1">
                    <div className="flex items-start gap-3">
                      <div className={`p-1.5 rounded-lg mt-0.5 ${log.action.includes('UPLOAD') ? 'bg-blue-500/10 text-blue-600 dark:text-blue-500' : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'}`}>
                        {log.action.includes('UPLOAD') ? <FileText className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-700 dark:text-slate-300">
                          <span className="text-blue-600 dark:text-blue-400">@{log.username}</span>
                        </p>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 mb-1">{log.action.toLowerCase().replace('_', ' ')}</p>
                        <p className="text-[9px] text-slate-400 dark:text-slate-600 italic truncate max-w-[150px]">{log.details}</p>
                      </div>
                    </div>
                    <span className="text-[8px] font-mono text-slate-400 dark:text-slate-700 whitespace-nowrap">{new Date(log.created_at).toLocaleTimeString('ro-RO')}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* MODAL CREARE DOSAR */}
      {isCreating && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-950/90 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tighter">Creează Dosar Nou</h2>
              <button onClick={() => setIsCreating(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full text-slate-500 transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>
            <form onSubmit={handleCreateCase} className="space-y-6">
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Nume Investigație</label>
                <input 
                  autoFocus
                  required
                  value={newCase.name}
                  onChange={(e) => setNewCase({...newCase, name: e.target.value})}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3.5 text-sm font-bold text-slate-900 dark:text-white focus:outline-none focus:border-blue-500 transition-all"
                  placeholder="Ex: Control Fiscal Octombrie 2024"
                />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Descriere / Obiective</label>
                <textarea 
                  value={newCase.description}
                  onChange={(e) => setNewCase({...newCase, description: e.target.value})}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-4 py-3.5 text-sm font-bold text-slate-900 dark:text-white focus:outline-none focus:border-blue-500 transition-all h-32 resize-none"
                  placeholder="Detalii despre scopul analizei..."
                />
              </div>
              <button 
                type="submit"
                className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-600/20 text-white"
              >
                Lansează Dosarul
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}