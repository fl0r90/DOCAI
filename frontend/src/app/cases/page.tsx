'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Folder, Plus, Search, Filter, Loader2, 
  ChevronRight, Calendar, Users, FileText, LayoutGrid, List, Brain, Trash2,
  Sun, Moon, LogOut
} from 'lucide-react';
import { useTheme } from '../../lib/ThemeProvider';

export default function Cases() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const [cases, setCases] = useState<any[]>([]);
  const [user, setUser] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [activeModel, setActiveModel] = useState<string>('...');
  const [newCase, setNewCase] = useState({ name: '', description: '' });
  const token = Cookies.get('token');

  const fetchData = async () => {
    try {
      const [casesRes, modelRes, userRes] = await Promise.all([
        api.get('/cases'),
        api.get('/system/models/active'),
        api.get('/auth/me')
      ]);
      setCases(casesRes.data);
      setActiveModel(modelRes.data.active_model);
      setUser(userRes.data);
    } catch (err) {
      router.push('/login');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    fetchData();
  }, []);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/cases', newCase);
      setNewCase({ name: '', description: '' });
      setIsCreating(false);
      fetchData();
    } catch (err) {
      alert("Eroare la crearea dosarului.");
    }
  };

  const handleDeleteCase = async (e: React.MouseEvent, id: number, name: string) => {
    e.stopPropagation();
    if (confirm(`ATENȚIE: Ștergerea dosarului "${name}" va elimina DEFINITIV toate documentele, vectorii și relațiile din hartă. Continui?`)) {
      try {
        await api.post(`/cases/${id}/delete`);
        fetchData();
      } catch (err) {
        alert("Eroare la ștergere.");
      }
    }
  };

  const handleLogout = () => {
    Cookies.remove('token');
    Cookies.remove('role');
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 font-sans transition-colors duration-300">
      {/* HEADER */}
      <div className="bg-white/80 dark:bg-slate-900/50 border-b border-slate-200 dark:border-white/5 sticky top-0 z-50 backdrop-blur-md transition-all">
        <div className="max-w-[1600px] mx-auto px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight uppercase leading-none italic">DocAI</h1>
              <span title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-[9px] font-black text-blue-600 dark:text-blue-500 uppercase tracking-[0.2em] mt-1 block">v0.7.0 BETA</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={toggleTheme}
              className="p-2.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl text-slate-600 dark:text-slate-400 transition-all border border-slate-200 dark:border-white/5"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <Brain className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span className="text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest">Model: {activeModel}</span>
            </div>
            {user?.role && user.role !== 'WORKER' && (
              <button 
                onClick={() => setIsCreating(true)}
                className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-500/20 text-white"
              >
                <Plus className="w-4 h-4" /> Dosar Nou
              </button>
            )}
            <button 
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 text-xs font-black uppercase tracking-widest transition-all"
              title="Deconectare din cont"
            >
              <LogOut className="w-4 h-4" /> Ieșire
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-[1600px] mx-auto px-8 py-12">
        {isLoading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-4 opacity-50">
            <Loader2 className="w-10 h-10 animate-spin text-blue-600 dark:text-blue-500" />
            <p className="text-xs font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">Se încarcă arhiva...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cases.map((c) => (
              <div 
                key={c.id} 
                onClick={() => router.push(`/cases/${c.id}`)}
                className="group bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-white/5 rounded-3xl p-8 hover:bg-slate-50 dark:hover:bg-slate-900/60 hover:border-blue-500/30 dark:hover:border-blue-500/30 transition-all cursor-pointer relative overflow-hidden shadow-sm hover:shadow-xl"
              >
                <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
                  <Folder className="w-24 h-24 text-slate-900 dark:text-white" />
                </div>
                
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-blue-500/10 rounded-2xl group-hover:bg-blue-500/20 transition-colors">
                      <Folder className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-tight">{c.name}</h3>
                      <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest">ID Dosar: #{c.id}</p>
                    </div>
                  </div>
                  {user?.role && user.role !== 'WORKER' && (
                    <button 
                      onClick={(e) => handleDeleteCase(e, c.id, c.name)}
                      className="p-2.5 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-500 rounded-xl transition-all opacity-0 group-hover:opacity-100 z-20"
                      title="Șterge Dosar"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <p className="text-sm text-slate-600 dark:text-slate-400 font-medium mb-8 line-clamp-2 h-10">{c.description || 'Nicio descriere adăugată.'}</p>

                <div className="flex items-center justify-between pt-6 border-t border-slate-100 dark:border-white/5">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-tighter">
                      <FileText className="w-3.5 h-3.5" /> {c.document_count} documente
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-tighter">
                      <Calendar className="w-3.5 h-3.5" /> {new Date(c.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 dark:text-slate-700 group-hover:text-blue-600 dark:group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MODAL CREARE DOSAR */}
      {isCreating && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-950/80 backdrop-blur-md">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-3xl p-8 shadow-2xl animate-in zoom-in-95 duration-200">
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
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/5 rounded-xl px-4 py-3.5 text-sm font-bold text-slate-900 dark:text-white focus:outline-none focus:border-blue-500/50 transition-all"
                  placeholder="Ex: Control Fiscal Octombrie 2024"
                />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Descriere / Obiective</label>
                <textarea 
                  value={newCase.description}
                  onChange={(e) => setNewCase({...newCase, description: e.target.value})}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/5 rounded-xl px-4 py-3.5 text-sm font-bold text-slate-900 dark:text-white focus:outline-none focus:border-blue-500/50 transition-all h-32 resize-none"
                  placeholder="Detalii despre scopul analizei..."
                />
              </div>
              <button 
                type="submit"
                className="w-full py-4 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-500/20 text-white"
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

function X({ className }: { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
  );
}
