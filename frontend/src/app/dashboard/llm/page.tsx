'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Brain, ChevronLeft, Loader2, Save, 
  Settings2, Info, AlertTriangle, Zap, Database, Code, FileText, Activity,
  Trash2, Download, RefreshCw, Box, Sun, Moon, Server, Globe, CheckCircle2, XCircle, LogOut, Cpu
} from 'lucide-react';
import { useTheme } from '../../../lib/ThemeProvider';

export default function LLMConfig() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const [config, setConfig] = useState({ 
    active_llm_engine: 'ollama',
    active_model: '', chat_temp: 0.7, chat_ctx: 16384, safety_limit: 20000,
    specialist_processing: '', processing_temp: 0.0, processing_ctx: 32768,
    specialist_tabular: '', tabular_temp: 0.0, tabular_ctx: 16384,
    specialist_narrative: '', narrative_temp: 0.1, narrative_ctx: 32768,
    vllm_kv_cache_dtype: 'turboquant', vllm_gpu_utilization: 0.90, vllm_max_model_len: 32768,
    lmstudio_url: 'http://host.docker.internal:1234/v1',
    lmstudio_api_key: '',
    lmstudio_timeout: 300,
    reranker_device: 'cpu',
    reranker_model: 'BAAI/bge-reranker-v2-m3'
  });
  const [testStatus, setTestStatus] = useState<{ testing: boolean; success?: boolean; message?: string } | null>(null);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [importModels, setImportModels] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isImporting, setIsImporting] = useState<string | null>(null);
  const [importProgress, setImportProgress] = useState<any>(null);
  const [pullModelName, setPullModelName] = useState('');
  const [isPulling, setIsPulling] = useState(false);
  const [pullProgress, setPullProgress] = useState<any>(null);
  const token = Cookies.get('token');

  const fetchData = async () => {
    try {
      // Fetching one by one to avoid total failure if one api is down
      const confRes = await api.get('/system/llm/config');
      const currentConf = confRes.data;

      const modelsRes = await api.get('/system/models/available');
      const modelsList = modelsRes.data || [];
      setAvailableModels(modelsList);

      if (currentConf.active_llm_engine === 'lmstudio' && modelsList.length > 0) {
        const firstModel = modelsList[0]?.name || modelsList[0]?.model || '';
        const chosenModel = currentConf.active_model || firstModel;
        currentConf.active_model = chosenModel;
        currentConf.specialist_processing = chosenModel;
        currentConf.specialist_tabular = chosenModel;
        currentConf.specialist_narrative = chosenModel;
      }
      if (!currentConf.specialist_processing) {
        currentConf.specialist_processing = currentConf.specialist_narrative || currentConf.specialist_tabular || currentConf.active_model || '';
      }
      if (currentConf.processing_temp === undefined) {
        currentConf.processing_temp = currentConf.tabular_temp ?? 0.0;
      }
      if (currentConf.processing_ctx === undefined) {
        currentConf.processing_ctx = currentConf.narrative_ctx || currentConf.tabular_ctx || 32768;
      }
      setConfig(currentConf);

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

  // Polling pentru status pull/import
  useEffect(() => {
    let interval: any = null;
    if (isPulling || isImporting) {
      interval = setInterval(async () => {
        try {
          if (isPulling) {
            const res = await api.get('/system/models/pull/status');
            setPullProgress(res.data);
            if (!res.data.active) {
              setIsPulling(false);
              fetchData();
            }
          }
          if (isImporting) {
            const res = await api.get('/system/models/import/status');
            setImportProgress(res.data);
            if (!res.data.active) {
              setIsImporting(null);
              fetchData();
            }
          }
        } catch (err) {
          console.warn("Status poll error:", err);
        }
      }, 1500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPulling, isImporting]);

  const handleActiveModelChange = (modelName: string) => {
    if (config.active_llm_engine === 'lmstudio') {
      setConfig(prev => ({
        ...prev,
        active_model: modelName,
        specialist_processing: modelName,
        specialist_tabular: modelName,
        specialist_narrative: modelName
      }));
    } else {
      setConfig(prev => ({
        ...prev,
        active_model: modelName
      }));
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const payload = { ...config };
      if (payload.active_llm_engine === 'lmstudio') {
        payload.specialist_processing = payload.active_model;
        payload.specialist_tabular = payload.active_model;
        payload.specialist_narrative = payload.active_model;
      } else {
        payload.specialist_tabular = payload.specialist_processing;
        payload.specialist_narrative = payload.specialist_processing;
        payload.tabular_temp = payload.processing_temp;
        payload.narrative_temp = payload.processing_temp;
        payload.tabular_ctx = payload.processing_ctx;
        payload.narrative_ctx = payload.processing_ctx;
      }
      await api.post('/system/llm/config', payload);
      alert("Configurația a fost salvată cu succes.");
      fetchData();
    } catch (err) { alert("Eroare la salvare."); }
    finally { setIsSaving(false); }
  };

  const handleTestConnection = async () => {
    setTestStatus({ testing: true });
    try {
      const res = await api.post('/system/llm/test-connection', {
        url: config.lmstudio_url,
        api_key: config.lmstudio_api_key
      });
      if (res.data.success) {
        const detectedModel = res.data.models?.[0] || '';
        setTestStatus({
          testing: false,
          success: true,
          message: `Conectat cu succes! (${res.data.latency_ms}ms) - ${res.data.count} modele detectate. Model activ alocat: ${detectedModel || 'Niciunul'}`
        });
        const modelsRes = await api.get('/system/models/available');
        setAvailableModels(modelsRes.data || []);

        if (detectedModel) {
          setConfig(prev => ({
            ...prev,
            active_model: detectedModel,
            specialist_processing: detectedModel,
            specialist_tabular: detectedModel,
            specialist_narrative: detectedModel
          }));
        }
      } else {
        setTestStatus({
          testing: false,
          success: false,
          message: res.data.error || 'Conexiunea a eșuat.'
        });
      }
    } catch (err: any) {
      setTestStatus({
        testing: false,
        success: false,
        message: err.response?.data?.detail || err.message || 'Eroare la testarea conexiunii.'
      });
    }
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

  const handleImport = async (item: any) => {
    const itemName = typeof item === 'string' ? item : item.name;
    setIsImporting(itemName);
    setImportProgress({ active: true, status: "processing", detail: `Import '${itemName}' în curs...`, percent: 10 });
    try {
      await api.post(`/system/models/import/run/${encodeURIComponent(itemName)}`);
    } catch (err: any) { 
      alert("Eroare la inițiere import: " + (err.response?.data?.detail || err.message)); 
      setIsImporting(null);
    }
  };

  const handlePullModel = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const name = pullModelName.trim();
    if (!name) {
      alert("Introduceți tag-ul modelului (ex: qwen2.5:14b sau hf.co/...).");
      return;
    }
    setIsPulling(true);
    setPullProgress({ active: true, status: "connecting", detail: `Conectare pentru '${name}'...`, percent: 0, model: name });
    try {
      await api.post('/system/models/pull', { name });
    } catch (err: any) {
      alert("Eroare la inițiere descărcare: " + (err.response?.data?.detail || err.message));
      setIsPulling(false);
    }
  };

  if (isLoading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center"><Loader2 className="w-12 h-12 text-indigo-500 animate-spin" /></div>;

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
              <h3 className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest px-2">
                Modele Active ({availableModels.length})
              </h3>
              <div className="space-y-1">
                {availableModels.map((m: any) => {
                  const mName = m.name || m.model;
                  return (
                    <div key={mName} className="flex items-center justify-between p-3 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 group transition-all">
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 truncate max-w-[140px]">{mName}</span>
                        {m.size ? (
                          <span className="text-[9px] text-slate-400 dark:text-slate-600 font-black uppercase">{(m.size / (1024**3)).toFixed(1)} GB</span>
                        ) : (
                          <span className="text-[9px] text-purple-500 dark:text-purple-400 font-black uppercase">LM Studio</span>
                        )}
                      </div>
                      {config.active_llm_engine === 'ollama' && (
                        <button 
                          type="button"
                          onClick={() => handleDelete(mName)}
                          className="p-2 hover:bg-red-500/20 hover:text-red-600 dark:hover:text-red-400 text-slate-400 dark:text-slate-500 rounded-lg transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="mt-auto pt-8 border-t border-slate-200 dark:border-white/5 space-y-2">
            <button onClick={toggleTheme} className="w-full px-4 py-3 bg-slate-200 dark:bg-white/5 hover:bg-slate-300 dark:hover:bg-white/10 rounded-xl text-slate-700 dark:text-slate-300 flex items-center gap-3 font-bold text-sm transition-all text-left">
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              {theme === 'dark' ? 'Tema Luminoasă' : 'Tema Întunecată'}
            </button>
            <button onClick={() => { Cookies.remove('token'); Cookies.remove('role'); router.push('/login'); }} className="w-full px-4 py-3 hover:bg-red-500/10 rounded-xl text-slate-500 hover:text-red-400 flex items-center gap-3 font-bold text-sm transition-all text-left">
              <LogOut className="w-4 h-4" /> Deconectare
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 p-12 max-w-[1400px]">
        <div className="mb-12">
          <h1 className="text-4xl font-black text-slate-900 dark:text-white uppercase tracking-tight mb-2 tracking-tighter">Parametri Granulari LLM</h1>
          <p className="text-slate-500 font-medium italic mb-8">Ajustează comportamentul fiecărui specialist pentru performanță maximă.</p>

          <div className="flex flex-wrap gap-4 p-1.5 bg-slate-100 dark:bg-white/5 rounded-2xl w-fit border border-slate-200 dark:border-white/5">
            <button 
              type="button"
              onClick={() => {
                const next = {...config, active_llm_engine: 'ollama'};
                setConfig(next);
                api.post('/system/llm/config', next).then(() => fetchData());
              }}
              className={`px-8 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                config.active_llm_engine === 'ollama' 
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              🛠️ Motor Ollama (Versatilitate)
            </button>
            <button 
              type="button"
              onClick={() => {
                const next = {...config, active_llm_engine: 'vllm'};
                setConfig(next);
                api.post('/system/llm/config', next).then(() => fetchData());
              }}
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
              onClick={async () => {
                const next = {
                  ...config, 
                  active_llm_engine: 'lmstudio',
                  specialist_processing: config.active_model,
                  specialist_tabular: config.active_model,
                  specialist_narrative: config.active_model
                };
                setConfig(next);
                await api.post('/system/llm/config', next);
                fetchData();
              }}
              className={`px-8 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                config.active_llm_engine === 'lmstudio' 
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20' 
                : 'text-slate-500 dark:text-slate-400 hover:bg-black/5 dark:hover:bg-white/5'
              }`}
            >
              🔮 Motor LM Studio (Local / Remote)
            </button>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-8">
          {/* PANOU CONFIGURARE LM STUDIO (LOCAL SAU STATIE REMOTE) */}
          {config.active_llm_engine === 'lmstudio' && (
            <div className="p-8 bg-purple-500/5 border border-purple-500/20 rounded-3xl space-y-6 shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
                    <Server className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">
                      Configurare Server LM Studio (Local sau Stație Remote)
                    </h2>
                    <p className="text-[11px] text-slate-500 font-medium">
                      Conectează DocAI la LM Studio rulat pe PC-ul local sau pe o stație dedicată din rețeaua locală / VPN.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testStatus?.testing}
                  className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {testStatus?.testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                  Testează Conexiunea
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                    <Globe className="w-3.5 h-3.5" /> Adresă Server (URL / IP:Port / v1)
                  </label>
                  <input
                    type="text"
                    value={config.lmstudio_url}
                    onChange={(e) => setConfig({...config, lmstudio_url: e.target.value})}
                    placeholder="ex: http://host.docker.internal:1234/v1 sau http://192.168.1.100:1234/v1"
                    className="w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-mono font-bold text-slate-900 dark:text-white outline-none focus:border-purple-500 transition-all shadow-sm"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    Pentru LM Studio pe mașina locală folosește <code className="text-purple-400">http://host.docker.internal:1234/v1</code>. Pentru alt PC din rețea folosește IP-ul său: <code className="text-purple-400">http://192.168.x.x:1234/v1</code>.
                  </span>
                </div>

                <div>
                  <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">
                    API Key (Opțional)
                  </label>
                  <input
                    type="password"
                    value={config.lmstudio_api_key}
                    onChange={(e) => setConfig({...config, lmstudio_api_key: e.target.value})}
                    placeholder="Lăsați gol dacă nu e setat token"
                    className="w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-mono text-slate-900 dark:text-white outline-none focus:border-purple-500 transition-all shadow-sm"
                  />
                </div>
              </div>

              {testStatus && (
                <div className={`p-4 rounded-xl text-xs font-bold flex items-center gap-3 ${
                  testStatus.success 
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' 
                  : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                }`}>
                  {testStatus.success ? <CheckCircle2 className="w-5 h-5 flex-shrink-0" /> : <XCircle className="w-5 h-5 flex-shrink-0" />}
                  <span>{testStatus.message}</span>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* PANOU MOTOR CHAT PRINCIPAL */}
            <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl space-y-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">
                    Motor Chat Principal ({config.active_llm_engine.toUpperCase()})
                  </h2>
                  <p className="text-[10px] text-slate-500 font-medium">
                    Agent ReAct, investigație forensic și dialog interactiv
                  </p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Model Desemnat</label>
                  {config.active_llm_engine === 'vllm' ? (
                    <input 
                      type="text"
                      value={config.active_model}
                      onChange={(e) => handleActiveModelChange(e.target.value)}
                      placeholder="ex: casperhansen/deepseek-r1-distill-qwen-14b-awq"
                      className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
                    />
                  ) : (
                    <div className="space-y-2">
                      <select 
                        value={config.active_model}
                        onChange={(e) => handleActiveModelChange(e.target.value)}
                        className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
                      >
                        {!availableModels.some(m => ((m.name || m.model) === config.active_model)) && config.active_model && (
                          <option value={config.active_model}>{config.active_model} (Selectat / Manual)</option>
                        )}
                        {availableModels.map((m: any) => (
                          <option key={m.name || m.model} value={m.name || m.model}>{m.name || m.model}</option>
                        ))}
                      </select>
                      {config.active_llm_engine === 'lmstudio' && (
                        <input
                          type="text"
                          value={config.active_model}
                          onChange={(e) => handleActiveModelChange(e.target.value)}
                          placeholder="Sau introdu manual identificatorul modelului din LM Studio"
                          className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-[11px] font-mono text-slate-700 dark:text-slate-300 outline-none focus:border-purple-500 transition-all"
                        />
                      )}
                    </div>
                  )}
                </div>

                {config.active_llm_engine !== 'lmstudio' ? (
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
                        <option value="65536">64k tokens</option>
                      </select>
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Temperatură ({config.chat_temp})</label>
                    <input 
                      type="range" min="0" max="1" step="0.1" 
                      value={config.chat_temp}
                      onChange={(e) => setConfig({...config, chat_temp: parseFloat(e.target.value)})}
                      className="w-full accent-purple-600 dark:accent-purple-500 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none"
                    />
                    <p className="text-[10px] text-slate-400 mt-2 italic">
                      * Fereastra de context RAM și limitele de tokeni sunt setate direct în interfața LM Studio la încărcarea modelului.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* PANOU EXPERT PROCESARE (DOCUMENTE, TABELE, TOC, SINTEZA) */}
            {config.active_llm_engine !== 'lmstudio' ? (
              <div className="p-8 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-3xl space-y-6 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">
                      Expert Procesare Unificat
                    </h2>
                    <p className="text-[10px] text-slate-500 font-medium">
                      Ingestie documente, tabele, cuprins forensic (TOC) și sinteză
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Model Desemnat</label>
                    <select 
                      value={config.specialist_processing}
                      onChange={(e) => setConfig({...config, specialist_processing: e.target.value})}
                      className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-emerald-500 transition-all"
                    >
                      {!availableModels.some(m => ((m.name || m.model) === config.specialist_processing)) && config.specialist_processing && (
                        <option value={config.specialist_processing}>{config.specialist_processing} (Selectat / Manual)</option>
                      )}
                      {availableModels.map((m: any) => (
                        <option key={m.name || m.model} value={m.name || m.model}>{m.name || m.model}</option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Temperatură ({config.processing_temp})</label>
                      <input 
                        type="range" min="0" max="1" step="0.1" 
                        value={config.processing_temp}
                        onChange={(e) => setConfig({...config, processing_temp: parseFloat(e.target.value)})}
                        className="w-full accent-emerald-600 dark:accent-emerald-500 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none"
                      />
                    </div>
                    <div>
                      <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">Context RAM</label>
                      <select 
                        value={config.processing_ctx}
                        onChange={(e) => setConfig({...config, processing_ctx: parseInt(e.target.value)})}
                        className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-2 text-[10px] font-bold text-slate-900 dark:text-white outline-none focus:border-emerald-500 transition-all"
                      >
                        <option value="8192">8k tokens</option>
                        <option value="16384">16k tokens</option>
                        <option value="32768">32k tokens</option>
                        <option value="65536">64k tokens</option>
                        <option value="131072">128k tokens</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-8 bg-purple-500/10 border border-purple-500/20 rounded-3xl flex flex-col justify-center space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-2xl bg-purple-500/20 text-purple-400 flex-shrink-0">
                    <Brain className="w-6 h-6" />
                  </div>
                  <h4 className="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">
                    Model Unic LM Studio Activ
                  </h4>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  În modul LM Studio, modelul încărcat ({config.active_model ? <code className="text-purple-400 font-bold">{config.active_model}</code> : 'detectat pe server'}) este alocat automat atât pentru investigația Chat (Agentic Investigator), cât și pentru procesarea documentelor (OCR, tabele, TOC, sinteză).
                </p>
                <p className="text-[10px] text-purple-400/80 font-medium">
                  Fereastra de context RAM și parametrii de cuantizare sunt gestionați direct în instanța LM Studio.
                </p>
              </div>
            )}
          </div>

          {/* CONFIGURARE NEURAL RERANKER (CROSS-ENCODER) */}
          <div className="p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-3xl space-y-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">
                    Neural Reranker (Cross-Encoder)
                  </h2>
                  <p className="text-[10px] text-slate-500 font-medium">
                    Filtrare semantică de înaltă precizie pentru probe criminalistice și sinteză
                  </p>
                </div>
              </div>
              <span className={`self-start sm:self-auto px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
                config.reranker_device === 'cuda' 
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' 
                  : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
              }`}>
                {config.reranker_device === 'cuda' ? '⚡ GPU (CUDA)' : '🛡️ CPU (Zero VRAM)'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">
                  Dispozitiv de Execuție (Hardware Target)
                </label>
                <select 
                  value={config.reranker_device || 'cpu'}
                  onChange={(e) => setConfig({...config, reranker_device: e.target.value})}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all"
                >
                  <option value="cpu">CPU (Recomandat - 0 MB VRAM, memorie liberă pentru LLM)</option>
                  <option value="cuda">CUDA / GPU (Latență minimă ~200ms, alocă ~1.1 GB VRAM)</option>
                </select>
                <p className="text-[10px] text-slate-400 mt-1.5">
                  {config.reranker_device === 'cuda' 
                    ? '⚠️ Asigură-te că modelul LLM lasă cel puțin 1.5 GB VRAM liberi pe RTX 4060.' 
                    : '✅ Execuția pe CPU permite LLM-ului să folosească întreaga memorie video fără coliziuni.'}
                </p>
              </div>

              <div>
                <label className="text-[9px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-2 block">
                  Model Neural Cross-Encoder
                </label>
                <input 
                  type="text"
                  list="reranker-models"
                  value={config.reranker_model || 'BAAI/bge-reranker-v2-m3'}
                  onChange={(e) => setConfig({...config, reranker_model: e.target.value})}
                  placeholder="ex: BAAI/bge-reranker-v2-m3"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all font-mono"
                />
                <datalist id="reranker-models">
                  <option value="BAAI/bge-reranker-v2-m3">BAAI/bge-reranker-v2-m3 (Recomandat - Multilingv & Criminalistic)</option>
                  <option value="BAAI/bge-reranker-large">BAAI/bge-reranker-large (Densitate mare)</option>
                  <option value="BAAI/bge-reranker-base">BAAI/bge-reranker-base (Rapid)</option>
                </datalist>
                <p className="text-[10px] text-slate-400 mt-1.5">
                  Selectează un model din listă sau specifică orice cale Hugging Face validă.
                </p>
              </div>
            </div>
          </div>

          {/* DESCARCARE & IMPORT MODELE (OLLAMA / HUGGINGFACE / OFFLINE) */}
          {config.active_llm_engine === 'ollama' && (
            <div className="p-8 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-3xl space-y-6">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/5 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-indigo-500/10 text-indigo-500 rounded-xl">
                    <Download className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-wider">
                      Adăugare & Import Modele (Ollama / Hugging Face)
                    </h3>
                    <p className="text-xs text-slate-500 font-medium">
                      Descarcă direct din registre online sau importă fișiere GGUF și arhive locale cu auto-dezarhivare.
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 1. PULL ONLINE */}
                <div className="p-5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-2xl space-y-4">
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-blue-500" />
                    <h4 className="text-xs font-black text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                      Descarcă din Registru Online
                    </h4>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Introduceți tag-ul din biblioteca Ollama (ex: <code className="text-indigo-500 font-bold">qwen2.5:14b</code>, <code className="text-indigo-500 font-bold">llama3.2:3b</code>) sau un model Hugging Face (ex: <code className="text-indigo-500 font-bold">hf.co/bartowski/Qwen2.5-7B-Instruct-GGUF:Q4_K_M</code>).
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={pullModelName}
                      onChange={(e) => setPullModelName(e.target.value)}
                      placeholder="ex: qwen2.5:14b sau hf.co/..."
                      disabled={isPulling}
                      className="flex-1 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-xl px-3.5 py-2.5 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all font-mono"
                    />
                    <button
                      type="button"
                      onClick={handlePullModel}
                      disabled={isPulling || !pullModelName.trim()}
                      className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-black uppercase tracking-wider transition-all disabled:opacity-50 flex items-center gap-2"
                    >
                      {isPulling ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                      Descarcă
                    </button>
                  </div>

                  {pullProgress && (pullProgress.active || pullProgress.status === 'completed' || pullProgress.status === 'error') && (
                    <div className="p-3.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-xl space-y-2">
                      <div className="flex items-center justify-between text-xs font-bold">
                        <span className="text-slate-700 dark:text-slate-300 truncate max-w-[200px]">{pullProgress.model || pullModelName}</span>
                        <span className="text-indigo-500 font-mono text-[11px]">{pullProgress.percent || 0}%</span>
                      </div>
                      <div className="w-full bg-slate-200 dark:bg-white/10 h-1.5 rounded-full overflow-hidden">
                        <div 
                          className="bg-indigo-500 h-full transition-all duration-300 rounded-full" 
                          style={{ width: `${pullProgress.percent || 0}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-slate-400 truncate">{pullProgress.detail}</p>
                    </div>
                  )}
                </div>

                {/* 2. IMPORT OFFLINE / GGUF / UNZIP */}
                <div className="p-5 bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-2xl space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Box className="w-4 h-4 text-amber-500" />
                      <h4 className="text-xs font-black text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                        Fișiere Locale (models/import/)
                      </h4>
                    </div>
                    <button
                      type="button"
                      onClick={fetchData}
                      className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400 transition-all"
                      title="Reîmprospătează lista"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <p className="text-[11px] text-slate-500">
                    Plasează fișiere <code className="text-amber-500 font-bold">.gguf</code> sau arhive <code className="text-amber-500 font-bold">.zip / .tar.gz</code> direct în folderul <code className="font-mono text-slate-400">V2/models/import/</code>. Dezarhivarea și înregistrarea se fac automat.
                  </p>

                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {importModels.length === 0 ? (
                      <div className="p-4 border border-dashed border-slate-200 dark:border-white/10 rounded-xl text-center">
                        <p className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                          Niciun fișier detectat în models/import/
                        </p>
                      </div>
                    ) : (
                      importModels.map((item: any) => {
                        const itName = typeof item === 'string' ? item : item.name;
                        const itType = typeof item === 'object' ? item.type : 'folder';
                        const itSize = typeof item === 'object' ? item.size_mb : null;
                        const importingThis = isImporting === itName;

                        return (
                          <div key={itName} className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-white/5 rounded-xl">
                            <div className="flex items-center gap-2.5 min-w-0">
                              <span className={`px-1.5 py-0.5 text-[9px] font-black uppercase rounded ${
                                itType === 'gguf' ? 'bg-emerald-500/10 text-emerald-500' :
                                itType === 'archive' ? 'bg-purple-500/10 text-purple-500' :
                                'bg-amber-500/10 text-amber-500'
                              }`}>
                                {itType}
                              </span>
                              <div className="truncate">
                                <p className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">{itName}</p>
                                {itSize && <p className="text-[9px] text-slate-400 font-mono">{itSize} MB</p>}
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleImport(itName)}
                              disabled={importingThis || isImporting !== null}
                              className="px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500 hover:text-white text-amber-600 dark:text-amber-500 rounded-lg text-xs font-bold transition-all disabled:opacity-50 flex items-center gap-1.5 flex-shrink-0"
                            >
                              {importingThis ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
                              Importă
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>

                  {importProgress && (importProgress.active || importProgress.status === 'completed' || importProgress.status === 'error') && (
                    <div className="p-3 bg-amber-500/5 border border-amber-500/10 rounded-xl">
                      <p className="text-[10px] text-amber-600 dark:text-amber-400 font-bold">{importProgress.detail}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* LIMITA SIGURANTA (SAFETY GUARDRAIL) */}
          <div className="p-6 bg-blue-500/5 border border-blue-500/10 rounded-3xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex gap-4 items-center">
              <div className="p-3 rounded-2xl bg-blue-500/10 text-blue-500 flex-shrink-0">
                <Shield className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">Limită de Siguranță Context (Safety Guardrail)</h3>
                <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                  Controlează volumul maxim de date brute transmise în raționament pentru a preveni epuizarea VRAM și blocajele de memorie.
                </p>
              </div>
            </div>
            <div className="w-full sm:w-56 flex-shrink-0">
              <select 
                value={config.safety_limit}
                onChange={(e) => setConfig({...config, safety_limit: parseInt(e.target.value)})}
                className="w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 dark:text-white outline-none focus:border-indigo-500 transition-all shadow-sm"
              >
                <option value="10000">10k (Rapid)</option>
                <option value="20000">20k (Standard)</option>
                <option value="50000">50k (Complex)</option>
                <option value="100000">100k (Audit Full)</option>
              </select>
            </div>
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
