'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Folder, FileText, Landmark, Database, History, 
  Clock, Building2, User, Loader2, Send, MessageSquare, 
  ChevronLeft, Trash2, ArrowRightCircle, X, AlertTriangle, ExternalLink, Search, ScrollText, RotateCcw, Brain, Copy, Upload,
  Crosshair, Route, Share2, RefreshCw, Info
} from 'lucide-react';

import dynamic from 'next/dynamic';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export default function CaseDetail() {
  const { id: caseId } = useParams();
  const router = useRouter();
  const graphRef = useRef<any>();
  const chatEndRef = useRef<HTMLDivElement>(null);
  
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [user, setUser] = useState<any>(null);
  const [entities, setEntities] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [activeModel, setActiveModel] = useState<string>('...');
  const [caseSummary, setCaseSummary] = useState<string>('');
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [showBriefing, setShowBriefing] = useState(false);
  const [evidencePreview, setEvidencePreview] = useState<{url: string, page: number, text: string} | null>(null);

  const [showGraph, setShowGraph] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [isGraphLoading, setIsGraphLoading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [highlightLinks, setHighlightLinks] = useState(new Set());
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [nodeColors, setNodeColors] = useState<Record<string, string>>({});
  const [nodeVals, setNodeVals] = useState<Record<string, number>>({});
  const [graphSearch, setGraphSearch] = useState('');
  const [pathSource, setPathSource] = useState('');
  const [pathTarget, setPathTarget] = useState('');
  const [cloneCui, setCloneCui] = useState('');

  const [messages, setMessages] = useState<any[]>([]);
  const [question, setQuestion] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  const token = Cookies.get('token');

  const fetchData = async () => {
    if (!token) return;
    try {
      const [cRes, eRes, dRes, uRes, mRes, sRes] = await Promise.all([
        api.get('/cases'),
        api.get(`/cases/${caseId}/entities`),
        api.get(`/cases/${caseId}/documents`),
        api.get('/auth/me'),
        api.get('/system/models/active'),
        api.get(`/cases/${caseId}/summary`)
      ]);
      const currentCase = cRes.data.find((c: any) => c.id === parseInt(caseId as string));
      if (!currentCase) { router.push('/cases'); return; }
      setCaseInfo(currentCase);
      setCaseSummary(sRes.data.summary || '');
      setUser(uRes.data);
      setEntities(eRes.data);
      setDocs(dRes.data);
      setActiveModel(mRes.data.active_model);
    } catch (err) { console.error("Error", err); }
  };

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    fetchData();
    api.get(`/cases/${caseId}/chat`).then(res => setMessages(res.data));
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [caseId]);

  useEffect(() => {
    if (showBriefing || showGraph) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
  }, [showBriefing, showGraph]);

  const handleGenerateSummary = async () => {
    setIsSummaryLoading(true);
    try {
      const res = await api.get(`/cases/${caseId}/summary`);
      setCaseSummary(res.data.summary);
      fetchData();
    } catch (err) { alert("Eroare sinteză."); }
    finally { setIsSummaryLoading(false); }
  };

  const handleClearChat = async () => {
    if (!confirm("Sigur dorești să ștergi tot istoricul de chat?")) return;
    try {
      await api.post(`/cases/${caseId}/chat/clear`);
      setMessages([]);
    } catch (err) { alert("Eroare."); }
  };

  const handleDeleteMessage = async (msgId: number) => {
    try {
      await api.post(`/cases/${caseId}/chat/${msgId}/delete`);
      setMessages(prev => prev.filter(m => m.id !== msgId));
    } catch (err) { alert("Eroare."); }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isChatLoading) return;
    const userMsg = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setQuestion('');
    setIsChatLoading(true);
    try {
      const res = await api.post(`/cases/${caseId}/chat`, { question: userMsg.content });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.answer, citations: res.data.citations }]);
    } catch (err) { setMessages(prev => [...prev, { role: 'assistant', content: 'Eroare.' }]); }
    finally { setIsChatLoading(false); }
  };

  const handleNodeClick = (node: any) => {
    if (!node) { setSelectedNode(null); setHighlightNodes(new Set()); setHighlightLinks(new Set()); return; }
    const newHighlightNodes = new Set();
    const newHighlightLinks = new Set();
    newHighlightNodes.add(node.id);
    graphData.links.forEach((link: any) => {
      if (link.source.id === node.id || link.target.id === node.id) {
        newHighlightLinks.add(link);
        newHighlightNodes.add(link.source.id);
        newHighlightNodes.add(link.target.id);
      }
    });
    setSelectedNode(node); setHighlightNodes(newHighlightNodes); setHighlightLinks(newHighlightLinks);
  };

  const handleFindLeader = async () => {
    setIsAnalyzing(true);
    try {
      const res = await api.get(`/cases/${caseId}/graph/analytics/leader`);
      const scores = res.data;
      const newVals: Record<string, number> = {};
      const newColors: Record<string, string> = {};
      Object.entries(scores).forEach(([id, score]) => {
        newVals[id] = Math.min(15, 5 + ((score as number) * 2));
        if ((score as number) > 1) newColors[id] = '#ef4444';
      });
      setNodeVals(newVals); setNodeColors(newColors);
      setGraphData(prev => ({ ...prev }));
    } finally { setIsAnalyzing(false); }
  };

  const handleDetectCartel = async () => {
    setIsAnalyzing(true);
    try {
      const res = await api.get(`/cases/${caseId}/graph/analytics/cartel`);
      const communities = res.data;
      const newColors: Record<string, string> = {};
      const palette = ['#f43f5e', '#a855f7', '#3b82f6', '#14b8a6', '#f59e0b'];
      Object.entries(communities).forEach(([id, commId]) => {
        newColors[id] = palette[(commId as number) % palette.length];
      });
      setNodeColors(newColors);
      setGraphData(prev => ({ ...prev }));
    } finally { setIsAnalyzing(false); }
  };

  const handleShortestPath = async () => {
    if (!pathSource || !pathTarget) return alert("Sursă/Destinație?");
    setIsAnalyzing(true);
    try {
      const res = await api.get(`/cases/${caseId}/graph/analytics/path?source_name=${pathSource}&target_name=${pathTarget}`);
      if (res.data.nodes.length === 0) return alert("Nu există traseu.");
      setHighlightNodes(new Set(res.data.nodes));
      setGraphData(prev => ({ ...prev }));
    } finally { setIsAnalyzing(false); }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col font-sans">
      {/* HEADER */}
      <div className="bg-slate-900/50 border-b border-white/5 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-[1800px] mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button onClick={() => router.push('/cases')} className="p-2.5 hover:bg-white/5 rounded-xl border border-transparent hover:border-white/10 group transition-all">
              <ChevronLeft className="w-5 h-5 text-slate-400 group-hover:text-white" />
            </button>
            <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-900/40"><Shield className="w-5 h-5 text-white" /></div>
              <div><h1 title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-sm font-black text-white uppercase leading-none italic tracking-tighter">DocAI v0.1 ALPHA</h1></div>
            </div>
            <div className="h-10 w-[1px] bg-white/10" />
            <h1 className="text-xl font-black text-white uppercase truncate max-w-md">{caseInfo?.name || 'Încărcare...'}</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/5 border border-blue-500/10 rounded-lg mr-2">
              <Brain className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">{activeModel}</span>
            </div>
            <button onClick={() => {
                const url = `${process.env.NEXT_PUBLIC_API_URL}/uploads/Audit_Report_${caseId}.pdf`;
                window.open(url, '_blank');
            }} className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl text-rose-400 text-sm font-bold transition-all">
              <ScrollText className="w-4 h-4" /> Raport Audit
            </button>
            <button onClick={() => { setIsGraphLoading(true); api.get(`/cases/${caseId}/graph`).then(res => { setGraphData(res.data); setShowGraph(true); setIsGraphLoading(false); }); }} className="flex items-center gap-2 px-4 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 rounded-xl text-indigo-400 text-sm font-bold transition-all">
              <Database className="w-4 h-4" /> Harta Relații
            </button>
            <button onClick={() => setShowBriefing(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl text-blue-400 text-sm font-bold transition-all">
              <Brain className="w-4 h-4" /> Briefing
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* SIDEBAR */}
        <div className="w-[450px] border-r border-white/5 flex flex-col bg-slate-900/30 overflow-y-auto p-6">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-800 hover:border-blue-500/50 rounded-2xl cursor-pointer transition-all bg-slate-900/50 hover:bg-blue-500/5 group mb-8">
              <Upload className="w-8 h-8 text-slate-500 group-hover:text-blue-400 mb-2" />
              <p className="text-sm font-bold text-slate-400 group-hover:text-slate-200">Încarcă probe noi</p>
              <input type="file" className="hidden" multiple onChange={async (e) => {
                if (!e.target.files) return;
                const fd = new FormData();
                fd.append('case_id', caseId as string);
                Array.from(e.target.files).forEach(f => fd.append('files', f));
                try { await api.post('/upload', fd); fetchData(); } catch (err) { alert("Eroare."); }
              }} />
            </label>
            <h3 className="text-[11px] font-black text-slate-500 uppercase mb-4 tracking-widest">Documente în Dosar</h3>
            {docs.map(doc => (
              <div key={doc.id} className="p-4 bg-slate-900/50 border border-white/5 rounded-xl mb-2 group">
                <div className="flex justify-between items-start mb-2">
                  <p className="text-xs font-bold truncate pr-4 text-slate-200">{doc.filename}</p>
                  <div className="flex items-center gap-2">
                    {doc.status === 'PARTIAL_COMPLETED' && (
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500 animate-pulse" title="Procesare parțială (unele segmente au eșuat)" />
                    )}
                    <span className={`text-[8px] font-black px-1.5 py-0.5 rounded ${
                      doc.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-500' : 
                      doc.status === 'PARTIAL_COMPLETED' ? 'bg-amber-500/10 text-amber-500' :
                      'bg-blue-500/10 text-blue-500'
                    }`}>{doc.status}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/uploads/${doc.filename}`, '_blank')} className="text-[9px] font-black text-blue-400 uppercase flex items-center gap-1 hover:text-blue-300 transition-colors">
                    <ExternalLink className="w-2.5 h-2.5" /> Deschide
                  </button>
                  <button onClick={async () => { if(confirm("Ștergi documentul?")) { await api.post(`/cases/documents/${doc.id}/delete`); fetchData(); } }} className="text-[9px] font-black text-slate-600 uppercase flex items-center gap-1 hover:text-red-400 transition-colors">
                    <Trash2 className="w-2.5 h-2.5" /> Șterge
                  </button>
                </div>
                {doc.ai_summary && <p className="mt-2 text-[10px] text-slate-400 italic leading-relaxed">{doc.ai_summary}</p>}
              </div>
            ))}
        </div>

        {/* CHAT AREA */}
        <div className="flex-1 flex flex-col bg-slate-950">
          <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} group/msg relative`}>
                <div className={`max-w-[85%] rounded-3xl p-5 ${msg.role === 'user' ? 'bg-blue-600 text-white shadow-xl shadow-blue-900/20' : 'bg-slate-900 border border-white/5 shadow-xl'} relative`}>
                  <button onClick={async () => {
                    try {
                      await api.post(`/cases/${caseId}/chat/${msg.id}/delete`);
                      setMessages(prev => prev.filter(m => m.id !== msg.id));
                    } catch (err) { alert("Eroare."); }
                  }} className="absolute -top-2 -right-2 p-1.5 bg-slate-800 border border-white/10 rounded-full opacity-0 group-hover/msg:opacity-100 transition-opacity hover:text-red-400 shadow-xl"><Trash2 className="w-3 h-3" /></button>
                  <p className="text-[10px] font-black uppercase tracking-widest opacity-50 mb-2">{msg.role === 'user' ? (user?.username || 'Investigator') : activeModel}</p>
                  <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/5 space-y-2">
                      {msg.citations.map((cite: any, i: number) => (
                        <div key={i} onClick={() => { setEvidencePreview({ url: `${process.env.NEXT_PUBLIC_API_URL}/uploads/${cite.source || docs[0]?.filename}`, page: cite.page || 1, text: typeof cite === 'string' ? cite : (cite.text || '') }); }} className="p-2.5 bg-blue-500/5 border-l-2 border-blue-500 rounded-r-lg text-[11px] text-slate-400 italic cursor-pointer hover:bg-blue-500/10 transition-all flex justify-between group/cite">
                          <span className="line-clamp-2">"{typeof cite === 'string' ? cite : (cite.text || JSON.stringify(cite))}"</span>
                          <div className="flex gap-1 opacity-0 group-hover/cite:opacity-100"><ExternalLink className="w-3 h-3" /></div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="p-8 bg-slate-950 border-t border-white/5">
            <form onSubmit={handleAsk} className="relative group">
              <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Interoghează dosarul..." className="w-full bg-slate-900 border border-white/10 rounded-2xl px-6 py-5 text-sm font-medium focus:outline-none focus:border-blue-500/50 transition-all" />
              <button type="submit" disabled={isChatLoading} className="absolute right-3 top-3 bottom-3 px-6 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-black uppercase transition-all flex items-center gap-2">
                {isChatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Interoghează
              </button>
            </form>
            <div className="mt-4 flex justify-between items-center px-2">
              <button onClick={async () => {
                if (!confirm("Sigur dorești să ștergi tot istoricul de chat?")) return;
                try {
                  await api.post(`/cases/${caseId}/chat/clear`);
                  setMessages([]);
                } catch (err) { alert("Eroare."); }
              }} className="text-[10px] font-black text-slate-600 hover:text-red-400 uppercase flex items-center gap-1.5 transition-colors"><RotateCcw className="w-3 h-3" /> Golește Istoric</button>
              <span title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-[10px] font-black text-slate-700 uppercase tracking-widest italic">DocAI v0.1 ALPHA • Pro Mode</span>
            </div>
          </div>
        </div>

        {/* PREVIEW PANEL */}
        {evidencePreview && (
          <div className="w-[600px] border-l border-white/5 bg-slate-900/50 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="p-4 border-b border-white/5 flex items-center justify-between bg-slate-900">
              <div className="flex items-center gap-2"><FileText className="w-4 h-4 text-blue-400" /><span className="text-[11px] font-black text-slate-300 uppercase tracking-widest">Probă Materială</span></div>
              <button onClick={() => setEvidencePreview(null)} className="p-1 hover:bg-white/10 rounded-md text-slate-500"><X className="w-5 h-5" /></button>
            </div>
            <div className="flex-1 bg-slate-800 relative">
              <iframe key={`${evidencePreview.url}`} src={`${evidencePreview.url}#page=${evidencePreview.page}`} className="w-full h-full border-none" />
            </div>
          </div>
        )}
      </div>

      {/* GRAPH MODAL */}
      {showGraph && (
        <div className="fixed inset-0 z-[100] bg-slate-950/95 backdrop-blur-md flex flex-col animate-in fade-in duration-300">
          <div className="p-4 border-b border-white/10 flex justify-between items-center bg-slate-900">
            <h2 className="text-white font-bold uppercase tracking-tight text-sm flex items-center gap-2">
              <Database className="w-4 h-4 text-indigo-400" /> Analiză Suveică
            </h2>
            <div className="flex items-center gap-3">
              <div className="relative group">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
                <input value={graphSearch} onChange={e => setGraphSearch(e.target.value)} placeholder="Caută în hartă..." className="bg-slate-950 border border-white/10 rounded-lg pl-8 pr-2 py-1 text-[9px] w-40 focus:border-blue-500 outline-none transition-all" />
              </div>
              <button onClick={handleFindLeader} disabled={isAnalyzing} className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-[9px] font-black uppercase">Lider</button>
              <button onClick={handleDetectCartel} disabled={isAnalyzing} className="px-3 py-1.5 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 text-fuchsia-400 border border-fuchsia-500/20 rounded-lg text-[9px] font-black uppercase">Cartel</button>
              <input value={pathSource} onChange={e => setPathSource(e.target.value)} placeholder="Sursă" className="bg-slate-950 border border-white/10 rounded-lg px-2 py-1 text-[9px] w-20 focus:border-indigo-500 outline-none" />
              <input value={pathTarget} onChange={e => setPathTarget(e.target.value)} placeholder="Destinație" className="bg-slate-950 border border-white/10 rounded-lg px-2 py-1 text-[9px] w-20 focus:border-indigo-500 outline-none" />
              <button onClick={handleShortestPath} className="p-1.5 bg-indigo-600 rounded-lg"><Route className="w-3.5 h-3.5 text-white"/></button>
              <button onClick={() => { setHighlightNodes(new Set()); setHighlightLinks(new Set()); setSelectedNode(null); setNodeColors({}); setNodeVals({}); }} className="p-2 hover:bg-white/10 rounded-full text-slate-400"><RotateCcw className="w-4 h-4" /></button>
              <button onClick={() => setShowGraph(false)} className="p-2 hover:bg-white/10 rounded-full text-slate-400"><X className="w-6 h-6" /></button>
            </div>
          </div>
          <div className="flex-1 relative bg-slate-950" onClick={() => handleNodeClick(null)}>
            <ForceGraph2D ref={graphRef} graphData={graphData} nodeLabel="name" 
              onNodeClick={(node, e) => { e.stopPropagation(); handleNodeClick(node); }}
              nodeColor={node => {
                if (graphSearch && !(node as any).name.toLowerCase().includes(graphSearch.toLowerCase())) return 'rgba(255,255,255,0.02)';
                if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) return 'rgba(255,255,255,0.03)';
                return (nodeColors[node.id as string] || (node as any).color);
              }}
              nodeVal={node => (nodeVals[node.id as string] || (node as any).val || 5) * (highlightNodes.has(node.id) ? 1.8 : 1)}
              linkColor={link => highlightLinks.has(link) ? 'rgba(59, 130, 246, 1)' : 'rgba(255,255,255,0.05)'}
              linkWidth={link => highlightLinks.has(link) ? 3 : 1}
              linkDirectionalParticles={link => highlightLinks.has(link) ? 6 : 0}
              nodeCanvasObjectMode={node => (highlightNodes.has(node.id) || !highlightNodes.size) ? 'after' : undefined}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                const label = node.name || node.valoare || node.filename || node.id || "Necunoscut";
                const fontSize = (node.label === "DOC" ? 14 : 12) / globalScale;
                ctx.font = `${fontSize}px Inter, Sans-Serif`; 
                const textWidth = ctx.measureText(label).width;
                const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.4);
                ctx.fillStyle = 'rgba(15, 23, 42, 0.9)'; 
                ctx.beginPath();
                ctx.roundRect(node.x - bckgDimensions[0] / 2, node.y - 15 - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1], 4); 
                ctx.fill();
                ctx.fillStyle = node.label === "DOC" ? "#22d3ee" : (node.color || "#94a3b8"); 
                ctx.textAlign = 'center'; 
                ctx.fillText(label, node.x, node.y - 15);
              }}
            />
          </div>
        </div>
      )}

      {/* BRIEFING MODAL */}
      {showBriefing && (
        <div className="fixed inset-0 z-[100] bg-slate-950/95 backdrop-blur-md flex flex-col p-12 animate-in zoom-in-95 duration-300">
          <div className="max-w-4xl mx-auto w-full flex-1 flex flex-col">
            <div className="flex justify-between items-center mb-12">
              <div className="flex items-center gap-4"><div className="p-3 bg-blue-600 rounded-2xl shadow-lg shadow-blue-900/40"><Brain className="w-8 h-8 text-white" /></div><h2 className="text-3xl font-black text-white uppercase tracking-tighter">Sinteză Executivă</h2></div>
              <div className="flex items-center gap-3">
                <button onClick={async () => {
                  setIsSummaryLoading(true);
                  try {
                    const res = await api.get(`/cases/${caseId}/summary`);
                    setCaseSummary(res.data.summary);
                    fetchData();
                  } catch (err) { alert("Eroare sinteză."); }
                  finally { setIsSummaryLoading(false); }
                }} disabled={isSummaryLoading} className="flex items-center gap-2 px-6 py-3 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-600/20 rounded-2xl text-blue-400 text-xs font-black uppercase tracking-widest transition-all">
                  {isSummaryLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />} Regenerează
                </button>
                <button onClick={() => setShowBriefing(false)} className="p-3 bg-white/5 hover:bg-white/10 rounded-full transition-colors text-white"><X className="w-8 h-8" /></button>
              </div>
            </div>
            <div className="flex-1 bg-slate-900/50 border border-white/5 rounded-[40px] p-12 overflow-y-auto custom-scrollbar shadow-2xl max-h-[70vh]">
              {caseSummary ? <p className="text-lg leading-relaxed text-slate-200 font-medium whitespace-pre-wrap italic">{caseSummary}</p> : <div className="h-full flex flex-col items-center justify-center text-center opacity-30"><Brain className="w-20 h-20 mb-6" /><p className="text-xl font-black uppercase tracking-widest">Nicio sinteză generată</p></div>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
