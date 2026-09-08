'use client';
import { useEffect, useState, useRef, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Folder, FileText, Landmark, Database, History, 
  Clock, Building2, User, Loader2, Send, MessageSquare, 
  ChevronLeft, Trash2, ArrowRightCircle, X, AlertTriangle, ExternalLink, Search, ScrollText, RotateCcw, Brain, Copy, Upload,
  Crosshair, Route, Share2, RefreshCw, Info, Sun, Moon, ChevronDown, ChevronUp, Pause, Play, Square, LogOut
} from 'lucide-react';
import { useTheme } from '../../../lib/ThemeProvider';

import dynamic from 'next/dynamic';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export default function CaseDetail() {
  const { theme, toggleTheme } = useTheme();
  const { id: caseId } = useParams();
  const router = useRouter();
  const graphRef = useRef<any>();
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [expandedDocs, setExpandedDocs] = useState<Set<number>>(new Set());

  const toggleDocExpand = (docId: number) => {
    setExpandedDocs(prev => {
      const next = new Set(prev);
      if (next.has(docId)) next.delete(docId);
      else next.add(docId);
      return next;
    });
  };
  
  const [caseInfo, setCaseInfo] = useState<any>(null);
  const [user, setUser] = useState<any>(null);
  const [entities, setEntities] = useState<any[]>([]);
  const [docs, setDocs] = useState<any[]>([]);
  const [docProgress, setDocProgress] = useState<Record<number, any>>({});
  const [activeModel, setActiveModel] = useState<string>('...');

  const fetchProgress = async (docId: number) => {
    try {
      const res = await api.get(`/cases/progress/${docId}`);
      setDocProgress(prev => ({ ...prev, [docId]: res.data }));
    } catch (err) { console.error("Progress Error", err); }
  };
  const [caseSummary, setCaseSummary] = useState<string>('');
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [showBriefing, setShowBriefing] = useState(false);
  const [snippetMode, setSnippetMode] = useState(true);
  const [evidencePreview, setEvidencePreview] = useState<{url: string, page: number, text: string, spatial?: string} | null>(null);

  const [showGraph, setShowGraph] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [timeline, setTimeline] = useState<any[]>([]);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
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
  const [streamingMessage, setStreamingMessage] = useState<{
    role: string, 
    content: string, 
    thought: string, 
    steps: string[], 
    toolCalls: any[], 
    observations: any[],
    traceLogs?: any[]
  } | null>(null);

  const token = Cookies.get('token');

  const renderForensicContent = (content: string, citations: any[]) => {
    if (!content) return null;
    
    // Verificăm dacă mesajul urmează formatul forensic (cu sau fără bold)
    if (!content.includes('[FACTS]') && !content.includes('[CONCLUSION]')) {
      return renderContentWithCitations(content, citations);
    }

    const sections: Record<string, string> = {};
    const sectionNames = ['FACTS', 'ANALYSIS', 'CONCLUSION', 'MISSING EVIDENCE', 'CONFIDENCE'];
    
    let currentSection = "";
    content.split('\n').forEach(line => {
      // Regex mai flexibil care acceptă și formatări de tipul **[FACTS]** sau [FACTS]:
      const match = line.match(/^\s*(\*\*)?\[(FACTS|ANALYSIS|CONCLUSION|MISSING EVIDENCE|CONFIDENCE)\](\*\*)?:?/);
      if (match) {
        currentSection = match[2];
        sections[currentSection] = "";
      } else if (currentSection) {
        sections[currentSection] += line + '\n';
      }
    });

    return (
      <div className="space-y-4 forensic-report text-slate-800 dark:text-slate-200">
        {sections['FACTS'] && (
          <div className="bg-blue-500/5 border border-blue-500/10 rounded-2xl p-4">
            <h4 className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 mb-3">
              <ScrollText className="w-3.5 h-3.5" /> Probe Identificate
            </h4>
            <div className="text-sm leading-relaxed whitespace-pre-wrap">
              {renderContentWithCitations(sections['FACTS'].trim(), citations)}
            </div>
          </div>
        )}

        {sections['ANALYSIS'] && (
          <div className="px-4 border-l-2 border-slate-200 dark:border-slate-800 italic text-slate-600 dark:text-slate-400">
            <h4 className="text-[9px] font-black uppercase tracking-tighter mb-1 opacity-50">Analiză Critică</h4>
            <div className="text-sm leading-relaxed whitespace-pre-wrap">
              {renderContentWithCitations(sections['ANALYSIS'].trim(), citations)}
            </div>
          </div>
        )}

        {sections['CONCLUSION'] && (
          <div className="bg-white dark:bg-slate-950 border-2 border-slate-200 dark:border-white/10 rounded-2xl p-5 shadow-sm">
            <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-900 dark:text-white mb-2">Concluzie Audit</h4>
            <div className="text-base font-bold leading-relaxed text-slate-900 dark:text-white whitespace-pre-wrap">
              {renderContentWithCitations(sections['CONCLUSION'].trim(), citations)}
            </div>
          </div>
        )}

        {sections['MISSING EVIDENCE'] && sections['MISSING EVIDENCE'].trim() && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-4">
            <h4 className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-amber-600 dark:text-amber-500 mb-2">
              <AlertTriangle className="w-3.5 h-3.5" /> Probe Lipsă / Lacune
            </h4>
            <div className="text-xs font-medium text-amber-700 dark:text-amber-500/80 leading-relaxed whitespace-pre-wrap">
              {sections['MISSING EVIDENCE'].trim()}
            </div>
          </div>
        )}

        {sections['CONFIDENCE'] && (
          <div className="flex justify-end">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-black uppercase tracking-widest shadow-sm ${
              sections['CONFIDENCE'].includes('HIGH') ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20' :
              sections['CONFIDENCE'].includes('MEDIUM') ? 'bg-amber-500/10 text-amber-600 border-amber-500/20' :
              'bg-red-500/10 text-red-600 border-red-500/20'
            }`}>
              <Shield className="w-3 h-3" /> Nivel Încredere: {sections['CONFIDENCE'].trim()}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderContentWithCitations = (content: string, citations: any[]) => {
    if (!content) return null;
    if (!citations || citations.length === 0) return <>{content}</>;
    
    const parts = content.split(/(\[\d+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const citeId = parseInt(match[1]);
        const cite = citations.find((c: any) => c.id === citeId);
        if (cite) {
          return (
            <span 
              key={idx} 
              onClick={() => {
                const doc = docs.find((d: any) => d.id === cite.doc_id);
                const filename = cite.filename || doc?.filename || docs[0]?.filename;
                setEvidencePreview({
                  url: `${process.env.NEXT_PUBLIC_API_URL}/uploads/${filename || ''}`,
                  page: cite.page || 1,
                  text: cite.content || ''
                });
              }}
              className="inline-flex items-center justify-center w-4 h-4 ml-1 text-[9px] font-bold text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/40 rounded-full cursor-pointer hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors shadow-sm"
              title="Vezi sursa documentului"
            >
              {citeId}
            </span>
          );
        }
      }
      return <span key={idx}>{part}</span>;
    });
  };

  const renderTraceLogs = (sql: string | null) => {
    if (!sql) return null;
    let logs: any[] = [];
    try {
      if (sql.trim().startsWith('[') && sql.trim().endsWith(']')) {
        logs = JSON.parse(sql);
      } else {
        logs = sql.split('\n').filter(Boolean).map(line => ({ type: 'status', data: line }));
      }
    } catch (e) {
      logs = [{ type: 'status', data: sql }];
    }

    return (
      <details className="mb-4 bg-slate-100/50 dark:bg-slate-950/50 rounded-xl border border-slate-200 dark:border-white/5 overflow-hidden group/trace">
        <summary className="px-4 py-2.5 text-[10px] font-bold text-slate-500 dark:text-slate-400 cursor-pointer hover:text-blue-500 dark:hover:text-blue-400 flex items-center gap-2 list-none uppercase tracking-tighter">
          <ScrollText className="w-3.5 h-3.5" /> Jurnal Investigare ({logs.filter(l => l.type === 'tool_call').length} Tool Calls) <ChevronDown className="w-3 h-3 group-open/trace:rotate-180 transition-transform" />
        </summary>
        <div className="px-4 pb-4 text-[11px] text-slate-600 dark:text-slate-400 font-medium leading-relaxed border-t border-slate-200 dark:border-white/5 pt-3 space-y-3">
          {logs.map((log: any, i: number) => {
            if (log.type === 'status' || log.type === 'step') {
              return (
                <div key={i} className="flex items-center gap-2 text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-tight">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500/50 animate-pulse" /> {log.data}
                </div>
              );
            }
            if (log.type === 'tool_call') {
              return (
                <div key={i} className="p-3 bg-blue-500/5 dark:bg-blue-500/10 border border-blue-500/10 dark:border-blue-500/20 rounded-xl">
                  <div className="text-[9px] font-black text-blue-600 dark:text-blue-400 uppercase mb-2 flex items-center gap-1">
                    <Search className="w-3 h-3" /> Executare Tool: {log.tool}
                  </div>
                  <pre className="text-[10px] font-mono text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-all bg-slate-200/50 dark:bg-slate-950/80 p-2.5 rounded-lg border border-slate-300/30 dark:border-white/5 overflow-x-auto">
                    {typeof log.params === 'object' ? JSON.stringify(log.params, null, 2) : log.params}
                  </pre>
                </div>
              );
            }
            if (log.type === 'observation') {
              return (
                <div key={i} className="p-3 bg-emerald-500/5 dark:bg-emerald-500/10 border border-emerald-500/10 dark:border-emerald-500/20 rounded-xl">
                  <div className="text-[9px] font-black text-emerald-600 dark:text-emerald-500 uppercase mb-2 flex items-center gap-1">
                    <FileText className="w-3 h-3" /> Rezultat / Observație
                  </div>
                  <div className="text-[10px] text-slate-600 dark:text-slate-300 max-h-60 overflow-y-auto whitespace-pre-wrap font-mono bg-slate-200/50 dark:bg-slate-950/80 p-2.5 rounded-lg border border-slate-300/30 dark:border-white/5 custom-scrollbar">
                    {log.data}
                  </div>
                </div>
              );
            }
            return null;
          })}
        </div>
      </details>
    );
  };

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

      // Verificăm progresul pentru documentele active (toate stările de procesare)
      const activeStatuses = ['PROCESSING', 'QUEUED', 'AI_EXTRACTING', 'DOCLING_OCR', 'RAG_INGESTING', 'AI_PENDING'];
      dRes.data.forEach((doc: any) => {
        if (activeStatuses.includes(doc.status)) {
          fetchProgress(doc.id);
        }
      });
    } catch (err) { console.error("Error", err); }
  };

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    fetchData();
    api.get(`/cases/${caseId}/chat`).then(res => setMessages(res.data));
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [caseId]);

  const formatETA = (seconds: number) => {
    if (!seconds || seconds <= 0) return 'calculând...';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    if (mins < 60) return `${mins}m ${secs}s`;
    const hours = Math.floor(mins / 60);
    const remMins = mins % 60;
    return `${hours}h ${remMins}m`;
  };

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
    } catch (err) {
      console.error("Eroare la stergere.", err);
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isChatLoading) return;
    
    const userMsg = { role: 'user', id: Date.now(), content: question };
    setMessages(prev => [...prev, userMsg]);
    setQuestion('');
    setIsChatLoading(true);
    
    // Inițializăm starea de streaming
    setStreamingMessage({
      role: 'assistant',
      content: '',
      thought: '',
      steps: [],
      toolCalls: [],
      observations: [],
      traceLogs: []
    });

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/cases/${caseId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question: userMsg.content })
      });

      if (!response.body) throw new Error("No body");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let fullContent = '';
      let currentThought = '';
      let isThinking = false;
      let buffer = '';
      let accumulatedCitations: any[] = [];
      const localTraceLogs: any[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Păstrăm ultima linie incompletă în buffer pentru runda următoare
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            
            if (data.type === 'status' || data.type === 'step') {
              localTraceLogs.push(data);
              setStreamingMessage(prev => prev ? { 
                ...prev, 
                steps: [...(prev.steps || []), data.data],
                traceLogs: [...(prev.traceLogs || []), data]
              } : null);
            }
            else if (data.type === 'chunk') {
              const text = data.data;
              
              if (text.includes('<think>')) {
                isThinking = true;
                continue;
              }
              if (text.includes('</think>')) {
                isThinking = false;
                continue;
              }
              
              if (isThinking) {
                currentThought += text;
                setStreamingMessage(prev => prev ? { ...prev, thought: currentThought } : null);
              } else {
                fullContent += text;
                setStreamingMessage(prev => prev ? { ...prev, content: fullContent } : null);
              }
            }
            else if (data.type === 'tool_call') {
              localTraceLogs.push(data);
              setStreamingMessage(prev => prev ? { 
                ...prev, 
                toolCalls: [...(prev.toolCalls || []), { name: data.tool, params: data.params }],
                traceLogs: [...(prev.traceLogs || []), data]
              } : null);
            }
            else if (data.type === 'observation') {
              localTraceLogs.push(data);
              const isThought = data.data && data.data.startsWith('Thinking:');
              setStreamingMessage(prev => {
                if (!prev) return null;
                const updated: any = {
                  ...prev,
                  traceLogs: [...(prev.traceLogs || []), data]
                };
                if (isThought) {
                  updated.thought = data.data.replace('Thinking:', '').trim();
                }
                return updated;
              });
            }
            else if (data.type === 'final') {
              fullContent = data.data;
              accumulatedCitations = data.citations || [];
              setStreamingMessage(prev => prev ? { 
                ...prev, 
                content: fullContent,
                observations: accumulatedCitations
              } : null);
            }
            else if (data.type === 'error') {
              setStreamingMessage(prev => prev ? { ...prev, content: `Eroare: ${data.data}` } : null);
            }
          } catch (e) {
            console.error("Error parsing chunk", e, line);
          }
        }
      }

      // La final, adăugăm mesajul complet în listă și resetăm streaming-ul
      setMessages(prev => [...prev, { 
        id: Date.now() + 1,
        role: 'assistant', 
        content: fullContent,
        thought: currentThought,
        citations: accumulatedCitations,
        sql: JSON.stringify(localTraceLogs)
      }]);
      setStreamingMessage(null);
      // fetchData() va fi chemat prin intervalul de 5 secunde existent pentru a actualiza restul datelor
    } catch (err) { 
      setMessages(prev => [...prev, { role: 'assistant', id: Date.now() + 2, content: 'Eroare la comunicarea cu serverul.' }]); 
    } finally { 
      setIsChatLoading(false); 
      setStreamingMessage(null);
    }
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

  const handleDownloadReport = async () => {
    try {
      const response = await api.get(`/cases/${caseId}/audit-report`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Raport_Audit_Dosar_${caseId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      console.error("Download error:", err);
      const msg = err.response?.data?.detail || "Eroare la descărcarea raportului. Asigurați-vă că dosarul are date procesate.";
      alert(msg);
    }
  };

  const parseSpatial = (spatial?: string) => {
    if (!spatial) return null;
    try {
      const parts: any = {};
      spatial.split(',').forEach(part => {
        const [key, val] = part.trim().split('=');
        parts[key] = parseFloat(val);
      });
      return parts;
    } catch { return null; }
  };

  const filteredData = useMemo(() => {
    if (!timeline.length || !graphData.nodes.length) return graphData;
    
    // SAFE MODE: Daca sliderul e la final, aratam tot
    if (currentTimeIndex === timeline.length - 1) return graphData;

    const activeDocNames = new Set(timeline.slice(0, currentTimeIndex + 1).map(e => e.doc_name).filter(Boolean));
    
    const visibleNodes = graphData.nodes.filter((n: any) => {
        if (n.label === "CASE") return true;
        // Documentele apar daca sunt in timeline-ul parcurs
        if (n.label === "DOC") return activeDocNames.has(n.name) || activeDocNames.has(n.filename);
        
        // Entitatile apar daca sunt legate de un document activ
        return graphData.links.some((l: any) => {
            const sId = typeof l.source === 'object' ? l.source.id : l.source;
            const tId = typeof l.target === 'object' ? l.target.id : l.target;
            const otherSideId = (sId === n.id) ? tId : (tId === n.id ? sId : null);
            if (!otherSideId) return false;
            
            const linkedNode = graphData.nodes.find((gn: any) => gn.id === otherSideId);
            return linkedNode && linkedNode.label === "DOC" && (activeDocNames.has(linkedNode.name) || activeDocNames.has(linkedNode.filename));
        });
    });

    const visibleNodeIds = new Set(visibleNodes.map((n: any) => n.id));
    const visibleLinks = graphData.links.filter((l: any) => {
        const sId = typeof l.source === 'object' ? l.source.id : l.source;
        const tId = typeof l.target === 'object' ? l.target.id : l.target;
        return visibleNodeIds.has(sId) && visibleNodeIds.has(tId);
    });

    return { nodes: visibleNodes, links: visibleLinks };
  }, [graphData, timeline, currentTimeIndex]);

  return (
    <div className="h-screen w-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 flex flex-col font-sans transition-colors duration-300 overflow-hidden">
      {/* HEADER */}
      <div className="bg-white/80 dark:bg-slate-900/50 border-b border-slate-200 dark:border-white/5 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-[1800px] mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button onClick={() => router.push('/cases')} className="p-2.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl border border-slate-200 dark:border-white/10 group transition-all">
              <ChevronLeft className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white" />
            </button>
            <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20"><Shield className="w-5 h-5 text-white" /></div>
              <div><h1 title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-sm font-black text-slate-900 dark:text-white uppercase leading-none italic tracking-tighter">DocAI v0.7.0 BETA</h1></div>
            </div>
            <div className="h-10 w-[1px] bg-slate-200 dark:bg-white/10" />
            <h1 className="text-xl font-black text-slate-900 dark:text-white uppercase truncate max-w-md italic">{caseInfo?.name || 'Încărcare...'}</h1>
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={toggleTheme}
              className="p-2.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl text-slate-600 dark:text-slate-400 transition-all border border-slate-200 dark:border-white/5"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 bg-blue-500/5 border border-blue-500/10 rounded-lg mr-2">
              <Brain className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span className="text-[10px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest">{activeModel}</span>
            </div>
            <button 
              onClick={handleDownloadReport}
              className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl text-rose-600 dark:text-rose-400 text-sm font-bold transition-all"
            >
              <ScrollText className="w-4 h-4" /> Raport Audit
            </button>
            <button onClick={async () => { 
              setIsGraphLoading(true); 
              try {
                const [gRes, tRes] = await Promise.all([
                  api.get(`/cases/${caseId}/graph`),
                  api.get(`/cases/${caseId}/timeline`).catch(() => ({ data: [] }))
                ]);
                setGraphData(gRes.data);
                setTimeline(tRes.data.length > 0 ? tRes.data : [
                  {date: '2026-01-01', title: 'Origine Dosar', type: 'INFO'},
                  {date: '2026-04-22', title: 'Stadiu Curent', type: 'INFO'}
                ]);
                setCurrentTimeIndex((tRes.data.length > 0 ? tRes.data.length : 2) - 1);
                setShowGraph(true); 
              } catch (err) { alert("Eroare încărcare graf."); }
              finally { setIsGraphLoading(false); }
            }} className="flex items-center gap-2 px-4 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 rounded-xl text-indigo-600 dark:text-indigo-400 text-sm font-bold transition-all">
              <Database className="w-4 h-4" /> Harta Relații
            </button>
            <button onClick={() => setShowBriefing(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl text-blue-600 dark:text-blue-400 text-sm font-bold transition-all">
              <Brain className="w-4 h-4" /> Briefing
            </button>
            <button 
              onClick={() => { Cookies.remove('token'); Cookies.remove('role'); router.push('/login'); }}
              className="flex items-center gap-2 px-3.5 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 text-sm font-bold transition-all ml-1"
              title="Deconectare din cont"
            >
              <LogOut className="w-4 h-4" /> Ieșire
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden h-[calc(100vh-80px)]">
        {/* SIDEBAR */}
        <div className="w-[450px] border-r border-slate-200 dark:border-white/5 flex flex-col bg-slate-100/50 dark:bg-slate-900/30 overflow-y-auto p-6 h-full custom-scrollbar">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-300 dark:border-slate-800 hover:border-blue-500/50 rounded-2xl cursor-pointer transition-all bg-white dark:bg-slate-900/50 hover:bg-blue-500/5 group mb-8 shadow-sm">
              <Upload className="w-8 h-8 text-slate-400 dark:text-slate-500 group-hover:text-blue-500 dark:group-hover:text-blue-400 mb-2" />
              <p className="text-sm font-bold text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-200">Încarcă probe noi</p>
              <input type="file" className="hidden" multiple onChange={async (e) => {
                if (!e.target.files) return;
                const fd = new FormData();
                fd.append('case_id', caseId as string);
                Array.from(e.target.files).forEach(f => fd.append('files', f));
                try { await api.post('/upload', fd); fetchData(); } catch (err) { alert("Eroare."); }
              }} />
            </label>
            <h3 className="text-[11px] font-black text-slate-400 dark:text-slate-500 uppercase mb-4 tracking-widest px-1">Documente în Dosar</h3>
            <div className="space-y-2">
              {docs.map(doc => (
                <div key={doc.id} className="p-4 bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-white/5 rounded-2xl group shadow-sm transition-all hover:shadow-md">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-xs font-bold truncate pr-4 text-slate-800 dark:text-slate-200">{doc.filename}</p>
                    <div className="flex items-center gap-2">
                      {doc.status === 'PARTIAL_COMPLETED' && (
                        <span title="Unele segmente nu au putut fi procesate de AI">
                          <AlertTriangle className="w-3 h-3 text-amber-500 animate-pulse" />
                        </span>
                      )}
                      <span className={`text-[8px] font-black px-2 py-0.5 rounded uppercase tracking-tighter ${
                        doc.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : 
                        doc.status === 'PARTIAL_COMPLETED' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20' :
                        doc.status === 'FAILED' ? 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20' :
                        doc.status === 'PAUSED' ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20' :
                        'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 animate-pulse'
                      }`}>
                        {doc.status === 'COMPLETED' ? 'Complet' : 
                         doc.status === 'PARTIAL_COMPLETED' ? 'Incomplet' :
                         doc.status === 'QUEUED' ? 'În Coadă' :
                         doc.status === 'DOCLING_OCR' ? 'OCR...' :
                         doc.status === 'RAG_INGESTING' ? 'Indexare...' :
                         doc.status === 'AI_PENDING' ? 'În Coadă AI' :
                         doc.status === 'FAILED' ? 'Eșuat' : 
                         doc.status === 'PAUSED' ? 'Pauză' :
                         'Procesare...'}
                      </span>
                    </div>
                  </div>
                  
                  {/* Progress Bar & ETA */}
                  {['PROCESSING', 'QUEUED', 'AI_EXTRACTING', 'DOCLING_OCR', 'RAG_INGESTING', 'AI_PENDING', 'PAUSED'].includes(doc.status) && docProgress[doc.id] && (
                    <div className="mb-3 px-1">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-[9px] font-black text-blue-500 uppercase tracking-tighter">
                          {docProgress[doc.id].message || `Progres: ${docProgress[doc.id].percent}%`}
                        </span>
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-tighter flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" /> ETA: {formatETA(docProgress[doc.id].eta_seconds)}
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 dark:bg-white/5 h-1.5 rounded-full overflow-hidden border border-slate-200 dark:border-white/5">
                        <div 
                          className={`h-full transition-all duration-500 ease-out ${doc.status === 'PAUSED' ? 'bg-orange-500' : 'bg-blue-500'}`}
                          style={{ width: `${docProgress[doc.id].percent}%` }}
                        />
                      </div>
                      <div className="mt-1 text-[8px] text-slate-400 font-bold uppercase text-right">
                        Segment {docProgress[doc.id].current_segment} / {docProgress[doc.id].total_segments}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <button onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/uploads/${doc.filename}`, '_blank')} className="text-[9px] font-black text-blue-600 dark:text-blue-400 uppercase flex items-center gap-1 hover:text-blue-500 transition-colors">
                      <ExternalLink className="w-2.5 h-2.5" /> Deschide
                    </button>

                    {/* Pause/Resume/Stop Controls */}
                    {['PROCESSING', 'QUEUED', 'AI_EXTRACTING', 'DOCLING_OCR', 'RAG_INGESTING', 'AI_PENDING'].includes(doc.status) && (
                      <>
                        <button onClick={async () => { await api.post(`/cases/documents/${doc.id}/pause`); fetchData(); }} className="text-[9px] font-black text-amber-600 dark:text-amber-500 uppercase flex items-center gap-1 hover:text-amber-400 transition-colors">
                          <Pause className="w-2.5 h-2.5" /> Pauză
                        </button>
                        <button onClick={async () => { if(confirm("Oprești procesarea?")) { await api.post(`/cases/documents/${doc.id}/stop`); fetchData(); } }} className="text-[9px] font-black text-red-600 dark:text-red-500 uppercase flex items-center gap-1 hover:text-red-400 transition-colors">
                          <Square className="w-2.5 h-2.5" /> Oprire
                        </button>
                      </>
                    )}
                    
                    {doc.status === 'PAUSED' && (
                      <>
                        <button onClick={async () => { await api.post(`/cases/documents/${doc.id}/resume`); fetchData(); }} className="text-[9px] font-black text-emerald-600 dark:text-emerald-500 uppercase flex items-center gap-1 hover:text-emerald-400 transition-colors">
                          <Play className="w-2.5 h-2.5" /> Reluare
                        </button>
                        <button onClick={async () => { if(confirm("Oprești procesarea?")) { await api.post(`/cases/documents/${doc.id}/stop`); fetchData(); } }} className="text-[9px] font-black text-red-600 text-red-500 uppercase flex items-center gap-1 hover:text-red-400 transition-colors">
                          <Square className="w-2.5 h-2.5" /> Oprire
                        </button>
                      </>
                    )}

                    {['FAILED', 'COMPLETED', 'PARTIAL_COMPLETED'].includes(doc.status) && (
                      <button 
                        onClick={async () => { 
                          if(confirm("Reîncepi procesarea documentului? Această acțiune va curăța VRAM-ul și va șterge datele vechi.")) { 
                            try {
                              await api.post(`/cases/documents/${doc.id}/retry`); 
                              fetchData(); 
                            } catch (err) { alert("Eroare la reîncercare."); }
                          } 
                        }} 
                        className="text-[9px] font-black text-indigo-600 dark:text-indigo-400 uppercase flex items-center gap-1 hover:text-indigo-500 transition-colors"
                        title="Curăță cache/VRAM și reprocesează"
                      >
                        <RefreshCw className="w-2.5 h-2.5" /> Reprocesare
                      </button>
                    )}

                    <button onClick={async () => { if(confirm("Ștergi documentul?")) { await api.post(`/cases/documents/${doc.id}/delete`); fetchData(); } }} className="text-[9px] font-black text-slate-400 dark:text-slate-600 uppercase flex items-center gap-1 hover:text-red-500 transition-colors">

                      <Trash2 className="w-2.5 h-2.5" /> Șterge
                    </button>
                    {doc.ai_summary && (
                      <button onClick={() => toggleDocExpand(doc.id)} className="text-[9px] font-black text-indigo-600 dark:text-indigo-400 uppercase flex items-center gap-1 hover:text-indigo-500 transition-colors ml-auto">
                        {expandedDocs.has(doc.id) ? <><ChevronUp className="w-3 h-3" /> Mai puțin</> : <><ChevronDown className="w-3 h-3" /> Sinteză AI</>}
                      </button>
                    )}
                  </div>
                  {doc.ai_summary && (
                    <p className={`mt-3 text-[10px] text-slate-500 dark:text-slate-400 italic leading-relaxed whitespace-pre-wrap border-t border-slate-100 dark:border-white/5 pt-3 ${!expandedDocs.has(doc.id) ? 'line-clamp-2' : ''}`}>
                      {doc.ai_summary}
                    </p>
                  )}
                </div>
              ))}
            </div>
        </div>

        {/* CHAT AREA */}
        <div className="flex-1 flex flex-col bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
          <div className="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar">
            {messages.map((msg, idx) => {
              let msgThought = msg.thought;
              if (!msgThought && msg.sql) {
                try {
                  const logs = JSON.parse(msg.sql);
                  const thoughtLog = logs.find((l: any) => l.type === 'observation' && l.data && l.data.startsWith('Thinking:'));
                  if (thoughtLog) {
                    msgThought = thoughtLog.data.replace('Thinking:', '').trim();
                  }
                } catch (e) {}
              }
              return (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} group/msg relative`}>
                  <div className={`max-w-[85%] rounded-3xl p-5 ${msg.role === 'user' ? 'bg-blue-600 text-white shadow-xl shadow-blue-500/20' : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/5 shadow-md dark:shadow-xl'} relative`}>
                    <button onClick={() => handleDeleteMessage(msg.id)} className="absolute -top-2 -right-2 p-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-full opacity-0 group-hover/msg:opacity-100 transition-opacity hover:text-red-500 shadow-xl"><Trash2 className="w-3 h-3" /></button>
                    <p className={`text-[10px] font-black uppercase tracking-widest mb-2 ${msg.role === 'user' ? 'text-blue-100' : 'text-slate-400 dark:text-slate-500'}`}>{msg.role === 'user' ? (user?.username || 'Investigator') : activeModel}</p>
                    
                    {/* Thought Process (pentru mesaje asistent) */}
                    {msgThought && (
                      <details className="mb-4 bg-slate-50 dark:bg-slate-950/50 rounded-xl border border-slate-100 dark:border-white/5 overflow-hidden group/thought">
                        <summary className="px-4 py-2 text-[10px] font-bold text-slate-500 cursor-pointer hover:text-blue-500 flex items-center gap-2 list-none uppercase tracking-tighter">
                          <Brain className="w-3 h-3" /> Raționament Intern <ChevronDown className="w-3 h-3 group-open/thought:rotate-180 transition-transform" />
                        </summary>
                        <div className="px-4 pb-4 text-[11px] text-slate-500 dark:text-slate-400 font-medium italic leading-relaxed whitespace-pre-wrap border-t border-slate-100 dark:border-white/5 pt-3">
                          {msgThought}
                        </div>
                      </details>
                    )}

                  {/* Jurnal Investigare (dacă există logs în msg.sql) */}
                  {msg.role === 'assistant' && msg.sql && renderTraceLogs(msg.sql)}

                  <p className={`text-sm font-medium leading-relaxed whitespace-pre-wrap ${msg.role === 'user' ? 'text-white' : 'text-slate-800 dark:text-slate-200'}`}>
                    {msg.role === 'user' ? msg.content : renderForensicContent(msg.content, msg.citations)}
                  </p>
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-100 dark:border-white/5 space-y-2">
                      {msg.citations.map((cite: any, i: number) => (
                        <div key={i} onClick={() => { 
                          const doc = docs.find((d: any) => d.id === cite.doc_id);
                          const filename = cite.filename || doc?.filename || docs[0]?.filename;
                          setEvidencePreview({ 
                            url: `${process.env.NEXT_PUBLIC_API_URL}/uploads/${filename}`, 
                            page: cite.page || 1, 
                            text: cite.content || '',
                            spatial: cite.spatial
                          }); 
                        }} className="p-2.5 bg-blue-500/5 border-l-2 border-blue-500 rounded-r-lg text-[11px] text-slate-500 dark:text-slate-400 italic cursor-pointer hover:bg-blue-500/10 transition-all flex justify-between group/cite">
                          <span className="line-clamp-2">"{cite.content || ''}"</span>
                          <div className="flex gap-1 opacity-0 group-hover/cite:opacity-100">
                            {cite.spatial && (
                              <span title="Grounding Spațial Detectat">
                                <Crosshair className="w-3 h-3 text-blue-500" />
                              </span>
                            )}
                            <ExternalLink className="w-3 h-3" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
            })}

            {/* Mesajul de Streaming ACTIV */}
            {streamingMessage && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-3xl p-5 bg-white dark:bg-slate-900 border-2 border-blue-500/30 shadow-2xl relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-blue-500/10 overflow-hidden">
                     <div className="h-full bg-blue-500 animate-progress" style={{ width: '40%' }}></div>
                  </div>
                  <div className="flex justify-between items-start mb-3">
                    <p className="text-[10px] font-black text-blue-500 uppercase tracking-widest flex items-center gap-2">
                      <Loader2 className="w-3 h-3 animate-spin" /> Investigare în curs...
                    </p>
                    <button 
                      onClick={async () => {
                        await api.post(`/cases/${caseId}/chat/stop`);
                        setIsChatLoading(false);
                        setStreamingMessage(null);
                        fetchData();
                      }}
                      className="px-2 py-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg text-[9px] font-black text-red-500 uppercase transition-all flex items-center gap-1"
                    >
                      <Square className="w-2 h-2 fill-current" /> Stop
                    </button>
                  </div>
                  
                  {/* Jurnal Investigare Live */}
                  {streamingMessage.traceLogs && streamingMessage.traceLogs.length > 0 && (
                    <details open className="mb-4 bg-slate-100/50 dark:bg-slate-950/50 rounded-xl border border-slate-200 dark:border-white/5 overflow-hidden group/trace">
                      <summary className="px-4 py-2.5 text-[10px] font-bold text-slate-500 dark:text-slate-400 cursor-pointer hover:text-blue-500 dark:hover:text-blue-400 flex items-center gap-2 list-none uppercase tracking-tighter">
                        <ScrollText className="w-3.5 h-3.5" /> Jurnal Investigare Live ({streamingMessage.traceLogs.filter(l => l.type === 'tool_call').length} Tool Calls) <ChevronDown className="w-3 h-3 group-open/trace:rotate-180 transition-transform" />
                      </summary>
                      <div className="px-4 pb-4 text-[11px] text-slate-600 dark:text-slate-400 font-medium leading-relaxed border-t border-slate-200 dark:border-white/5 pt-3 space-y-3">
                        {streamingMessage.traceLogs.map((log: any, i: number) => {
                          if (log.type === 'status' || log.type === 'step') {
                            return (
                              <div key={i} className="flex items-center gap-2 text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-tight animate-pulse">
                                <div className="w-1.5 h-1.5 rounded-full bg-blue-500/50 animate-pulse" /> {log.data}
                              </div>
                            );
                          }
                          if (log.type === 'tool_call') {
                            return (
                              <div key={i} className="p-3 bg-blue-500/5 dark:bg-blue-500/10 border border-blue-500/10 dark:border-blue-500/20 rounded-xl">
                                <div className="text-[9px] font-black text-blue-600 dark:text-blue-400 uppercase mb-2 flex items-center gap-1">
                                  <Search className="w-3 h-3" /> Executare Tool: {log.tool}
                                </div>
                                <pre className="text-[10px] font-mono text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-all bg-slate-200/50 dark:bg-slate-950/80 p-2.5 rounded-lg border border-slate-300/30 dark:border-white/5 overflow-x-auto">
                                  {typeof log.params === 'object' ? JSON.stringify(log.params, null, 2) : log.params}
                                </pre>
                              </div>
                            );
                          }
                          if (log.type === 'observation') {
                            return (
                              <div key={i} className="p-3 bg-emerald-500/5 dark:bg-emerald-500/10 border border-emerald-500/10 dark:border-emerald-500/20 rounded-xl">
                                <div className="text-[9px] font-black text-emerald-600 dark:text-emerald-500 uppercase mb-2 flex items-center gap-1">
                                  <FileText className="w-3 h-3" /> Rezultat / Observație
                                </div>
                                <div className="text-[10px] text-slate-600 dark:text-slate-300 max-h-60 overflow-y-auto whitespace-pre-wrap font-mono bg-slate-200/50 dark:bg-slate-950/80 p-2.5 rounded-lg border border-slate-300/30 dark:border-white/5 custom-scrollbar">
                                  {log.data}
                                </div>
                              </div>
                            );
                          }
                          return null;
                        })}
                      </div>
                    </details>
                  )}

                  {/* Gândirea Live */}
                  {streamingMessage.thought && (
                    <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-950/50 rounded-xl border border-slate-100 dark:border-white/5">
                      <p className="text-[9px] font-black text-slate-400 uppercase mb-2 flex items-center gap-1"><Brain className="w-3 h-3" /> Raționament...</p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium italic leading-relaxed whitespace-pre-wrap animate-pulse">
                        {streamingMessage.thought}
                      </p>
                    </div>
                  )}

                  {/* Răspunsul Parțial */}
                  {streamingMessage.content && (
                    <div className="text-sm font-medium leading-relaxed whitespace-pre-wrap text-slate-800 dark:text-slate-200">
                      {renderForensicContent(streamingMessage.content, streamingMessage.observations || [])}
                    </div>
                  )}
                  
                  {!streamingMessage.content && !streamingMessage.thought && (
                    <div className="flex gap-1 items-center py-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0s' }} />
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0.2s' }} />
                      <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0.4s' }} />
                    </div>
                  )}
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <div className="p-8 bg-white/50 dark:bg-slate-950 border-t border-slate-200 dark:border-white/5">
            <form onSubmit={handleAsk} className="relative group">
              <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Interoghează dosarul..." className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-white/10 rounded-2xl px-6 py-5 text-sm font-medium text-slate-900 dark:text-white focus:outline-none focus:border-blue-500/50 transition-all shadow-sm" />
              <button type="submit" disabled={isChatLoading} className="absolute right-3 top-3 bottom-3 px-6 bg-blue-600 hover:bg-blue-500 rounded-xl text-xs font-black uppercase transition-all flex items-center gap-2 text-white">
                {isChatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Interoghează
              </button>
            </form>
            <div className="mt-4 flex justify-between items-center px-2">
              <button onClick={handleClearChat} className="text-[10px] font-black text-slate-400 hover:text-red-500 uppercase flex items-center gap-1.5 transition-colors"><RotateCcw className="w-3 h-3" /> Golește Istoric</button>
              <span title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-[10px] font-black text-slate-300 dark:text-slate-700 uppercase tracking-widest italic">DocAI v0.3 ALPHA • Test Mode</span>
            </div>
          </div>
        </div>

        {/* PREVIEW PANEL (FIXED) */}
        {evidencePreview && (
          <div className="fixed top-20 right-0 bottom-0 w-[750px] bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-white/10 flex flex-col shadow-2xl z-[60] animate-in slide-in-from-right duration-300">
            <div className="p-5 border-b border-slate-200 dark:border-white/5 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-600 rounded-xl">
                  <FileText className="w-5 h-5 text-white" />
                </div>
                <div>
                  <span className="text-xs font-black text-slate-900 dark:text-slate-200 uppercase tracking-widest block">Sursă Documentară</span>
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Pagina {evidencePreview.page} • Dosar {caseId}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => window.open(`${evidencePreview.url}#page=${evidencePreview.page}`, '_blank')}
                  className="p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-slate-500 hover:text-blue-500 transition-all shadow-sm"
                  title="Deschide în filă nouă"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
                <button onClick={() => setEvidencePreview(null)} className="p-2.5 hover:bg-red-500/10 rounded-full text-slate-500 hover:text-red-500 transition-colors"><X className="w-6 h-6" /></button>
              </div>
            </div>

            <div className="flex-1 bg-slate-200 dark:bg-slate-950 overflow-auto custom-scrollbar relative">
              {/* WRAPPER CARE SCROLEAZA TOTUL (PDF + BARA) */}
              <div className="relative w-full" style={{ height: '1500px', minWidth: '100%' }}>
                <iframe 
                    key={`${evidencePreview.url}-${evidencePreview.page}`} 
                    src={`${evidencePreview.url}#page=${evidencePreview.page}&view=FitH&toolbar=0&navpanes=0`} 
                    className="absolute inset-0 w-full h-full border-none pointer-events-none" 
                />
                
                {/* CHENAR ROSU (Acum se va misca odata cu scroll-ul de deasupra) */}
                {evidencePreview.spatial && parseSpatial(evidencePreview.spatial) && (
                  <div 
                    className="absolute border-[6px] border-rose-500 bg-rose-500/5 pointer-events-none z-10 shadow-[0_0_0_2000px_rgba(0,0,0,0.4)]"
                    style={{
                      left: `${(parseSpatial(evidencePreview.spatial).x / 595) * 100}%`,
                      top: `${(parseSpatial(evidencePreview.spatial).y / 842) * 100}%`,
                      width: `${(parseSpatial(evidencePreview.spatial).w / 595) * 100}%`,
                      height: `${(parseSpatial(evidencePreview.spatial).h / 842) * 100}%`,
                      transform: 'translate(-3px, -3px)'
                    }}
                  >
                    <div className="absolute -top-7 left-0 bg-rose-500 text-white text-[9px] font-black px-2 py-1 rounded shadow-lg uppercase tracking-widest whitespace-nowrap">
                       <Crosshair className="w-3 h-3 inline mr-1" /> Pasaj Identificat
                    </div>
                  </div>
                )}
              </div>
            </div>

            {evidencePreview.text && (
               <div className="p-8 bg-white dark:bg-slate-950 border-t-2 border-indigo-500/20 shadow-2xl">
                 <h4 className="text-[10px] font-black text-indigo-500 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                   <ScrollText className="w-4 h-4" /> Fragment Probat
                 </h4>
                 <div className="bg-indigo-500/5 dark:bg-slate-900 p-6 rounded-2xl border border-indigo-500/10 relative">
                   <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 rounded-l-2xl"></div>
                   <p className="text-sm text-slate-700 dark:text-slate-300 font-bold leading-relaxed italic">"{evidencePreview.text}"</p>
                 </div>
               </div>
            )}
          </div>
        )}
      </div>

      {/* GRAPH MODAL */}
      {showGraph && (
        <div className="fixed inset-0 z-[100] bg-slate-950/95 backdrop-blur-md flex flex-col animate-in fade-in duration-300 overflow-hidden h-screen w-screen">
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
          
          <div className="flex-1 relative bg-slate-950 overflow-hidden" onClick={() => handleNodeClick(null)}>
            {/* Recentrează Probele */}
            <div className="absolute top-6 left-1/2 -translate-x-1/2 z-50">
                <button 
                    onClick={() => graphRef.current?.zoomToFit(400)}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 border border-white/20 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all shadow-[0_0_30px_rgba(79,70,229,0.4)]"
                >
                    Recentrează Probele
                </button>
            </div>

            <ForceGraph2D ref={graphRef} graphData={filteredData} nodeLabel="name" 
              width={typeof window !== 'undefined' ? window.innerWidth : 1200}
              height={typeof window !== 'undefined' ? window.innerHeight - 80 : 800}
              onNodeClick={(node, e) => { e.stopPropagation(); handleNodeClick(node); }}
              nodeColor={node => {
                if (graphSearch && !(node as any).name.toLowerCase().includes(graphSearch.toLowerCase())) return 'rgba(255,255,255,0.02)';
                if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) return 'rgba(255,255,255,0.03)';
                return (nodeColors[node.id as string] || (node as any).color);
              }}
              // Scalare Logaritmică
              nodeVal={node => {
                const rawVal = nodeVals[node.id as string] || (node as any).val || 5;
                const baseVal = Math.log2(rawVal + 1) * 3 + 2;
                return baseVal * (highlightNodes.has(node.id) ? 1.8 : 1);
              }}
              linkColor={link => {
                if (highlightLinks.has(link)) return 'rgba(99, 102, 241, 1)';
                return 'rgba(255,255,255,0.3)'; // Mai vizibile
              }}
              linkWidth={link => highlightLinks.has(link) ? 3 : 1.5}
              linkDirectionalParticles={link => highlightLinks.has(link) ? 6 : 0}
              nodeCanvasObjectMode={node => (highlightNodes.has(node.id) || !highlightNodes.size) ? 'after' : undefined}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                // Nu afișăm label-uri dacă suntem la zoom out mare (performance + clarity)
                if (globalScale < 1.2 && highlightNodes.size === 0) return;

                const label = node.name || node.valoare || node.filename || node.id || "Necunoscut";
                const fontSize = (node.label === "DOC" ? 14 : 12) / globalScale;
                ctx.font = `${fontSize}px Inter, Sans-Serif`; 
                
                ctx.fillStyle = 'rgba(255, 255, 255, 0.85)'; 
                ctx.textAlign = 'center'; 
                ctx.textBaseline = 'top';
                
                const boudingRadius = Math.log2((nodeVals[node.id] || (node as any).val || 5) + 1) * 3 + 2;
                ctx.fillText(label, node.x, node.y + boudingRadius + 2);
              }}
            />

            {/* TIMELINE MACHINE (Right Control) */}
            {timeline.length > 0 && (
                <div className="fixed top-32 right-12 z-[100] w-96 bg-slate-900 border-2 border-indigo-500/30 rounded-[2.5rem] p-8 shadow-[0_0_60px_rgba(0,0,0,0.8)] pointer-events-auto" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center gap-4 mb-6">
                        <div className="p-3 bg-indigo-600 rounded-2xl shadow-lg shadow-indigo-900/40">
                            <Shield className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <p className="text-[11px] font-black text-indigo-400 uppercase tracking-widest mb-1">Chronos v1.0</p>
                            <p className="text-lg font-bold text-white tracking-tight leading-none uppercase">Time Machine</p>
                        </div>
                    </div>

                    <div className="space-y-8">
                        <div className="bg-black/40 rounded-[1.5rem] p-5 border border-white/5 shadow-inner">
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-2">Punct Temporal Selectat</p>
                            <p className="text-sm font-bold text-indigo-300 mb-2">{timeline[currentTimeIndex]?.date}</p>
                            <p className="text-xs text-white font-medium line-clamp-2 leading-relaxed italic opacity-80">"{timeline[currentTimeIndex]?.title}"</p>
                        </div>

                        <div className="px-2">
                            <input 
                                type="range" 
                                min="0" 
                                max={timeline.length - 1} 
                                value={currentTimeIndex} 
                                onChange={(e) => setCurrentTimeIndex(parseInt(e.target.value))}
                                className="w-full h-2 bg-slate-800 rounded-full appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400 transition-all shadow-[0_0_15px_rgba(99,102,241,0.2)]"
                            />
                        </div>

                        <div className="flex justify-between items-center">
                            <div className="flex flex-col">
                                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Origine</span>
                                <span className="text-[11px] font-bold text-white opacity-40">{timeline[0]?.date}</span>
                            </div>
                            <div className="px-4 py-1.5 bg-indigo-500/10 rounded-full border border-indigo-500/20">
                                <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">{currentTimeIndex + 1} / {timeline.length}</span>
                            </div>
                            <div className="flex flex-col items-end">
                                <span className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Orizont</span>
                                <span className="text-[11px] font-bold text-white opacity-40">{timeline[timeline.length-1]?.date}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
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
