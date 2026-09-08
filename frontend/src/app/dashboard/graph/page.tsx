'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import dynamic from 'next/dynamic';
import { 
  Shield, Share2, ChevronLeft, Loader2, Database, X, Users, Crosshair, Route, Search, LogOut
} from 'lucide-react';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export default function GlobalGraph() {
  const router = useRouter();
  const graphRef = useRef<any>();
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [timeline, setTimeline] = useState<any[]>([]);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [filteredData, setFilteredData] = useState({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  const token = Cookies.get('token');
  const [highlightNodes, setHighlightNodes] = useState<Set<any>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<any>>(new Set());
  const [nodeColors, setNodeColors] = useState<Record<string, string>>({});
  const [nodeVals, setNodeVals] = useState<Record<string, number>>({});
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [pathSource, setPathSource] = useState('');
  const [pathTarget, setPathTarget] = useState('');
  const [cloneCui, setCloneCui] = useState('');

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    const fetchData = async () => {
      try {
        const [graphRes, timelineRes] = await Promise.all([
          api.get('/system/graph'),
          api.get('/cases/6/timeline').catch(() => ({ data: [] }))
        ]);
        setGraphData(graphRes.data || { nodes: [], links: [] });
        const tlData = (timelineRes.data && timelineRes.data.length > 0) ? timelineRes.data : [
            {date: '2026-01-01', title: 'Origine Dosar', type: 'INFO'},
            {date: '2026-04-22', title: 'Stadiu Curent', type: 'INFO'}
        ];
        setTimeline(tlData);
        setCurrentTimeIndex(tlData.length - 1);
      } catch (err) {
        console.error("Error fetching data", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [token, router]);

  // Logică de filtrare cronologică
  useEffect(() => {
    if (timeline.length === 0 || graphData.nodes.length === 0) {
      setFilteredData(graphData);
      return;
    }

    const maxDate = timeline[currentTimeIndex]?.date;
    if (!maxDate) return;

    // TODO: Aici am putea filtra nodurile care au 'last_seen' dupa maxDate
    // Pentru inceput, aratam tot, dar pregatim infrastructura
    setFilteredData(graphData);
  }, [currentTimeIndex, timeline, graphData]);

  const resetStyles = useCallback(() => {
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
    setNodeColors({});
    setNodeVals({});
  }, []);

  // --- ANALYTICS ACTIONS ---

  const handleFindLeader = async () => {
    setIsAnalyzing(true);
    resetStyles();
    try {
      const res = await api.get('/system/graph/analytics/leader');
      const scores = res.data;
      const newVals: Record<string, number> = {};
      const newColors: Record<string, string> = {};
      
      let maxScore = 0;
      let leaderId = '';

      Object.entries(scores).forEach(([id, score]) => {
        const s = score as number;
        newVals[id] = 5 + (s * 3); // Exponențial vizual
        if (s > maxScore) { maxScore = s; leaderId = id; }
      });

      if (leaderId) {
        newColors[leaderId] = '#ef4444'; // Roșu aprins pentru lider
        const leaderNode = graphData.nodes.find((n: any) => n.id === leaderId) as any;
        if (leaderNode) graphRef.current?.centerAt(leaderNode.x, leaderNode.y, 1000);
      }

      setNodeVals(newVals);
      setNodeColors(newColors);
    } catch (err) { alert("Eroare PageRank"); }
    finally { setIsAnalyzing(false); }
  };

  const handleDetectCartel = async () => {
    setIsAnalyzing(true);
    resetStyles();
    try {
      const res = await api.get('/system/graph/analytics/cartel');
      const communities = res.data;
      const newColors: Record<string, string> = {};
      
      // Generare culori unice per comunitate
      const colors = ['#f43f5e', '#a855f7', '#8b5cf6', '#3b82f6', '#14b8a6', '#f59e0b'];
      
      Object.entries(communities).forEach(([id, commId]) => {
        newColors[id] = colors[(commId as number) % colors.length];
      });

      setNodeColors(newColors);
    } catch (err) { alert("Eroare Louvain"); }
    finally { setIsAnalyzing(false); }
  };

  const handleShortestPath = async () => {
    if (!pathSource || !pathTarget) return alert("Introdu ambele noduri.");
    setIsAnalyzing(true);
    resetStyles();
    try {
      const res = await api.get(`/system/graph/analytics/path?source_name=${pathSource}&target_name=${pathTarget}`);
      const pathNodes = res.data.nodes;
      
      if (pathNodes.length === 0) return alert("Nu există traseu direct.");

      const newHighlights = new Set(pathNodes);
      setHighlightNodes(newHighlights);
    } catch (err) { alert("Eroare Shortest Path"); }
    finally { setIsAnalyzing(false); }
  };

  const handleFindClones = async () => {
    if (!cloneCui) return alert("Introdu CUI Suspect.");
    setIsAnalyzing(true);
    resetStyles();
    try {
      const res = await api.get(`/system/graph/analytics/clones?cui=${cloneCui}`);
      const clones = res.data.clones;
      
      if (clones.length === 0) return alert("Nu s-au găsit clone (adrese/tipare comune).");

      const newHighlights = new Set();
      const newColors: Record<string, string> = {};
      
      clones.forEach((c: any) => {
        newHighlights.add(c.suspect_id);
        newHighlights.add(c.clone_id);
        newColors[c.suspect_id] = '#ef4444';
        newColors[c.clone_id] = '#f59e0b';
      });

      setHighlightNodes(newHighlights);
      setNodeColors(newColors);
    } catch (err) { alert("Eroare Node Similarity"); }
    finally { setIsAnalyzing(false); }
  };

  // --- RENDERING ---
  
  if (isLoading) return <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4"><Loader2 className="w-12 h-12 text-indigo-500 animate-spin" /><p className="text-sm font-black text-indigo-400 uppercase tracking-widest">Sincronizare GDS...</p></div>;

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-200 flex flex-col font-sans relative overflow-hidden">
      {/* HEADER */}
      <div className="bg-slate-900 border-b border-white/5 p-6 z-50">
        <div className="max-w-[1800px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-6">
            <button onClick={() => router.push('/dashboard')} className="p-2.5 hover:bg-white/5 rounded-xl transition-all border border-transparent hover:border-white/10 group">
              <ChevronLeft className="w-5 h-5 text-slate-400 group-hover:text-white" />
            </button>
            <div className="h-10 w-[1px] bg-white/10" />
            <div>
              <h1 className="text-xl font-black text-white tracking-tight uppercase flex items-center gap-3">
                <Share2 className="w-6 h-6 text-indigo-400" />
                GDS Analytics - Suveică Globală
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={resetStyles} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-black uppercase tracking-widest rounded-xl transition-colors">Reset Vizualizare</button>
            <button 
              onClick={() => { Cookies.remove('token'); Cookies.remove('role'); router.push('/login'); }} 
              className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl text-red-400 text-xs font-black uppercase tracking-widest transition-all"
              title="Deconectare din cont"
            >
              <LogOut className="w-4 h-4" /> Ieșire
            </button>
          </div>
        </div>
      </div>

      {/* TOOLBAR ANTIFRAUDA (Glassmorphism) */}
      <div className="absolute top-28 left-8 z-40 w-80 bg-slate-900/80 backdrop-blur-xl border border-white/10 rounded-3xl p-6 shadow-2xl">
        <h3 className="text-xs font-black text-indigo-400 uppercase tracking-widest mb-6 flex items-center gap-2">
          <Crosshair className="w-4 h-4" /> Instrumente Antifraudă
        </h3>
        
        <div className="space-y-6">
          {/* Lider */}
          <button onClick={handleFindLeader} disabled={isAnalyzing} className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-indigo-500/20 border border-transparent hover:border-indigo-500/30 rounded-xl transition-all group">
            <span className="text-xs font-bold text-slate-300 group-hover:text-indigo-300">Găsește Liderul</span>
            <Users className="w-4 h-4 text-slate-500 group-hover:text-indigo-400" />
          </button>

          {/* Cartel */}
          <button onClick={handleDetectCartel} disabled={isAnalyzing} className="w-full flex items-center justify-between p-3 bg-white/5 hover:bg-fuchsia-500/20 border border-transparent hover:border-fuchsia-500/30 rounded-xl transition-all group">
            <span className="text-xs font-bold text-slate-300 group-hover:text-fuchsia-300">Detectează Cartel</span>
            <Database className="w-4 h-4 text-slate-500 group-hover:text-fuchsia-400" />
          </button>

          {/* Shortest Path */}
          <div className="p-4 bg-black/30 rounded-xl border border-white/5 space-y-3">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Traseu (Shortest Path)</p>
            <input value={pathSource} onChange={e => setPathSource(e.target.value)} placeholder="Nume Sursă..." className="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500" />
            <input value={pathTarget} onChange={e => setPathTarget(e.target.value)} placeholder="Nume Destinație..." className="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500" />
            <button onClick={handleShortestPath} disabled={isAnalyzing} className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-[10px] font-black uppercase tracking-widest transition-colors flex justify-center items-center gap-2">
              <Route className="w-3 h-3" /> Găsește Traseul
            </button>
          </div>

          {/* Clones */}
          <div className="p-4 bg-black/30 rounded-xl border border-white/5 space-y-3">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Clone (Node Similarity)</p>
            <input value={cloneCui} onChange={e => setCloneCui(e.target.value)} placeholder="CUI Suspect..." className="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500" />
            <button onClick={handleFindClones} disabled={isAnalyzing} className="w-full py-2 bg-amber-600 hover:bg-amber-500 rounded-lg text-[10px] font-black uppercase tracking-widest transition-colors flex justify-center items-center gap-2">
              <Search className="w-3 h-3" /> Găsește Clonele
            </button>
          </div>
        </div>
      </div>
      {/* GRAPH AREA */}
      <div className="flex-1 relative bg-slate-950 overflow-hidden border-4 border-indigo-500/10">
        <div className="absolute top-6 left-1/2 -translate-x-1/2 z-50">
            <button 
                onClick={() => graphRef.current?.zoomToFit(400)}
                className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 border border-white/20 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all shadow-[0_0_30px_rgba(79,70,229,0.4)]"
            >
                Recentrează Probele
            </button>
        </div>

        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeLabel="name"
          width={typeof window !== 'undefined' ? window.innerWidth : 1000}
          height={typeof window !== 'undefined' ? window.innerHeight - 80 : 600}

          // Dynamic Colors (Louvain / Default / Highlight)
          nodeColor={node => {
            if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) return 'rgba(255,255,255,0.05)';
            return nodeColors[node.id as string] || (node as any).color;
          }}
          // Dynamic Value (PageRank) - Normalizare Logaritmică pentru a evita "bulinele imense"
          nodeVal={node => {
            const rawVal = nodeVals[node.id as string] || (node as any).val || 5;
            return Math.log2(rawVal + 1) * 3 + 2; // Scalare echilibrată
          }}
          
          linkDirectionalParticles={highlightNodes.size > 0 ? 0 : 4}
          linkDirectionalParticleSpeed={0.005}
          linkColor={link => {
            const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source;
            const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target;
            if (highlightNodes.size > 0) {
              if (highlightNodes.has(sourceId) && highlightNodes.has(targetId)) return 'rgba(99, 102, 241, 1)'; // Indigo aprins
              return 'rgba(255,255,255,0.02)';
            }
            return 'rgba(255, 255, 255, 0.35)'; // Mult mai vizibil (35% opacitate)
          }}
          linkWidth={link => {
            const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source;
            const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target;
            if (highlightNodes.size > 0 && highlightNodes.has(sourceId) && highlightNodes.has(targetId)) return 3;
            return 1.5; // Linii mai groase
          }}
          nodeCanvasObjectMode={() => 'after'}
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            // Nu afișăm label-uri dacă suntem la zoom out mare (performance + clarity)
            if (globalScale < 1.2 && highlightNodes.size === 0) return;
            
            // Nu scriem text pentru nodurile estompate în mod analiză
            if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) return;

            const label = node.name;
            const fontSize = 14 / globalScale;
            ctx.font = `${fontSize}px Inter, Sans-Serif`;
            
            if (nodeColors[node.id]) {
              ctx.shadowColor = nodeColors[node.id];
              ctx.shadowBlur = 10;
            }

            ctx.fillStyle = 'rgba(255,255,255,0.85)';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            
            // Poziționăm textul sub bulină
            const boudingRadius = Math.log2((nodeVals[node.id] || (node as any).val || 5) + 1) * 3 + 2;
            ctx.fillText(label, node.x, node.y + boudingRadius + 1);
            ctx.shadowBlur = 0;
          }}
        />
      </div>
      {/* TIMELINE MACHINE (Right Control) */}
      {timeline.length > 0 && (
        <div className="fixed top-32 right-8 z-[100] w-96 bg-slate-900 border-2 border-indigo-500/30 rounded-[2rem] p-6 shadow-[0_0_60px_rgba(0,0,0,0.8)]">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-indigo-600 rounded-xl">
                <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
                <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">Chronos v1.0</p>
                <p className="text-sm font-bold text-white tracking-tight">Time Machine</p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-black/40 rounded-2xl p-4 border border-white/5">
                <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Punct Temporal Selectat</p>
                <p className="text-xs font-bold text-indigo-300 mb-1">{timeline[currentTimeIndex]?.date}</p>
                <p className="text-[11px] text-white font-medium line-clamp-2">{timeline[currentTimeIndex]?.title}</p>
            </div>

            <div className="px-2">
                <input 
                    type="range" 
                    min="0" 
                    max={timeline.length - 1} 
                    value={currentTimeIndex} 
                    onChange={(e) => setCurrentTimeIndex(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
            </div>

            <div className="flex justify-between items-center text-[8px] font-black text-slate-500 uppercase tracking-tighter">
                <span>{timeline[0]?.date}</span>
                <span className="px-2 py-0.5 bg-indigo-500/10 rounded-md text-indigo-400">{currentTimeIndex + 1} / {timeline.length}</span>
                <span>{timeline[timeline.length-1]?.date}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
