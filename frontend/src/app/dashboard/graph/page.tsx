'use client';
import { useEffect, useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import api from '../../../lib/api';
import Cookies from 'js-cookie';
import dynamic from 'next/dynamic';
import { 
  Shield, Share2, ChevronLeft, Loader2, Database, X, Users, Crosshair, Route, Search
} from 'lucide-react';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export default function GlobalGraph() {
  const router = useRouter();
  const graphRef = useRef<any>();
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(true);
  
  // Analytics States
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [highlightNodes, setHighlightNodes] = useState(new Set());
  const [highlightLinks, setHighlightLinks] = useState(new Set());
  const [nodeColors, setNodeColors] = useState<Record<string, string>>({});
  const [nodeVals, setNodeVals] = useState<Record<string, number>>({});
  const [pathSource, setPathSource] = useState('');
  const [pathTarget, setPathTarget] = useState('');
  const [cloneCui, setCloneCui] = useState('');

  const token = Cookies.get('token');

  useEffect(() => {
    if (!token) { router.push('/login'); return; }
    const fetchGlobalGraph = async () => {
      try {
        const res = await api.get('/system/graph/global');
        setGraphData(res.data);
      } catch (err) {
        console.error("Error fetching global graph", err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchGlobalGraph();
  }, [token, router]);

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
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col font-sans relative">
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
          <button onClick={resetStyles} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-black uppercase tracking-widest rounded-xl transition-colors">Reset Vizualizare</button>
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
      <div className="flex-1 relative bg-slate-950 overflow-hidden">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeLabel="name"
          // Dynamic Colors (Louvain / Default / Highlight)
          nodeColor={node => {
            if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) return 'rgba(255,255,255,0.05)';
            return nodeColors[node.id as string] || (node as any).color;
          }}
          // Dynamic Value (PageRank)
          nodeVal={node => nodeVals[node.id as string] || (node as any).val || 5}
          
          linkDirectionalParticles={highlightNodes.size > 0 ? 0 : 4}
          linkDirectionalParticleSpeed={0.005}
          linkColor={link => {
            const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source;
            const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target;
            if (highlightNodes.size > 0) {
              if (highlightNodes.has(sourceId) && highlightNodes.has(targetId)) return 'rgba(255,255,255,0.8)';
              return 'rgba(255,255,255,0.02)'; // Estompare trasee irelevante
            }
            return 'rgba(255,255,255,0.1)';
          }}
          linkWidth={link => {
            const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source;
            const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target;
            if (highlightNodes.size > 0 && highlightNodes.has(sourceId) && highlightNodes.has(targetId)) return 3;
            return 1;
          }}
          nodeCanvasObjectMode={() => 'after'}
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            // Nu scriem text pentru nodurile estompate în mod analiză
            if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) return;

            const label = node.name;
            const fontSize = (nodeVals[node.id] ? 18 : 12) / globalScale;
            ctx.font = `${fontSize}px Inter, Sans-Serif`;
            
            // Highlight specific leader or clones
            if (nodeColors[node.id]) {
              ctx.shadowColor = nodeColors[node.id];
              ctx.shadowBlur = 15;
            } else {
              ctx.shadowBlur = 0;
            }

            ctx.fillStyle = 'rgba(255,255,255,0.9)';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(label, node.x, node.y - (node.val || 5) - 2);
            ctx.shadowBlur = 0;
          }}
        />
      </div>
    </div>
  );
}
