'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Brain, ChevronLeft, Loader2, Save, 
  Settings2, Info, AlertTriangle, Zap, Database, Code, FileText, Activity
} from 'lucide-react';

export default function LLMConfig() {
  const router = useRouter();
  const [config, setConfig] = useState({ 
    active_model: '', chat_temp: 0.7, chat_ctx: 16384,
    specialist_tabular: '', tabular_temp: 0.0, tabular_ctx: 16384,
    specialist_narrative: '', narrative_temp: 0.1, narrative_ctx: 32768
  });
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const token = Cookies.get('token');

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    const fetchData = async () => {
      try {
        const [confRes, modelsRes] = await Promise.all([
          api.get('/system/llm/config'),
          api.get('/system/models/available')
        ]);
        setConfig(confRes.data);
        setAvailableModels(modelsRes.data);
      } catch (err) { console.error(err); }
      finally { setIsLoading(false); }
    };
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

  if (isLoading) return <div className="min-h-screen bg-slate-950 flex items-center justify-center"><Loader2 className="w-12 h-12 text-indigo-500 animate-spin" /></div>;

  const ConfigCard = ({ title, icon: Icon, color, modelKey, tempKey, ctxKey }: any) => (
    <div className="p-8 bg-slate-900/50 border border-white/5 rounded-3xl space-y-6">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg bg-${color}-500/10`}><Icon className={`w-5 h-5 text-${color}-400`} /></div>
        <h2 className="text-sm font-black text-white uppercase tracking-tight">{title}</h2>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Model</label>
          <select 
            value={(config as any)[modelKey]}
            onChange={(e) => setConfig({...config, [modelKey]: e.target.value})}
            className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-3 text-xs font-bold text-white outline-none focus:border-indigo-500"
          >
            {availableModels.map((m: any) => <option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Temperatură ({(config as any)[tempKey]})</label>
            <input 
              type="range" min="0" max="1" step="0.1" 
              value={(config as any)[tempKey]}
              onChange={(e) => setConfig({...config, [tempKey]: parseFloat(e.target.value)})}
              className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg appearance-none"
            />
          </div>
          <div>
            <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-2 block">Context</label>
            <select 
              value={(config as any)[ctxKey]}
              onChange={(e) => setConfig({...config, [ctxKey]: parseInt(e.target.value)})}
              className="w-full bg-slate-950 border border-white/10 rounded-xl px-3 py-2 text-[10px] font-bold text-white outline-none focus:border-indigo-500"
            >
              <option value="4096">4k</option><option value="8192">8k</option><option value="16384">16k</option><option value="32768">32k</option><option value="65536">64k</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans flex text-left">
      <div className="w-72 bg-slate-900 border-r border-white/5 p-6 flex flex-col sticky top-0 h-screen">
        <button onClick={() => router.push('/dashboard')} className="flex items-center gap-3 mb-12 px-2 hover:opacity-80 transition-opacity">
          <ChevronLeft className="w-5 h-5 text-slate-400" />
          <span className="text-xl font-black tracking-tighter text-white uppercase">DocAI Admin</span>
        </button>
        <div className="px-4 py-3 bg-indigo-600/10 border border-indigo-600/20 rounded-xl text-indigo-400 flex items-center gap-3 font-bold text-sm">
          <Brain className="w-4 h-4" /> Configurație LLM
        </div>
      </div>

      <div className="flex-1 p-12 max-w-[1400px]">
        <div className="mb-12">
          <h1 className="text-4xl font-black text-white uppercase tracking-tight mb-2 tracking-tighter">Parametri Granulari LLM</h1>
          <p className="text-slate-500 font-medium italic">Ajustează comportamentul fiecărui specialist pentru performanță maximă.</p>
        </div>

        <form onSubmit={handleSave} className="space-y-8">
          <div className="grid grid-cols-3 gap-6">
            <ConfigCard title="Motor Chat" icon={Zap} color="blue" modelKey="active_model" tempKey="chat_temp" ctxKey="chat_ctx" />
            <ConfigCard title="Specialist Tabular" icon={Code} color="indigo" modelKey="specialist_tabular" tempKey="tabular_temp" ctxKey="tabular_ctx" />
            <ConfigCard title="Specialist Narrativ" icon={FileText} color="fuchsia" modelKey="specialist_narrative" tempKey="narrative_temp" ctxKey="narrative_ctx" />
          </div>

          <div className="p-6 bg-blue-500/5 border border-blue-500/10 rounded-2xl flex gap-4 items-center">
            <Info className="w-6 h-6 text-blue-400 flex-shrink-0" />
            <p className="text-xs text-slate-400 font-medium leading-relaxed">
              Setările de <span className="text-white font-bold">Context</span> mari (32k+) îmbunătățesc analiza documentelor lungi, dar necesită mai mult VRAM. Specialistul tabular (Qwen) funcționează cel mai bine cu <span className="text-white font-bold">Temperatură 0</span>.
            </p>
          </div>

          <button type="submit" disabled={isSaving} className="w-full py-5 bg-indigo-600 hover:bg-indigo-500 rounded-2xl text-sm font-black uppercase tracking-widest transition-all shadow-xl flex items-center justify-center gap-3">
            {isSaving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />} Salvează Toți Parametrii
          </button>
        </form>
      </div>
    </div>
  );
}
