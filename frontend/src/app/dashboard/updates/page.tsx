'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, RefreshCw, ChevronLeft, Loader2, Database, 
  Play, FileArchive, CheckCircle2, AlertTriangle, Clock, History, Package,
  RotateCcw, Sun, Moon, Activity, LogOut
} from 'lucide-react';
import { useTheme } from '../../../lib/ThemeProvider';

export default function UpdatesCenter() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const [updates, setUpdates] = useState<string[]>([]);
  const [backups, setBackups] = useState<string[]>([]);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [isUpdating, setIsUpdating] = useState<string | null>(null);
  const [isRestoring, setIsRestoring] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const token = Cookies.get('token');

  const fetchData = async () => {
    try {
      const [upRes, backRes] = await Promise.all([
        api.get('/system/updates/available'),
        api.get('/system/backups/available')
      ]);
      setUpdates(upRes.data);
      setBackups(backRes.data);
    } catch (err) {
      console.error("Error loading maintenance data", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    fetchData();
  }, []);

  const handleBackup = async () => {
    if (!confirm("Atenție: Backup-ul total poate dura între 15-30 minute. Continuați?")) return;
    setIsBackingUp(true);
    try {
      const res = await api.post('/system/backup/trigger');
      alert(res.data.message);
    } catch (err) { alert("Eroare backup."); }
    finally { setIsBackingUp(false); }
  };

  const handleApplyUpdate = async (filename: string) => {
    if (!confirm(`Sigur doriți să aplicați actualizarea "${filename}"?`)) return;
    setIsUpdating(filename);
    try {
      const res = await api.post(`/system/updates/apply/${filename}`);
      alert("Rezultat Update:\n" + res.data.output);
      fetchData();
    } catch (err) { alert("Eroare update."); }
    finally { setIsUpdating(null); }
  };

  const handleRestore = async (filename: string) => {
    if (!confirm(`CRITIC: Sigur doriți să restaurați sistemul folosind "${filename}"? Datele actuale nesalvate se vor pierde.`)) return;
    setIsRestoring(filename);
    try {
      const res = await api.post(`/system/backups/restore/${filename}`);
      alert("Rezultat Restaurare:\n" + res.data.output);
      fetchData();
    } catch (err) { alert("Eroare restaurare."); }
    finally { setIsRestoring(null); }
  };

  if (isLoading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center"><Loader2 className="w-12 h-12 text-blue-500 animate-spin" /></div>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 font-sans flex text-left transition-colors duration-300">
      <div className="w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-white/5 p-6 flex flex-col sticky top-0 h-screen transition-colors">
        <button onClick={() => router.push('/dashboard')} className="flex items-center gap-3 mb-12 px-2 hover:opacity-80 transition-opacity">
          <ChevronLeft className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          <span className="text-xl font-black tracking-tighter text-slate-900 dark:text-white uppercase">DocAI Admin</span>
        </button>
        <div className="space-y-2">
          <button onClick={() => router.push('/dashboard')} className="w-full px-4 py-3 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-600 dark:text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <Activity className="w-4 h-4" /> Starea Sistemului
          </button>
          <div className="px-4 py-3 bg-blue-600/10 border border-blue-600/20 rounded-xl text-blue-600 dark:text-blue-400 flex items-center gap-3 font-bold text-sm">
            <RefreshCw className="w-4 h-4" /> Actualizări & Backup
          </div>
        </div>
        
        <div className="mt-auto pt-8 border-t border-slate-200 dark:border-white/5 space-y-2">
          <button onClick={toggleTheme} className="w-full px-4 py-3 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl text-slate-700 dark:text-slate-300 flex items-center gap-3 font-bold text-sm transition-all text-left">
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {theme === 'dark' ? 'Tema Luminoasă' : 'Tema Întunecată'}
          </button>
          <button onClick={() => { Cookies.remove('token'); Cookies.remove('role'); router.push('/login'); }} className="w-full px-4 py-3 hover:bg-red-500/10 rounded-xl text-slate-500 hover:text-red-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
            <LogOut className="w-4 h-4" /> Deconectare
          </button>
        </div>
      </div>

      <div className="flex-1 p-12 max-w-[1600px]">
        <div className="mb-12">
          <h1 className="text-4xl font-black text-slate-900 dark:text-white uppercase tracking-tight mb-2 tracking-tighter">Centru de Mentenanță</h1>
          <p className="text-slate-500 dark:text-slate-400 font-medium italic">Gestionează versiunile sistemului, actualizările și punctele de restaurare.</p>
        </div>

        <div className="grid grid-cols-4 gap-8">
          {/* BACKUP TRIGGER */}
          <div className="col-span-1 space-y-6">
            <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl shadow-sm transition-colors">
              <div className="p-4 bg-blue-500/10 rounded-2xl w-fit mb-6">
                <Package className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h2 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight mb-2">Creare Snapshot</h2>
              <p className="text-xs text-slate-600 dark:text-slate-500 font-medium leading-relaxed mb-8">
                Generați un pachet complet cu starea actuală a codului și a modelelor LLM.
              </p>
              <button 
                onClick={handleBackup}
                disabled={isBackingUp}
                className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-3 disabled:opacity-50 text-white shadow-lg shadow-blue-500/20"
              >
                {isBackingUp ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
                Generează Full Pack
              </button>
            </div>
          </div>

          {/* UPDATES LIST */}
          <div className="col-span-1.5 space-y-6 flex flex-col h-full">
            <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl flex-1 flex flex-col shadow-sm transition-colors">
              <h3 className="text-xs font-black text-slate-600 dark:text-slate-500 uppercase tracking-widest mb-8 flex items-center gap-2">
                <RefreshCw className="w-4 h-4" /> Pachete de Actualizare
              </h3>
              <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {updates.map((file, i) => (
                  <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-white/5 group transition-colors">
                    <div className="flex items-center gap-3">
                      <FileArchive className="w-4 h-4 text-emerald-600 dark:text-emerald-500" />
                      <span className="text-xs font-bold text-slate-700 dark:text-slate-300 truncate w-32" title={file}>{file}</span>
                    </div>
                    <button 
                      onClick={() => handleApplyUpdate(file)}
                      disabled={!!isUpdating || !!isRestoring}
                      className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500 text-emerald-600 dark:text-emerald-400 hover:text-white rounded-lg text-[9px] font-black uppercase transition-all"
                    >
                      Aplică
                    </button>
                  </div>
                ))}
                {updates.length === 0 && <p className="text-[10px] text-slate-500 dark:text-slate-600 font-bold uppercase text-center mt-12 italic">Niciun update disponibil</p>}
              </div>
            </div>
          </div>

          {/* ROLLBACK POINTS */}
          <div className="col-span-1.5 space-y-6 flex flex-col h-full">
            <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl flex-1 flex flex-col shadow-sm transition-colors">
              <h3 className="text-xs font-black text-slate-600 dark:text-slate-500 uppercase tracking-widest mb-8 flex items-center gap-2 text-indigo-600 dark:text-indigo-400">
                <History className="w-4 h-4" /> Puncte de Restaurare
              </h3>
              <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {backups.map((file, i) => (
                  <div key={i} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-950 rounded-2xl border border-indigo-200 dark:border-indigo-500/10 group border-dashed transition-colors">
                    <div className="flex items-center gap-3">
                      <Clock className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                      <span className="text-xs font-bold text-slate-700 dark:text-slate-300 truncate w-32" title={file}>{file}</span>
                    </div>
                    <button 
                      onClick={() => handleRestore(file)}
                      disabled={!!isUpdating || !!isRestoring}
                      className="px-3 py-1.5 bg-indigo-500/10 hover:bg-indigo-500 text-indigo-600 dark:text-indigo-400 hover:text-white rounded-lg text-[9px] font-black uppercase transition-all"
                    >
                      Rollback
                    </button>
                  </div>
                ))}
                {backups.length === 0 && <p className="text-[10px] text-slate-500 dark:text-slate-600 font-bold uppercase text-center mt-12 italic">Niciun backup găsit</p>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
