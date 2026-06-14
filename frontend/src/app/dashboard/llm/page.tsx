'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Brain, ChevronLeft, Loader2, Save, 
  Settings2, Info, AlertTriangle, Zap, Database, Code, FileText, Activity,
  Trash2, Download, RefreshCw, Box, Sun, Moon
} from 'lucide-react';
import { useTheme } from '../../../lib/ThemeProvider';

export default function LLMConfig() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const [config, setConfig] = useState({ 
    active_llm_engine: 'vllm',
    active_model: '', chat_temp: 0.7, chat_ctx: 16384, safety_limit: 20000,
    specialist_tabular: '', tabular_temp: 0.0, tabular_ctx: 16384,
    specialist_narrative: '', narrative_temp: 0.1, narrative_ctx: 32768,
    vllm_kv_cache_dtype: 'turboquant', vllm_gpu_utilization: 0.90, vllm_max_model_len: 32768
  });
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [importModels, setImportModels] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isImporting, setIsImporting] = useState<string | null>(null);
  const token = Cookies.get('token');

  const fetchData = async () => {
    try {
      // Fetching one by one to avoid total failure if one api is down
      const confRes = await api.get('/system/llm/config');
      setConfig(confRes.data);

      const modelsRes = await api.get('/system/models/available');
      setAvailableModels(modelsRes.data || []);

      try {
        const importRes = await api.get('/system/models/import/available');
        setImportModels(importRes.data || []);
      } catch (err) {
        console.warn("Import models api failed:", err);
        setImportModels([]);
      }
    } catch (err) {
      console.error("Critical api failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    fetchData();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.post('/system/llm/config', config);
      alert("Configurația granulară a fost activată.");
    } catch (err) { alert("Eroare la salvare."); }
    finally { setIsSaving(false); }
  };

  const handleDelete = async (modelName: string) => {
    if (!confirm(`Sigur doriți să ștergeți modelul ${modelName}? Această acțiune este ireversibilă.`)) return;
    try {
      const encodedName = encodeURIComponent(modelName);
      const res = await api.post(`/system/models/delete?model_name=${encodedName}`);
      alert(`Succes: ${modelName} a fost eliminat.`);
      fetchData(); 
    } catch (err: any) { 
      console.error("Delete error:", err);
      alert("Eroare la ștergere: " + (err.response?.data?.detail || err.message)); 
    }
  };

  const handleImport = async (folderName: string) => {
    setIsImporting(folderName);
    try {
      await api.post(`/system/models/import/run/${folderName}`);
      alert(`Importul pentru ${folderName} a început în fundal. Verificați lista modelelor în 1-2 minute.`);
      fetchData();
    } catch (err) { alert("Eroare la inițiere import."); }
    finally { setIsImporting(null); }
  };

  if (isLoading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center"><Loader2 className="w-12 h-12 text-indigo-500 animate-spin" /></div>;

  const ConfigCard = ({ title, icon: Icon, color, modelKey, tempKey, ctxKey }: any) => (
    <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl space-y-6 shadow-sm dark:shadow-none transition-all hover:shadow-md">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${
          color === 'blue' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' :
          color === 'indigo' ? 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400' :
          'bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400'
        }`}>
          <Icon className="w-5 h-5" />
        </div>
        <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">{title}</h2>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Model Desemnat</label>
          <select 
            value={(config as any)[modelKey]}
            onChange={(e) => setConfig({...config, [modelKey]: e.target.value})}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
          >
            {availableModels.map((m: any) => <option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Temperatură ({(config as any)[tempKey]})</label>
            <input 
              type="range" min="0" max="1" step="0.1" 
              value={(config as any)[tempKey]}
              onChange={(e) => setConfig({...config, [tempKey]: parseFloat(e.target.value)})}
              className="w-full accent-indigo-600 dark:accent-indigo-500 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none"
            />
          </div>
          <div>
            <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Context RAM</label>
            <select 
              value={(config as any)[ctxKey]}
              onChange={(e) => setConfig({...config, [ctxKey]: parseInt(e.target.value)})}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-[10px] font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
            >
              <option value="4096">4k</option>
              <option value="8192">8k</option>
              <option value="16384">16k</option>
              <option value="32768">32k</option>
              <option value="65536">64k</option>
              <option value="131072">128k</option>
              <option value="262144">256k</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-200 font-sans flex text-left transition-colors duration-300">
      <div className="w-80 bg-slate-100 dark:bg-slate-900 border-r border-slate-200 dark:border-white/5 p-6 flex flex-col sticky top-0 h-screen overflow-y-auto transition-colors">
        <button onClick={() => router.push('/dashboard')} className="flex items-center gap-3 mb-10 px-2 hover:opacity-80 transition-opacity">
          <ChevronLeft className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          <span className="text-xl font-black tracking-tighter text-slate-900 dark:text-white uppercase leading-none italic">DocAI Admin</span>
        </button>
        
        <div className="space-y-8">
          <div>
            <button onClick={() => router.push('/dashboard')} className="w-full px-4 py-3 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl text-slate-500 dark:text-slate-400 flex items-center gap-3 font-bold text-sm transition-all text-left mb-2">
              <Activity className="w-4 h-4" /> Starea Sistemului
            </button>
            <div className="px-4 py-3 bg-indigo-600/10 border border-indigo-600/20 rounded-xl text-indigo-600 dark:text-indigo-400 flex items-center gap-3 font-black text-[10px] uppercase tracking-widest mb-6">
              <Brain className="w-4 h-4" /> Configurație LLM
            </div>

            {/* MANAGE ACTIVE MODELS */}
            <div className="space-y-4">
              <h3 className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-2">Modele Active ({availableModels.length})</h3>
              <div className="space-y-1">
                {availableModels.map((m: any) => (
                  <div key={m.name} className="flex items-center justify-between p-3 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 group transition-all">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate-700 dark:text-slate-300 truncate max-w-[140px]">{m.name}</span>
                      <span className="text-[9px] text-slate-400 dark:text-slate-600 font-black uppercase">{(m.size / (1024**3)).toFixed(1)} GB</span>
                    </div>
                    <button 
                      type="button"
                      onClick={() => handleDelete(m.name)}
                      className="p-2 hover:bg-red-500/20 hover:text-red-600 dark:hover:text-red-400 text-slate-400 dark:text-slate-500 rounded-lg transition-all"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-200 dark:border-white/5">
            <h3 className="text-[10px] font-black text-amber-600 dark:text-amber-500 uppercase tracking-widest px-2 mb-4 flex items-center gap-2">
              <Download className="w-3 h-3" /> Import Offline
            </h3>
            <div className="space-y-2">
              {importModels.length === 0 ? (
                <p className="text-[9px] text-slate-400 dark:text-slate-600 font-bold uppercase italic px-2">Niciun folder în models/import/</p>
              ) : (
                importModels.map((folder) => (
                  <div key={folder} className="flex items-center justify-between p-3 bg-black/5 dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-xl">
                    <div className="flex items-center gap-2">
                      <Box className="w-3 h-3 text-slate-400 dark:text-slate-500" />
                      <span className="text-[10px] font-bold text-slate-700 dark:text-slate-300 truncate max-w-[120px]">{folder}</span>
                    </div>
                    <button 
                      type="button"
                      onClick={() => handleImport(folder)}
                      disabled={isImporting === folder}
                      className="p-2 bg-amber-500/20 text-amber-600 dark:text-amber-500 hover:bg-amber-500 hover:text-white rounded-lg transition-all disabled:opacity-50"
                    >
                      {isImporting === folder ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-auto pt-8 border-t border-slate-200 dark:border-white/5 space-y-2">
            <button onClick={toggleTheme} className="w-full px-4 py-3 bg-slate-200 dark:bg-white/5 hover:bg-slate-300 dark:hover:bg-white/10 rounded-xl text-slate-700 dark:text-slate-300 flex items-center gap-3 font-bold text-sm transition-all text-left">
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              {theme === 'dark' ? 'Tema Luminoasă' : 'Tema Întunecată'}
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 p-12 max-w-[1400px]">
        <div className="mb-12">
          <h1 className="text-4xl font-black text-slate-900 dark:text-white uppercase tracking-tight mb-2 tracking-tighter">Parametri Granulari LLM</h1>
          <p className="text-slate-500 font-medium italic mb-8">Ajustează comportamentul fiecărui specialist pentru performanță maximă.</p>

          <div className="flex gap-4 p-1.5 bg-slate-100 dark:bg-white/5 rounded-2xl w-fit border border-slate-200 dark:border-white/5">
            <button 
              type="button"
              onClick={() => setConfig({...config, active_llm_engine: 'vllm'})}
              className={`px-8 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                config.active_llm_engine === 'vllm' 
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              🚀 Motor vLLM (Performanță)
            </button>
            <button 
              type="button"
              onClick={() => setConfig({...config, active_llm_engine: 'ollama'})}
              className={`px-8 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                config.active_llm_engine === 'ollama' 
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              🛠️ Motor Ollama (Versatilitate)
            </button>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* PANOU MOTOR PRINCIPAL */}
            <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl space-y-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  <Zap className="w-5 h-5" />
                </div>
                <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">
                  Motor Chat Principal ({config.active_llm_engine.toUpperCase()})
                </h2>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Model Desemnat</label>
                  {config.active_llm_engine === 'vllm' ? (
                    <input 
                      type="text"
                      value={config.active_model}
                      onChange={(e) => setConfig({...config, active_model: e.target.value})}
                      placeholder="ex: casperhansen/deepseek-r1-distill-qwen-14b-awq"
                      className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
                    />
                  ) : (
                    <select 
                      value={config.active_model}
                      onChange={(e) => setConfig({...config, active_model: e.target.value})}
                      className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
                    >
                      {!availableModels.some(m => m.name === config.active_model) && config.active_model && (
                        <option value={config.active_model}>{config.active_model} (Extern/vLLM)</option>
                      )}
                      {availableModels.map((m: any) => <option key={m.name} value={m.name}>{m.name}</option>)}
                    </select>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Temperatură ({config.chat_temp})</label>
                    <input 
                      type="range" min="0" max="1" step="0.1" 
                      value={config.chat_temp}
                      onChange={(e) => setConfig({...config, chat_temp: parseFloat(e.target.value)})}
                      className="w-full accent-indigo-600 dark:accent-indigo-500 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Context RAM</label>
                    <select 
                      value={config.chat_ctx}
                      onChange={(e) => setConfig({...config, chat_ctx: parseInt(e.target.value)})}
                      className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-[10px] font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
                    >
                      <option value="4096">4k tokens</option>
                      <option value="8192">8k tokens</option>
                      <option value="16384">16k tokens</option>
                      <option value="32768">32k tokens</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* LIMITA SIGURANTA */}
            <div className="p-8 bg-blue-500/5 border border-blue-500/10 rounded-3xl flex flex-col justify-center space-y-6">
              <div className="flex gap-4 items-start">
                <Shield className="w-8 h-8 text-blue-400 flex-shrink-0 mt-1" />
                <div>
                  <h3 className="text-sm font-black text-slate-900 dark:text-white uppercase mb-2">Limită de Siguranță (Safety)</h3>
                  <p className="text-[11px] text-slate-500 font-medium leading-relaxed mb-6">
                    Controlează volumul maxim de date brute care ajung în raționament. 
                    Limitează contextul trimis către specialiști pentru a evita blocajele.
                  </p>
                  <select 
                    value={config.safety_limit}
                    onChange={(e) => setConfig({...config, safety_limit: parseInt(e.target.value)})}
                    className="w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all shadow-sm"
                  >
                    <option value="10000">10k (Rapid)</option>
                    <option value="20000">20k (Standard)</option>
                    <option value="50000">50k (Complex)</option>
                    <option value="100000">100k (Audit Full)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* CARDURI SPECIALISTI (MEREU VIZIBILE) */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
            <ConfigCard title="Specialist Tabular" icon={Code} color="indigo" modelKey="specialist_tabular" tempKey="tabular_temp" ctxKey="tabular_ctx" />
            <ConfigCard title="Specialist Narrativ" icon={FileText} color="fuchsia" modelKey="specialist_narrative" tempKey="narrative_temp" ctxKey="narrative_ctx" />
          </div>

          {config.active_llm_engine === 'vllm' && (
            <div className="p-6 bg-amber-500/5 border border-amber-500/10 rounded-2xl">
              <div className="flex gap-3 items-center">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <p className="text-[10px] font-bold text-amber-600 uppercase tracking-widest">
                  Atenție: vLLM este activ. Containerul Ollama poate fi oprit automat pentru economisirea VRAM.
                </p>
              </div>
            </div>
          )}

          <button type="submit" disabled={isSaving} className="w-full py-5 bg-indigo-600 hover:bg-indigo-500 rounded-2xl text-sm font-black uppercase tracking-widest transition-all shadow-xl flex items-center justify-center gap-3">
            {isSaving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />} Salvează Toți Parametrii
          </button>
        </form>
      </div>
    </div>
  );
}
