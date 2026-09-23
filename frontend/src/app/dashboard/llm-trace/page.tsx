'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../../lib/api';
import { 
  Brain, Terminal, Cpu, Clock, RefreshCw, Search, ArrowLeft, 
  Copy, Check, Play, Pause, AlertCircle, Code, Layers, FileText, Sparkles, Filter, ChevronRight
} from 'lucide-react';
import { useTheme } from '../../../lib/ThemeProvider';

export default function LLMTracePage() {
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  
  const [traces, setTraces] = useState<any[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'prompt' | 'thinking' | 'tools' | 'content'>('prompt');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const fetchTraces = async () => {
    try {
      const res = await api.get('/system/logs/llm-trace?limit=100');
      const items = res.data.traces || [];
      setTraces(items);
      setSelectedTrace(prev => {
        if (!prev) return items[0] || null;
        const matched = items.find((x: any) => x.id === prev.id);
        return matched || prev || items[0] || null;
      });
    } catch (err) {
      console.error("Fetch LLM traces error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTraces();
    if (!autoRefresh) return;
    const interval = setInterval(fetchTraces, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleCopy = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const filteredTraces = traces.filter(t => {
    if (!searchTerm.trim()) return true;
    const s = searchTerm.toLowerCase();
    return (
      (t.model || '').toLowerCase().includes(s) ||
      (t.prompt_text || '').toLowerCase().includes(s) ||
      (t.content || '').toLowerCase().includes(s) ||
      (t.reasoning || '').toLowerCase().includes(s)
    );
  });

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {/* HEADER BAR */}
      <header className="bg-slate-950 border-b border-slate-800 px-8 py-4 flex items-center justify-between shadow-xl">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push('/dashboard')}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors text-slate-300 flex items-center gap-2 text-xs font-bold"
          >
            <ArrowLeft className="w-4 h-4" /> Înapoi la Dashboard
          </button>
          <div>
            <h1 className="text-xl font-black text-white uppercase tracking-tight italic flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" /> LLM Execution Inspector & Live Traces
            </h1>
            <p className="text-xs text-slate-400 font-medium">
              Monitorizare în timp real: prompt-uri integrale pe bucăți, raționament [THINKING], unelte și răspunsuri brute.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider flex items-center gap-2 border transition-all ${
              autoRefresh 
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 shadow-sm' 
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
            }`}
          >
            {autoRefresh ? (
              <>
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <Pause className="w-3.5 h-3.5" /> Streaming Activ (3s)
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5" /> Reia Stream
              </>
            )}
          </button>
          <button
            onClick={fetchTraces}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors text-slate-300"
            title="Reîmprospătează acum"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR: TRACE LIST */}
        <div className="w-[420px] bg-slate-950/60 border-r border-slate-800 flex flex-col">
          {/* SEARCH BAR */}
          <div className="p-4 border-b border-slate-800">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                placeholder="Caută după model, prompt, text..."
                className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
            <div className="mt-2 text-[10px] text-slate-400 flex justify-between font-mono">
              <span>Afișat: {filteredTraces.length} / {traces.length} apeluri</span>
              <span>Buffer Redis: 100 max</span>
            </div>
          </div>

          {/* LIST ITEMS */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
            {isLoading ? (
              <div className="text-center py-12 text-slate-500 text-xs animate-pulse">Se încarcă logurile LLM...</div>
            ) : filteredTraces.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-xs">Nicio execuție LLM găsită.</div>
            ) : (
              filteredTraces.map((trace, idx) => {
                const isSelected = selectedTrace && selectedTrace.id === trace.id;
                const hasReasoning = Boolean(trace.reasoning && trace.reasoning.trim());
                const toolCount = (trace.tool_calls || []).length;
                const dateStr = trace.timestamp ? new Date(trace.timestamp).toLocaleTimeString('ro-RO') : 'N/A';

                return (
                  <div
                    key={trace.id || idx}
                    onClick={() => setSelectedTrace(trace)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500/50 shadow-md ring-1 ring-indigo-500/30'
                        : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/60 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] font-mono font-bold">
                        {trace.model || 'unknown-model'}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">{dateStr}</span>
                    </div>

                    <p className="text-xs text-slate-300 font-medium line-clamp-2 mb-2 italic">
                      "{trace.prompt_text ? trace.prompt_text.slice(0, 120) : 'Prompt...'}"
                    </p>

                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 border-t border-slate-800/60 pt-2">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" /> {trace.duration_ms || 0} ms
                      </span>

                      <div className="flex items-center gap-2">
                        {hasReasoning && (
                          <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                            <Brain className="w-3 h-3" /> Gândire
                          </span>
                        )}
                        {toolCount > 0 && (
                          <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center gap-1">
                            <Terminal className="w-3 h-3" /> {toolCount} Unelte
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT AREA: DETAILED INSPECTOR */}
        <div className="flex-1 flex flex-col bg-slate-900 overflow-hidden">
          {selectedTrace ? (
            <>
              {/* INSPECTOR HEADER & TABS */}
              <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="px-2.5 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-mono font-bold">
                    {selectedTrace.model}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Latență: <strong className="text-slate-200">{selectedTrace.duration_ms} ms</strong>
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Data: <strong className="text-slate-200">{new Date(selectedTrace.timestamp).toLocaleString('ro-RO')}</strong>
                  </span>
                </div>

                {/* TABS */}
                <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl">
                  <button
                    onClick={() => setActiveTab('prompt')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                      activeTab === 'prompt'
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" /> 1. Input / Calupuri Text
                  </button>

                  <button
                    onClick={() => setActiveTab('thinking')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                      activeTab === 'thinking'
                        ? 'bg-amber-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Brain className="w-3.5 h-3.5" /> 2. Raționament (Thinking)
                    {selectedTrace.reasoning && <div className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
                  </button>

                  <button
                    onClick={() => setActiveTab('tools')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                      activeTab === 'tools'
                        ? 'bg-cyan-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Terminal className="w-3.5 h-3.5" /> 3. Unelte ({(selectedTrace.tool_calls || []).length})
                  </button>

                  <button
                    onClick={() => setActiveTab('content')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                      activeTab === 'content'
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Code className="w-3.5 h-3.5" /> 4. Răspuns Brut Output
                  </button>
                </div>
              </div>

              {/* TAB CONTENT PANEL */}
              <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
                {/* TAB 1: INPUT PROMPT & CHUNKS */}
                {activeTab === 'prompt' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <span className="text-xs font-mono text-slate-400">
                        Dimensiune Prompt: <strong className="text-indigo-400">{(selectedTrace.prompt_text || '').length} caractere</strong> (~{Math.round((selectedTrace.prompt_text || '').length / 3.5)} tokeni)
                      </span>
                      <button
                        onClick={() => handleCopy(selectedTrace.prompt_text || '', 'prompt')}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-bold text-slate-300 flex items-center gap-1.5 transition-colors"
                      >
                        {copiedField === 'prompt' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedField === 'prompt' ? 'Copiat!' : 'Copiază Prompt Integrat'}
                      </button>
                    </div>

                    <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 font-mono text-xs text-slate-200 leading-relaxed whitespace-pre-wrap overflow-x-auto shadow-inner">
                      {selectedTrace.prompt_text || (
                        (selectedTrace.messages || []).map((m: any, i: number) => (
                          <div key={i} className="mb-4 pb-4 border-b border-slate-800/60">
                            <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 text-[10px] font-bold uppercase tracking-wider block w-fit mb-2">
                              {m.role || 'USER'}
                            </span>
                            <div>{m.content}</div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* TAB 2: THINKING / REASONING */}
                {activeTab === 'thinking' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <span className="text-xs font-mono text-slate-400 flex items-center gap-2">
                        <Brain className="w-4 h-4 text-amber-400" /> Procesul de Gândire Internă [THINKING]
                      </span>
                      {selectedTrace.reasoning && (
                        <button
                          onClick={() => handleCopy(selectedTrace.reasoning, 'thinking')}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-bold text-slate-300 flex items-center gap-1.5 transition-colors"
                        >
                          {copiedField === 'thinking' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copiedField === 'thinking' ? 'Copiat!' : 'Copiază Raționamentul'}
                        </button>
                      )}
                    </div>

                    {selectedTrace.reasoning ? (
                      <div className="bg-slate-950 border border-amber-500/20 rounded-2xl p-6 font-mono text-xs text-amber-200/90 leading-relaxed whitespace-pre-wrap shadow-inner border-l-4 border-l-amber-500">
                        {selectedTrace.reasoning}
                      </div>
                    ) : (
                      <div className="p-12 text-center text-slate-500 bg-slate-950/50 rounded-2xl border border-slate-800/50 text-xs">
                        Acest model nu a furnizat un bloc separat de gândire/reasoning pentru această interogare.
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 3: TOOL CALLS */}
                {activeTab === 'tools' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <span className="text-xs font-mono text-slate-400">
                        Unelte Apelate: <strong className="text-cyan-400">{(selectedTrace.tool_calls || []).length} unelte</strong>
                      </span>
                      {(selectedTrace.tool_calls || []).length > 0 && (
                        <button
                          onClick={() => handleCopy(JSON.stringify(selectedTrace.tool_calls, null, 2), 'tools')}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-bold text-slate-300 flex items-center gap-1.5 transition-colors"
                        >
                          {copiedField === 'tools' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copiedField === 'tools' ? 'Copiat!' : 'Copiază Uneltele (JSON)'}
                        </button>
                      )}
                    </div>

                    {(selectedTrace.tool_calls || []).length === 0 ? (
                      <div className="p-12 text-center text-slate-500 bg-slate-950/50 rounded-2xl border border-slate-800/50 text-xs">
                        Modelul nu a apelat nici o unealtă în acest pas.
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {selectedTrace.tool_calls.map((tc: any, i: number) => (
                          <div key={i} className="bg-slate-950 border border-cyan-500/20 rounded-2xl p-5 shadow-sm">
                            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-3">
                              <span className="px-3 py-1 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-mono font-bold flex items-center gap-2">
                                <Terminal className="w-3.5 h-3.5" /> {tc.name || tc.function?.name || 'tool'}
                              </span>
                              <span className="text-[10px] font-mono text-slate-500">Pas #{i + 1}</span>
                            </div>
                            <div className="font-mono text-xs text-cyan-200/90 whitespace-pre-wrap bg-slate-900/80 p-4 rounded-xl border border-slate-800">
                              {typeof tc.args === 'object' ? JSON.stringify(tc.args, null, 2) : (tc.args || tc.function?.arguments || '{}')}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 4: RAW CONTENT OUTPUT */}
                {activeTab === 'content' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between bg-slate-950 p-3 rounded-xl border border-slate-800">
                      <span className="text-xs font-mono text-slate-400">
                        Dimensiune Răspuns: <strong className="text-emerald-400">{(selectedTrace.content || '').length} caractere</strong> (~{Math.round((selectedTrace.content || '').length / 3.5)} tokeni)
                      </span>
                      <button
                        onClick={() => handleCopy(selectedTrace.content || '', 'content')}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-bold text-slate-300 flex items-center gap-1.5 transition-colors"
                      >
                        {copiedField === 'content' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedField === 'content' ? 'Copiat!' : 'Copiază Output Brut'}
                      </button>
                    </div>

                    <div className="bg-slate-950 border border-emerald-500/20 rounded-2xl p-6 font-mono text-xs text-emerald-300/90 leading-relaxed whitespace-pre-wrap shadow-inner border-l-4 border-l-emerald-500">
                      {selectedTrace.content || selectedTrace.raw?.content || 'Fără conținut generat.'}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-12">
              <Brain className="w-16 h-16 mb-4 text-slate-700 animate-pulse" />
              <p className="text-sm font-bold">Selectează un apel LLM din lista stângă pentru a-i inspecta datele brute.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
