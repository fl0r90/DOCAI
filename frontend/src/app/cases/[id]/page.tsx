'use client';
import { useEffect, useState, useRef, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import { 
  Shield, Folder, FileText, Landmark, Database, History, 
  Clock, Building2, User, Loader2, Send, MessageSquare, 
  ChevronLeft, Trash2, ArrowRightCircle, X, AlertTriangle, ExternalLink, Search, ScrollText, RotateCcw, Brain, Copy, Upload,
  Crosshair, Route, Share2, RefreshCw, Info, Sun, Moon, ChevronDown, ChevronUp, Pause, Play, Square, LogOut,
  ZoomIn, ZoomOut, Image as ImageIcon, Download, Check
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
  const [evidencePreview, setEvidencePreview] = useState<{
    url: string;
    page: number;
    text: string;
    spatial?: string;
    highlight?: string;
    filename?: string;
    docId?: number | string;
    docType?: string;
  } | null>(null);
  const [docContentData, setDocContentData] = useState<{
    docId: number | string | null;
    rawText: string;
    loading: boolean;
    error: string | null;
  }>({ docId: null, rawText: '', loading: false, error: null });
  const [imageZoom, setImageZoom] = useState<number>(1);
  const [copiedEvidence, setCopiedEvidence] = useState(false);
  const pdfCanvasRef = useRef<HTMLCanvasElement>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState(false);

  const [showGraph, setShowGraph] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [timeline, setTimeline] = useState<any[]>([]);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [isGraphLoading, setIsGraphLoading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [highlightLinks, setHighlightLinks] = useState(new Set());
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [hoverNode, setHoverNode] = useState<any>(null);
  const [nodeColors, setNodeColors] = useState<Record<string, string>>({});
  const [nodeVals, setNodeVals] = useState<Record<string, number>>({});
  const [graphSearch, setGraphSearch] = useState('');
  const [pathSource, setPathSource] = useState('');
  const [pathTarget, setPathTarget] = useState('');
  const [cloneCui, setCloneCui] = useState('');

  const [messages, setMessages] = useState<any[]>([]);
  const [question, setQuestion] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [backgroundChatStatus, setBackgroundChatStatus] = useState<any>(null);
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

  const renderHighlightedSnippet = (content: string, term?: string) => {
    if (!content) return '';
    if (!term || !term.trim() || term.length < 2) return content;
    try {
      const escaped = term.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(${escaped})`, 'gi');
      const parts = content.split(regex);
      if (parts.length === 1) {
        const words = term.trim().split(/\s+/).filter(w => w.length >= 3);
        if (words.length > 0) {
          const wordRegex = new RegExp(`\\b(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'gi');
          const wordParts = content.split(wordRegex);
          return wordParts.map((part, i) =>
            wordRegex.test(part) ? (
              <mark key={i} className="bg-yellow-300 dark:bg-yellow-400 text-slate-950 font-black px-1 py-0.5 rounded shadow-sm">
                {part}
              </mark>
            ) : part
          );
        }
        return content;
      }
      return parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-yellow-300 dark:bg-yellow-400 text-slate-950 font-black px-1 py-0.5 rounded shadow-sm">
            {part}
          </mark>
        ) : part
      );
    } catch (e) {
      return content;
    }
  };

  const renderDocReaderContent = (rawText: string, searchTarget: string) => {
    if (!rawText) return null;
    const paragraphs = rawText.split(/\n\s*\n/);
    const targetClean = searchTarget ? searchTarget.trim() : '';
    const searchKeywords = targetClean.split(/\s+/).filter(w => w.length >= 3);

    let bestIdx = -1;
    let maxMatches = 0;

    paragraphs.forEach((p, idx) => {
      if (!targetClean) return;
      if (p.toLowerCase().includes(targetClean.toLowerCase())) {
        bestIdx = idx;
        maxMatches = 999;
        return;
      }
      if (maxMatches < 999) {
        let matches = 0;
        for (const kw of searchKeywords) {
          if (p.toLowerCase().includes(kw.toLowerCase())) matches++;
        }
        if (matches > maxMatches && matches >= 2) {
          maxMatches = matches;
          bestIdx = idx;
        }
      }
    });

    return (
      <div className="space-y-4">
        {paragraphs.map((p, idx) => {
          const isTarget = idx === bestIdx;
          return (
            <div
              key={idx}
              id={isTarget ? 'cited-reader-target' : undefined}
              className={`p-4 rounded-xl leading-relaxed text-sm transition-all duration-300 ${
                isTarget
                  ? 'bg-yellow-50 dark:bg-yellow-500/15 border-2 border-yellow-400 dark:border-yellow-500 shadow-[0_0_20px_rgba(250,204,21,0.25)] ring-4 ring-yellow-400/20'
                  : 'bg-transparent hover:bg-slate-50 dark:hover:bg-slate-800/30 border border-transparent'
              }`}
            >
              {isTarget && (
                <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-yellow-700 dark:text-yellow-400 mb-2">
                  <ScrollText className="w-3.5 h-3.5" /> Paragraf Citat
                </div>
              )}
              <p className="whitespace-pre-wrap font-serif text-[13px] leading-relaxed text-slate-800 dark:text-slate-200">
                {renderHighlightedSnippet(p, targetClean)}
              </p>
            </div>
          );
        })}
      </div>
    );
  };

  const openCitationPreview = (cite: any) => {
    const doc = docs.find((d: any) => d.id === cite.doc_id || d.filename === cite.filename);
    const filename = cite.filename || doc?.filename || docs[0]?.filename || '';
    const docId = cite.doc_id && cite.doc_id !== 'SQL_DB' ? cite.doc_id : doc?.id;
    const docType = doc?.doc_type || (filename.split('.').pop()?.toLowerCase()) || '';
    setEvidencePreview({
      url: `${process.env.NEXT_PUBLIC_API_URL}/uploads/${filename}`,
      page: cite.page || 1,
      text: cite.content || '',
      spatial: cite.spatial,
      highlight: cite.highlight_term || '',
      filename: filename,
      docId: docId,
      docType: docType
    });
  };

  const renderContentWithCitations = (content: string, citations: any[]) => {
    if (!content) return null;
    if (!citations || citations.length === 0) return <>{content}</>;
    
    const parts = content.split(/(\[(?:REF\s*)?\d+\])/gi);
    return parts.map((part, idx) => {
      const match = part.match(/\[(?:REF\s*)?(\d+)\]/i);
      if (match) {
        const citeId = parseInt(match[1]);
        const cite = citations.find((c: any) => c.id === citeId);
        if (cite) {
          return (
            <button 
              key={idx} 
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                openCitationPreview(cite);
              }}
              className="inline-flex items-center justify-center px-1.5 py-0.5 ml-1 text-[10px] font-black text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/50 hover:bg-blue-200 dark:hover:bg-blue-800 rounded-md cursor-pointer transition-all shadow-sm border border-blue-300/40 dark:border-blue-700/40 hover:scale-105 select-none align-baseline"
              title={`Vezi sursa: ${cite.filename || 'Document'} (Pagina ${cite.page || 1})`}
            >
              REF {citeId}
            </button>
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

      // Verificăm dacă există o investigație activă în fundal pe server
      try {
        const sRes = await api.get(`/cases/${caseId}/chat/status`);
        if (sRes.data?.is_running) {
          setBackgroundChatStatus(sRes.data);
        } else {
          setBackgroundChatStatus((prev: any) => {
            if (prev?.is_running) {
              // Investigatia tocmai s-a finalizat, reîncărcăm automat istoricul
              api.get(`/cases/${caseId}/chat`).then(cRes => setMessages(cRes.data));
            }
            return null;
          });
        }
      } catch (e) {}
    } catch (err) { console.error("Error", err); }
  };

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    if (caseId && typeof window !== 'undefined') {
      localStorage.setItem('last_selected_case_id', caseId as string);
    }
    fetchData();
    api.get(`/cases/${caseId}/chat`).then(res => setMessages(res.data));
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [caseId]);

  const handleBack = () => {
    if (typeof window !== 'undefined' && window.history.state && window.history.state.idx > 0) {
      router.back();
    } else {
      router.push('/');
    }
  };

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

  const handleAsk = async (e?: React.FormEvent | React.SyntheticEvent) => {
    if (e) e.preventDefault();
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
      console.log("[CHAT] Token present:", !!token, "Token preview:", token ? token.slice(0, 20) + "..." : "MISSING");
      const response = await fetch(`${baseUrl}/cases/${caseId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ question: userMsg.content })
      });

      console.log("[CHAT] Response status:", response.status, response.statusText);
      if (!response.ok) {
        const errText = await response.text();
        console.error("[CHAT] Error response:", errText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

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
      console.error("[CHAT] Exception:", err);
      const errorMsg = err instanceof Error ? err.message : 'Eroare necunoscută';
      setMessages(prev => [...prev, { role: 'assistant', id: Date.now() + 2, content: `Eroare: ${errorMsg}` }]); 
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

  const renderPdfWithHighlight = async (url: string, page: number, highlightText: string) => {
    const canvas = pdfCanvasRef.current;
    if (!canvas) { setPdfError(true); return; }
    setPdfError(false);
    try {
      setPdfLoading(true);
      if (!(window as any).pdfjsLib) {
        await new Promise<void>((resolve, reject) => {
          const s = document.createElement('script');
          s.src = '/pdfjs/pdf.min.js';
          s.onload = () => resolve();
          s.onerror = () => reject(new Error('PDF.js load failed'));
          document.head.appendChild(s);
        });
      }
      const pdfjsLib = (window as any).pdfjsLib;
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdfjs/pdf.worker.min.js';
      const pdf = await pdfjsLib.getDocument(url).promise;
      const pdfPage = await pdf.getPage(page);
      const scale = 2.0;
      const viewport = pdfPage.getViewport({ scale });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      await pdfPage.render({ canvasContext: ctx, viewport }).promise;
      const textContent = await pdfPage.getTextContent();
      const items = (textContent.items as any[]).filter((it: any) => it.str && it.str.trim());
      const cleanSearch = highlightText.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
      if (!cleanSearch) return;
      let fullText = '';
      const itemMap: { start: number; end: number; item: any }[] = [];
      for (const item of items) {
        itemMap.push({ start: fullText.length, end: fullText.length + item.str.length, item });
        fullText += item.str;
      }
      const normFull = fullText.toLowerCase();
      let searchStr = cleanSearch.substring(0, 80);
      let matchIdx = normFull.indexOf(searchStr);
      if (matchIdx === -1) {
        const escaped = searchStr.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(escaped.replace(/ /g, '\\s+'), 'i');
        const m = regex.exec(fullText);
        if (m) { matchIdx = m.index; searchStr = m[0].toLowerCase(); }
      }
      if (matchIdx === -1) return;
      const matchEnd = matchIdx + searchStr.length;
      const overlapping = itemMap.filter(p => p.start < matchEnd && p.end > matchIdx);
      if (overlapping.length === 0) return;
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const p of overlapping) {
        const t = p.item.transform;
        const x = t[4], y = t[5], w = p.item.width || 0, h = p.item.height || 0;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x + w);
        maxY = Math.max(maxY, y + h);
      }
      const pageH = pdfPage.view[3];
      const pad = 4;
      const hx = (minX - pad) * scale;
      const hy = (pageH - maxY - pad) * scale;
      const hw = (maxX - minX + pad * 2) * scale;
      const hh = (maxY - minY + pad * 2) * scale;
      ctx.save();
      ctx.fillStyle = 'rgba(250, 204, 21, 0.35)';
      ctx.fillRect(hx, hy, hw, hh);
      ctx.strokeStyle = 'rgba(202, 138, 4, 0.9)';
      ctx.lineWidth = 3;
      ctx.strokeRect(hx, hy, hw, hh);
      ctx.restore();
    } catch (e) {
      console.error('PDF highlight error:', e);
      setPdfError(true);
    } finally {
      setPdfLoading(false);
    }
  };

  useEffect(() => {
    if (!evidencePreview) {
      setDocContentData({ docId: null, rawText: '', loading: false, error: null });
      setImageZoom(1);
      return;
    }

    const ext = (evidencePreview.filename || '').split('.').pop()?.toLowerCase() || '';
    const isPdf = ext === 'pdf' || evidencePreview.docType?.toLowerCase() === 'pdf';
    const isImg = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'gif', 'svg'].includes(ext) || ['image', 'jpeg', 'png'].includes(evidencePreview.docType?.toLowerCase() || '');

    if (isPdf) {
      setPdfLoading(true);
    } else {
      setPdfLoading(false);
    }

    if (isImg) {
      setImageZoom(1);
    }

    if (!isPdf && !isImg && evidencePreview.docId && evidencePreview.docId !== 'SQL_DB') {
      setDocContentData({ docId: evidencePreview.docId, rawText: '', loading: true, error: null });
      api.get(`/cases/documents/${evidencePreview.docId}/content`)
        .then(res => {
          setDocContentData({
            docId: evidencePreview.docId,
            rawText: res.data.raw_text || '',
            loading: false,
            error: null
          });
        })
        .catch(err => {
          console.error("Failed to load document content", err);
          setDocContentData({
            docId: evidencePreview.docId,
            rawText: '',
            loading: false,
            error: 'Nu s-a putut încărca conținutul text al documentului.'
          });
        });
    }
  }, [evidencePreview?.docId, evidencePreview?.filename]);

  useEffect(() => {
    if (evidencePreview && docContentData.rawText) {
      const timer = setTimeout(() => {
        const el = document.getElementById('cited-reader-target');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 350);
      return () => clearTimeout(timer);
    }
  }, [docContentData.rawText, evidencePreview]);

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

  useEffect(() => {
    if (showGraph && graphRef.current) {
      const fg = graphRef.current;
      fg.d3Force('charge')?.strength(-400)?.distanceMax(800);
      fg.d3Force('link')?.distance(85);
      setTimeout(() => {
        fg.zoomToFit?.(400, 60);
      }, 400);
    }
  }, [showGraph]);

  return (
    <div className="h-screen w-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-200 flex flex-col font-sans transition-colors duration-300 overflow-hidden">
      {/* HEADER */}
      <div className="bg-white/80 dark:bg-slate-900/50 border-b border-slate-200 dark:border-white/5 sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-[1800px] mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button 
              onClick={handleBack} 
              title="Înapoi"
              className="p-2.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl border border-slate-200 dark:border-white/10 group transition-all"
            >
              <ChevronLeft className="w-5 h-5 text-slate-500 dark:text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white" />
            </button>
            <div 
              onClick={() => router.push('/')}
              title="Mergi la Panoul Principal"
              className="flex items-center gap-4 cursor-pointer hover:opacity-80 transition-opacity"
            >
              <div className="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20"><Shield className="w-5 h-5 text-white" /></div>
              <div><h1 title="Codat (prost) de Gemini ✨ si cfp90" className="cursor-help text-sm font-black text-slate-900 dark:text-white uppercase leading-none italic tracking-tighter">DocAI v0.7.0 BETA</h1></div>
            </div>
            <div className="h-10 w-[1px] bg-slate-200 dark:bg-white/10" />
            <h1 className="text-xl font-black text-slate-900 dark:text-white uppercase truncate max-w-md italic">{caseInfo?.name || 'Încărcare...'}</h1>
          </div>
          <div className="flex items-center gap-2.5">
            <button 
              onClick={toggleTheme}
              className="w-9 h-9 flex items-center justify-center bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl text-slate-600 dark:text-slate-400 transition-all border border-slate-200 dark:border-white/5 shrink-0"
              title="Comutare temă"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div className="hidden xl:flex items-center gap-2 px-3 h-9 bg-blue-500/10 border border-blue-500/20 rounded-xl shrink-0">
              <Brain className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
              <span className="text-[11px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest leading-none">{activeModel}</span>
            </div>
            <button 
              onClick={handleDownloadReport}
              className="flex items-center gap-2 px-3.5 h-9 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-xl text-rose-600 dark:text-rose-400 text-xs font-bold transition-all shrink-0"
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
            }} className="flex items-center gap-2 px-3.5 h-9 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 rounded-xl text-indigo-600 dark:text-indigo-400 text-xs font-bold transition-all shrink-0">
              <Database className="w-4 h-4" /> Harta Relații
            </button>
            <button onClick={() => setShowBriefing(true)} className="flex items-center gap-2 px-3.5 h-9 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl text-blue-600 dark:text-blue-400 text-xs font-bold transition-all shrink-0">
              <Brain className="w-4 h-4" /> Briefing
            </button>
            <button 
              onClick={() => { Cookies.remove('token'); Cookies.remove('role'); router.push('/login'); }}
              className="flex items-center gap-2 px-3.5 h-9 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl text-red-600 dark:text-red-400 text-xs font-bold transition-all shrink-0"
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
                        <div 
                          key={i} 
                          onClick={() => openCitationPreview(cite)} 
                          className="p-2.5 bg-blue-500/5 border-l-2 border-blue-500 rounded-r-lg text-[11px] text-slate-500 dark:text-slate-400 italic cursor-pointer hover:bg-blue-500/10 transition-all flex justify-between items-center group/cite"
                        >
                          <div className="flex items-center gap-2 overflow-hidden mr-2">
                            <span className="not-italic font-black text-[9px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 shrink-0">
                              REF {cite.id}
                            </span>
                            <span className="line-clamp-2">"{cite.content || ''}"</span>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0 opacity-0 group-hover/cite:opacity-100 transition-opacity">
                            {cite.spatial && (
                              <span title="Grounding Spațial Detectat">
                                <Crosshair className="w-3.5 h-3.5 text-blue-500" />
                              </span>
                            )}
                            <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover/cite:text-blue-500" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
            })}

            {/* Indicator investigație activă în fundal (supraviețuire la refresh / tab închis) */}
            {!streamingMessage && backgroundChatStatus?.is_running && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-3xl p-5 bg-white dark:bg-slate-900 border-2 border-amber-500/30 shadow-2xl relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-amber-500/10 overflow-hidden">
                     <div className="h-full bg-amber-500 animate-pulse" style={{ width: '100%' }}></div>
                  </div>
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest flex items-center gap-2">
                      <Loader2 className="w-3 h-3 animate-spin" /> Investigație activă pe server...
                    </p>
                    <button 
                      onClick={async () => {
                        try {
                          await api.post(`/cases/${caseId}/chat/stop`);
                        } catch (e) {
                          console.error("Failed to stop chat:", e);
                        }
                        setBackgroundChatStatus(null);
                        api.get(`/cases/${caseId}/chat`).then(cRes => setMessages(cRes.data));
                      }}
                      className="px-2 py-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg text-[9px] font-black text-red-500 uppercase transition-all flex items-center gap-1"
                    >
                      <Square className="w-2 h-2 fill-current" /> Stop
                    </button>
                  </div>
                  <div className="text-xs text-slate-700 dark:text-slate-300 font-medium py-1.5 flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-amber-500 animate-ping shrink-0" />
                    <span>{backgroundChatStatus.step || "Analiză în curs de desfășurare pe server..."}</span>
                  </div>
                  <p className="text-[10px] text-slate-400 dark:text-slate-500 italic mt-1">
                    Procesul rulează pe server chiar dacă schimbi pagina sau dai refresh. Rezultatul va fi afișat automat aici când este gata.
                  </p>
                </div>
              </div>
            )}

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
                        try {
                          await api.post(`/cases/${caseId}/chat/stop`);
                        } catch (e) {
                          console.error("Failed to stop chat:", e);
                        }
                        setIsChatLoading(false);
                        setStreamingMessage(null);
                        setBackgroundChatStatus(null);
                        api.get(`/cases/${caseId}/chat`).then(cRes => setMessages(cRes.data));
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
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleAsk();
                  }
                }}
                rows={1}
                placeholder="Interoghează dosarul... (Enter pentru trimitere, Shift+Enter pentru linie nouă)"
                className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-white/10 rounded-2xl pl-6 pr-48 py-4 text-sm font-medium text-slate-900 dark:text-white focus:outline-none focus:border-blue-500/50 transition-all shadow-sm resize-none min-h-[58px] max-h-[160px] leading-relaxed"
              />
              <button
                type="submit"
                disabled={isChatLoading || !question.trim()}
                className="absolute right-3 top-2.5 bottom-2.5 px-6 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-xs font-black uppercase transition-all flex items-center gap-2 text-white shadow-sm"
              >
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
        {/* PREVIEW PANEL (FIXED) */}
        {evidencePreview && (() => {
          const ext = (evidencePreview.filename || '').split('.').pop()?.toLowerCase() || '';
          const isPdf = ext === 'pdf' || evidencePreview.docType?.toLowerCase() === 'pdf';
          const isImage = ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff', 'gif', 'svg'].includes(ext) || ['image', 'jpeg', 'png'].includes(evidencePreview.docType?.toLowerCase() || '');
          const isWord = ['doc', 'docx', 'rtf', 'odt'].includes(ext) || ['word', 'docx', 'doc'].includes(evidencePreview.docType?.toLowerCase() || '');

          const pdfSearchParam = evidencePreview.highlight ? `&search=${encodeURIComponent(evidencePreview.highlight)}` : '';
          const pdfViewerUrl = `${evidencePreview.url}#page=${evidencePreview.page}&zoom=page-width${pdfSearchParam}`;

          return (
            <div className="fixed top-20 right-0 bottom-0 w-[780px] max-w-[90vw] bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-white/10 flex flex-col shadow-2xl z-[60] animate-in slide-in-from-right duration-300">
              {/* Header */}
              <div className="p-4 px-5 border-b border-slate-200 dark:border-white/5 flex items-center justify-between bg-slate-50 dark:bg-slate-950 shrink-0">
                <div className="flex items-center gap-3 overflow-hidden">
                  <div className={`p-2 rounded-xl shrink-0 ${
                    isPdf ? 'bg-red-600 text-white' : 
                    isImage ? 'bg-emerald-600 text-white' : 
                    isWord ? 'bg-blue-600 text-white' : 
                    'bg-slate-700 text-white'
                  }`}>
                    {isPdf ? <FileText className="w-5 h-5" /> : 
                     isImage ? <ImageIcon className="w-5 h-5" /> : 
                     <ScrollText className="w-5 h-5" />}
                  </div>
                  <div className="overflow-hidden">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-black text-slate-900 dark:text-slate-200 uppercase tracking-widest truncate">
                        {evidencePreview.filename || 'Document Forensic'}
                      </span>
                      <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase ${
                        isPdf ? 'bg-red-500/10 text-red-600 dark:text-red-400' :
                        isImage ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
                        isWord ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' :
                        'bg-slate-500/10 text-slate-600 dark:text-slate-400'
                      }`}>
                        {ext.toUpperCase() || 'DOC'}
                      </span>
                    </div>
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter block truncate">
                      {isPdf ? `Pagina ${evidencePreview.page}` : (isImage ? 'Scan / Imagine' : 'Reader View')} • Dosar {caseId}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {/* Zoom controls for Image */}
                  {isImage && (
                    <div className="flex items-center bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl p-0.5 shadow-sm mr-1">
                      <button 
                        onClick={() => setImageZoom(z => Math.max(0.4, z - 0.25))}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-500 transition-colors"
                        title="Zoom Out"
                      >
                        <ZoomOut className="w-3.5 h-3.5" />
                      </button>
                      <span className="text-[10px] font-mono font-bold px-2 text-slate-600 dark:text-slate-300">
                        {Math.round(imageZoom * 100)}%
                      </span>
                      <button 
                        onClick={() => setImageZoom(z => Math.min(3, z + 0.25))}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-500 transition-colors"
                        title="Zoom In"
                      >
                        <ZoomIn className="w-3.5 h-3.5" />
                      </button>
                      <button 
                        onClick={() => setImageZoom(1)}
                        className="text-[9px] font-bold px-1.5 py-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded text-slate-400 uppercase"
                        title="Reset Zoom"
                      >
                        100%
                      </button>
                    </div>
                  )}

                  {/* Download original or open tab */}
                  <a
                    href={isPdf ? pdfViewerUrl : evidencePreview.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-slate-500 hover:text-blue-500 transition-all shadow-sm flex items-center gap-1.5 text-xs font-bold"
                    title="Deschide fișierul original în filă nouă"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                  <button 
                    onClick={() => setEvidencePreview(null)} 
                    className="p-2.5 hover:bg-red-500/10 rounded-full text-slate-500 hover:text-red-500 transition-colors"
                    title="Închide previzualizarea"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>
              </div>

              {/* Main Body */}
              <div className="flex-1 bg-slate-100 dark:bg-slate-950 relative overflow-hidden flex flex-col">
                {/* PDF VIEW */}
                {isPdf && (
                  <div className="w-full h-full relative">
                    {pdfLoading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-slate-900/80 z-10">
                        <Loader2 className="w-8 h-8 text-yellow-500 animate-spin" />
                      </div>
                    )}
                    <iframe
                      key={pdfViewerUrl}
                      src={pdfViewerUrl}
                      className="w-full h-full border-0"
                      title="PDF Preview"
                      onLoad={() => setPdfLoading(false)}
                    />
                  </div>
                )}

                {/* IMAGE VIEW */}
                {isImage && (
                  <div className="w-full h-full overflow-auto p-6 flex items-center justify-center bg-slate-900/90 custom-scrollbar">
                    <div className="relative inline-block transition-transform duration-150" style={{ transform: `scale(${imageZoom})`, transformOrigin: 'center center' }}>
                      <img 
                        src={evidencePreview.url} 
                        alt={evidencePreview.filename || 'Document Image'} 
                        className="max-w-full max-h-[75vh] object-contain rounded-xl shadow-2xl border border-white/10"
                      />
                      {evidencePreview.spatial && (
                        <div className="absolute top-2 left-2 px-2.5 py-1 bg-blue-600/90 text-white text-[9px] font-mono font-bold rounded-lg backdrop-blur-sm shadow-lg flex items-center gap-1.5">
                          <Crosshair className="w-3 h-3 text-cyan-300" /> Coordonate: {evidencePreview.spatial}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* WORD / TEXT / NON-PDF READER VIEW */}
                {!isPdf && !isImage && (
                  <div className="w-full h-full overflow-y-auto p-8 custom-scrollbar bg-slate-50 dark:bg-slate-950">
                    {docContentData.loading ? (
                      <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-400">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                        <span className="text-xs font-bold uppercase tracking-wider">Se încarcă textul documentului...</span>
                      </div>
                    ) : docContentData.error ? (
                      <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-500 text-xs">
                        {docContentData.error}
                      </div>
                    ) : docContentData.rawText ? (
                      <div className="max-w-3xl mx-auto bg-white dark:bg-slate-900 p-8 rounded-2xl border border-slate-200 dark:border-white/10 shadow-lg space-y-4 font-sans text-slate-800 dark:text-slate-200">
                        <div className="border-b border-slate-200 dark:border-white/10 pb-4 mb-4 flex justify-between items-center">
                          <div>
                            <h3 className="text-sm font-black uppercase tracking-wider text-slate-900 dark:text-white">
                              {evidencePreview.filename}
                            </h3>
                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                              Reader Text Forensic • {isWord ? 'Document Word' : 'Document Text'}
                            </span>
                          </div>
                          <a 
                            href={evidencePreview.url} 
                            download
                            className="px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-600 dark:text-blue-400 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
                          >
                            <Download className="w-3.5 h-3.5" /> Descarcă original
                          </a>
                        </div>
                        {renderDocReaderContent(docContentData.rawText, evidencePreview.highlight || evidencePreview.text)}
                      </div>
                    ) : (
                      <div className="max-w-3xl mx-auto bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-white/10 text-center text-slate-400 text-xs">
                        Nu există text extras disponibil pentru acest document.
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* FOOTER: Fragment Evidențiat */}
              {evidencePreview.text && (
                <div className="p-5 bg-white dark:bg-slate-950 border-t-2 border-yellow-400/50 shadow-2xl shrink-0">
                  <div className="flex items-center justify-between mb-2.5">
                    <h4 className="text-[10px] font-black text-yellow-600 dark:text-yellow-400 uppercase tracking-[0.2em] flex items-center gap-2">
                      <ScrollText className="w-4 h-4" /> Fragment Extras din Document
                    </h4>
                    <div className="flex items-center gap-2">
                      {evidencePreview.highlight && (
                        <span className="text-[9px] font-black px-2 py-0.5 rounded-full bg-yellow-400/20 text-yellow-700 dark:text-yellow-300 border border-yellow-400/30 uppercase tracking-wider">
                          Focalizare: {evidencePreview.highlight}
                        </span>
                      )}
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(evidencePreview.text);
                          setCopiedEvidence(true);
                          setTimeout(() => setCopiedEvidence(false), 2000);
                        }}
                        className="text-[9px] font-bold text-slate-400 hover:text-yellow-600 dark:hover:text-yellow-400 uppercase tracking-wider transition-colors flex items-center gap-1"
                      >
                        {copiedEvidence ? <><Check className="w-3 h-3 text-emerald-500" /> Copiat!</> : <><Copy className="w-3 h-3" /> Copiază</>}
                      </button>
                    </div>
                  </div>
                  <div className="bg-yellow-50 dark:bg-yellow-500/5 p-4 rounded-xl border-2 border-yellow-400/60 dark:border-yellow-500/30 relative shadow-[0_0_20px_rgba(250,204,21,0.15)]">
                    <div className="absolute top-0 left-0 w-1.5 h-full bg-yellow-400 rounded-l-xl"></div>
                    <p className="text-xs text-slate-800 dark:text-slate-200 font-medium leading-relaxed pl-2 whitespace-pre-wrap">
                      {renderHighlightedSnippet(evidencePreview.text, evidencePreview.highlight)}
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>

      {/* GRAPH MODAL */}
      {showGraph && (
        <div className="fixed inset-0 z-[100] bg-slate-950/95 backdrop-blur-md flex flex-col animate-in fade-in duration-300 overflow-hidden h-screen w-screen">
          <div className="p-4 border-b border-white/10 flex justify-between items-center bg-slate-900">
            <h2 className="text-white font-bold uppercase tracking-tight text-sm flex items-center gap-2">
              <Database className="w-4 h-4 text-indigo-400" /> Analiză Suveică
            </h2>
            <div className="flex items-center gap-2.5">
              <div className="relative group">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
                <input value={graphSearch} onChange={e => setGraphSearch(e.target.value)} placeholder="Caută în hartă..." className="bg-slate-950 border border-white/10 rounded-lg pl-8 pr-2 py-1 text-[9px] w-40 focus:border-blue-500 outline-none transition-all text-white" />
              </div>
              <button 
                onClick={() => graphRef.current?.zoomToFit(400, 60)} 
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-[9px] font-black uppercase tracking-wider flex items-center gap-1 shadow-sm transition-all"
                title="Recentrează și încadrează tot graful"
              >
                <Crosshair className="w-3 h-3" /> Recentrează
              </button>
              <button onClick={handleFindLeader} disabled={isAnalyzing} className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-[9px] font-black uppercase transition-all">Lider</button>
              <button onClick={handleDetectCartel} disabled={isAnalyzing} className="px-3 py-1.5 bg-fuchsia-500/10 hover:bg-fuchsia-500/20 text-fuchsia-400 border border-fuchsia-500/20 rounded-lg text-[9px] font-black uppercase transition-all">Cartel</button>
              <input value={pathSource} onChange={e => setPathSource(e.target.value)} placeholder="Sursă" className="bg-slate-950 border border-white/10 rounded-lg px-2 py-1 text-[9px] w-20 focus:border-indigo-500 outline-none text-white" />
              <input value={pathTarget} onChange={e => setPathTarget(e.target.value)} placeholder="Destinație" className="bg-slate-950 border border-white/10 rounded-lg px-2 py-1 text-[9px] w-20 focus:border-indigo-500 outline-none text-white" />
              <button onClick={handleShortestPath} className="p-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white transition-all" title="Traseu cel mai scurt"><Route className="w-3.5 h-3.5 text-white"/></button>
              <button onClick={() => { setHighlightNodes(new Set()); setHighlightLinks(new Set()); setSelectedNode(null); setHoverNode(null); setNodeColors({}); setNodeVals({}); }} className="p-2 hover:bg-white/10 rounded-full text-slate-400 transition-colors" title="Resetează selecția"><RotateCcw className="w-4 h-4" /></button>
              <button onClick={() => setShowGraph(false)} className="p-2 hover:bg-white/10 rounded-full text-slate-400 transition-colors" title="Închide graful"><X className="w-6 h-6" /></button>
            </div>
          </div>
          
          <div className="flex-1 relative bg-slate-950 overflow-hidden" onClick={() => handleNodeClick(null)}>
            <ForceGraph2D 
              ref={graphRef} 
              graphData={filteredData} 
              nodeLabel="name" 
              width={typeof window !== 'undefined' ? window.innerWidth : 1200}
              height={typeof window !== 'undefined' ? window.innerHeight - 80 : 800}
              warmupTicks={70}
              cooldownTicks={120}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              onNodeClick={(node, e) => { e.stopPropagation(); handleNodeClick(node); }}
              onNodeHover={node => setHoverNode(node)}
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
                return 'rgba(255,255,255,0.2)';
              }}
              linkWidth={link => highlightLinks.has(link) ? 3 : 1.2}
              linkDirectionalParticles={link => highlightLinks.has(link) ? 6 : 0}
              nodeCanvasObjectMode={node => {
                const isHovered = hoverNode && hoverNode.id === node.id;
                const isSelected = selectedNode && selectedNode.id === node.id;
                const isNeighbor = highlightNodes.size > 0 && highlightNodes.has(node.id);
                const isSearchMatch = Boolean(graphSearch && (node as any).name?.toLowerCase().includes(graphSearch.toLowerCase()));
                if (isHovered || isSelected || isNeighbor || isSearchMatch) return 'after';
                return undefined;
              }}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                const label = node.name || node.valoare || node.filename || node.id || "Necunoscut";
                const isSelected = selectedNode && selectedNode.id === node.id;
                const isHovered = hoverNode && hoverNode.id === node.id;
                
                const displayLabel = (isSelected || isHovered) 
                  ? label 
                  : (label.length > 24 ? label.slice(0, 22) + '...' : label);

                const fontSize = Math.max(9, Math.min(13, 12 / globalScale));
                ctx.font = `600 ${fontSize}px Inter, sans-serif`;
                
                const textWidth = ctx.measureText(displayLabel).width;
                const boudingRadius = Math.log2((nodeVals[node.id] || (node as any).val || 5) + 1) * 3 + 2;
                const paddingX = 6;
                const paddingY = 2.5;
                const rectX = node.x - textWidth / 2 - paddingX;
                const rectY = node.y + boudingRadius + 3;
                const rectWidth = textWidth + paddingX * 2;
                const rectHeight = fontSize + paddingY * 2;
                const radius = 4;

                // Pill background badge
                ctx.fillStyle = isSelected 
                  ? 'rgba(79, 70, 229, 0.95)' 
                  : (isHovered ? 'rgba(30, 41, 59, 0.95)' : 'rgba(15, 23, 42, 0.9)');
                ctx.strokeStyle = isSelected 
                  ? 'rgba(199, 210, 254, 0.9)' 
                  : (isHovered ? 'rgba(99, 102, 241, 0.8)' : 'rgba(255, 255, 255, 0.2)');
                ctx.lineWidth = 1;
                
                ctx.beginPath();
                if (typeof (ctx as any).roundRect === 'function') {
                  (ctx as any).roundRect(rectX, rectY, rectWidth, rectHeight, radius);
                } else {
                  ctx.rect(rectX, rectY, rectWidth, rectHeight);
                }
                ctx.fill();
                ctx.stroke();

                // Text
                ctx.fillStyle = isSelected ? '#ffffff' : (isHovered ? '#93c5fd' : 'rgba(255, 255, 255, 0.95)');
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(displayLabel, node.x, rectY + rectHeight / 2);
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
