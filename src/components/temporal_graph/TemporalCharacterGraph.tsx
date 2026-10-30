import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import {
  TemporalGraphSnapshot,
  TemporalGraphNode,
  TemporalGraphEdge,
  TemporalGraphDiff,
  TemporalGraphEdgeCategory,
} from '../../types';
import { fetchTemporalGraph, fetchTemporalGraphDiff } from '../../api';

interface TemporalCharacterGraphProps {
  projectId: string;
  initialTick?: number;
  onSelectCharacter?: (charId: string) => void;
}

// Extended node type for D3 simulation
interface SimulationNode extends TemporalGraphNode, d3.SimulationNodeDatum {
  x: number;
  y: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

// Extended link type for D3 simulation
interface SimulationLink extends d3.SimulationLinkDatum<SimulationNode> {
  id: string;
  source: SimulationNode | string;
  target: SimulationNode | string;
  data: TemporalGraphEdge;
}

export const TemporalCharacterGraph: React.FC<TemporalCharacterGraphProps> = ({
  projectId,
  initialTick,
  onSelectCharacter,
}) => {
  const [currentTick, setCurrentTick] = useState<number>(initialTick ?? 0);
  const [snapshot, setSnapshot] = useState<TemporalGraphSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Selection states
  const [selectedNode, setSelectedNode] = useState<TemporalGraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<TemporalGraphEdge | null>(null);

  // Filter & Category states
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'canonical' | 'hypothesis'>('all');
  const [nodeTypeFilter, setNodeTypeFilter] = useState<'all' | 'characters' | 'events'>('all');
  const [dimensionFilter, setDimensionFilter] = useState<string>('all');
  const [minConfidence, setMinConfidence] = useState<number>(0.0);

  // Playback states
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const playTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const latestRequestIdRef = useRef<number>(0);

  // Diff comparison states
  const [diffMode, setDiffMode] = useState<boolean>(false);
  const [diffFromTick, setDiffFromTick] = useState<number>(0);
  const [diffToTick, setDiffToTick] = useState<number>(initialTick ?? 0);
  const [diffResult, setDiffResult] = useState<TemporalGraphDiff | null>(null);
  const [loadingDiff, setLoadingDiff] = useState<boolean>(false);

  // D3 force simulation state
  const svgRef = useRef<SVGSVGElement | null>(null);
  const gRef = useRef<SVGGElement | null>(null);
  const simulationRef = useRef<d3.Simulation<SimulationNode, SimulationLink> | null>(null);
  const [simulationNodes, setSimulationNodes] = useState<SimulationNode[]>([]);
  const [simulationLinks, setSimulationLinks] = useState<SimulationLink[]>([]);
  const [, setTickCounter] = useState<number>(0);
  const [isPhysicsPaused, setIsPhysicsPaused] = useState<boolean>(false);
  const zoomTransformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity);

  // Fetch graph snapshot at currentTick
  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();
    const requestId = ++latestRequestIdRef.current;
    setLoading(true);

    fetchTemporalGraph(projectId, currentTick, controller.signal)
      .then((data) => {
        if (isMounted && requestId === latestRequestIdRef.current) {
          setSnapshot(data);
          setError(null);
          // Sync selections
          if (selectedNode) {
            const updatedNode = data.nodes.find((n) => n.id === selectedNode.id);
            setSelectedNode(updatedNode || null);
          }
          if (selectedEdge) {
            const updatedEdge = data.edges.find((e) => e.id === selectedEdge.id);
            setSelectedEdge(updatedEdge || null);
          }
        }
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        if (isMounted && requestId === latestRequestIdRef.current) {
          setError(err.message || 'Failed to load temporal graph');
        }
      })
      .finally(() => {
        if (isMounted && requestId === latestRequestIdRef.current) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [projectId, currentTick]);

  // Handle Playback timer
  useEffect(() => {
    if (isPlaying && snapshot) {
      playTimerRef.current = setInterval(() => {
        setCurrentTick((prev) => {
          if (prev >= snapshot.max_tick) {
            setIsPlaying(false);
            return snapshot.max_tick;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    }
    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, snapshot?.max_tick]);

  // Filtered nodes
  const filteredNodes = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.nodes.filter((node) => {
      if (nodeTypeFilter === 'characters' && node.node_type === 'causal_event') return false;
      if (nodeTypeFilter === 'events' && node.node_type !== 'causal_event') return false;
      return true;
    });
  }, [snapshot, nodeTypeFilter]);

  // Filtered edges
  const filteredEdges = useMemo(() => {
    if (!snapshot) return [];
    const validNodeIds = new Set(filteredNodes.map((n) => n.id));

    return snapshot.edges.filter((edge) => {
      // Must connect visible nodes
      if (!validNodeIds.has(edge.source_id) || !validNodeIds.has(edge.target_id)) {
        return false;
      }

      // Category filter (canonical vs hypothesis)
      const category: TemporalGraphEdgeCategory = edge.edge_category || 'canonical';
      if (categoryFilter === 'canonical' && category !== 'canonical') return false;
      if (categoryFilter === 'hypothesis' && category !== 'analytical_hypothesis') return false;

      // Confidence filter for hypotheses
      if (category === 'analytical_hypothesis' && (edge.confidence || 0) < minConfidence) {
        return false;
      }

      // Dimension/Relationship filter
      if (dimensionFilter === 'all') return true;
      if (dimensionFilter === 'high_intensity') return edge.aggregate_intensity >= 0.5;
      if (dimensionFilter === 'allies') return edge.relationship_type === 'allies';
      if (dimensionFilter === 'hostile') return edge.relationship_type === 'hostile';
      if (dimensionFilter === 'guarded') return edge.relationship_type === 'guarded';
      if (dimensionFilter === 'causal') {
        return edge.edge_kind === 'causal_action' || edge.edge_kind === 'causal_impact' || edge.relationship_type === 'hypothesized_causality';
      }

      const val = edge.dimensions[dimensionFilter];
      return val !== undefined && Math.abs(val) >= 0.3;
    });
  }, [snapshot, filteredNodes, categoryFilter, minConfidence, dimensionFilter]);

  // Setup and run D3 Force Simulation
  useEffect(() => {
    if (!snapshot || filteredNodes.length === 0) {
      setSimulationNodes([]);
      setSimulationLinks([]);
      return;
    }

    const width = 760;
    const height = 520;
    const centerX = width / 2;
    const centerY = height / 2;

    // Preserve existing node coordinates if they already exist, else initialize
    const existingCoords = new Map<string, { x: number; y: number; vx?: number; vy?: number }>();
    simulationNodes.forEach((n) => {
      existingCoords.set(n.id, { x: n.x, y: n.y, vx: n.vx, vy: n.vy });
    });

    const count = filteredNodes.length;
    const initialSimNodes: SimulationNode[] = filteredNodes.map((node, index) => {
      const existing = existingCoords.get(node.id);
      if (existing) {
        return {
          ...node,
          x: existing.x,
          y: existing.y,
          vx: existing.vx,
          vy: existing.vy,
        };
      }
      // Radial distribution initial layout
      const angle = (2 * Math.PI * index) / Math.max(1, count) - Math.PI / 2;
      const radius = node.node_type === 'causal_event' ? 200 : 130;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 20,
        y: centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 20,
      };
    });

    // Map links
    const nodeMap = new Map<string, SimulationNode>(initialSimNodes.map((n) => [n.id, n]));
    const initialSimLinks: SimulationLink[] = [];

    filteredEdges.forEach((edge) => {
      const srcNode = nodeMap.get(edge.source_id);
      const tgtNode = nodeMap.get(edge.target_id);
      if (srcNode && tgtNode) {
        initialSimLinks.push({
          id: edge.id,
          source: srcNode,
          target: tgtNode,
          data: edge,
        });
      }
    });

    // Create D3 Force Simulation
    const simulation = d3
      .forceSimulation<SimulationNode>(initialSimNodes)
      .force(
        'link',
        d3
          .forceLink<SimulationNode, SimulationLink>(initialSimLinks)
          .id((d) => d.id)
          .distance((link) => {
            const kind = link.data.edge_kind;
            if (kind === 'causal_action' || kind === 'causal_impact') return 110;
            if (link.data.edge_category === 'analytical_hypothesis') return 180;
            return 140;
          })
          .strength(0.6)
      )
      .force('charge', d3.forceManyBody<SimulationNode>().strength((d) => (d.node_type === 'causal_event' ? -220 : -380)))
      .force('center', d3.forceCenter(centerX, centerY).strength(0.08))
      .force(
        'collide',
        d3.forceCollide<SimulationNode>().radius((d) => (d.node_type === 'causal_event' ? 36 : 48)).iterations(2)
      );

    simulation.alphaDecay(0.06);

    // Warm-up simulation ticks synchronously so initial snapshot has computed coordinates immediately
    // (Crucial for DOM stability, layout settling, and test assertions)
    for (let i = 0; i < 60; ++i) {
      simulation.tick();
    }

    setSimulationNodes([...initialSimNodes]);
    setSimulationLinks([...initialSimLinks]);

    simulation.on('tick', () => {
      // Settle quickly and stop churning DOM
      if (simulation.alpha() > 0.01) {
        setSimulationNodes([...initialSimNodes]);
        setSimulationLinks([...initialSimLinks]);
        setTickCounter((c) => c + 1);
      }
    });

    simulation.on('end', () => {
      setSimulationNodes([...initialSimNodes]);
      setSimulationLinks([...initialSimLinks]);
    });

    if (isPhysicsPaused) {
      simulation.stop();
    }

    simulationRef.current = simulation;

    return () => {
      simulation.stop();
    };
  }, [snapshot, filteredNodes.length, filteredEdges.length, categoryFilter, minConfidence, dimensionFilter, nodeTypeFilter]);

  // Handle D3 Zoom and Pan
  useEffect(() => {
    if (!svgRef.current || !gRef.current) return;

    const svg = d3.select(svgRef.current);
    const g = d3.select(gRef.current);

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 3.5])
      .on('zoom', (event) => {
        zoomTransformRef.current = event.transform;
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    return () => {
      svg.on('.zoom', null);
    };
  }, []);

  // Zoom control helpers
  const handleZoomIn = () => {
    if (!svgRef.current) return;
    d3.select(svgRef.current).transition().duration(250).call(d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 1.3);
  };

  const handleZoomOut = () => {
    if (!svgRef.current) return;
    d3.select(svgRef.current).transition().duration(250).call(d3.zoom<SVGSVGElement, unknown>().scaleBy as any, 0.7);
  };

  const handleResetZoom = () => {
    if (!svgRef.current) return;
    d3.select(svgRef.current)
      .transition()
      .duration(300)
      .call(d3.zoom<SVGSVGElement, unknown>().transform as any, d3.zoomIdentity);
  };

  const handleTogglePhysics = () => {
    if (!simulationRef.current) return;
    if (isPhysicsPaused) {
      simulationRef.current.alpha(0.3).restart();
      setIsPhysicsPaused(false);
    } else {
      simulationRef.current.stop();
      setIsPhysicsPaused(true);
    }
  };

  // Node Drag Handlers
  const handleNodeMouseDown = (e: React.MouseEvent, node: SimulationNode) => {
    e.stopPropagation();
    if (!simulationRef.current) return;

    const sim = simulationRef.current;
    sim.alphaTarget(0.3).restart();
    node.fx = node.x;
    node.fy = node.y;

    const onMouseMove = (moveEvent: MouseEvent) => {
      if (!svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const transform = zoomTransformRef.current;
      const clientX = moveEvent.clientX - rect.left;
      const clientY = moveEvent.clientY - rect.top;
      node.fx = (clientX - transform.x) / transform.k;
      node.fy = (clientY - transform.y) / transform.k;
    };

    const onMouseUp = () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      if (!isPhysicsPaused) {
        sim.alphaTarget(0);
        node.fx = null;
        node.fy = null;
      }
    };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  // Handle diff compute
  const handleComputeDiff = async () => {
    setLoadingDiff(true);
    try {
      const diff = await fetchTemporalGraphDiff(projectId, diffFromTick, diffToTick);
      setDiffResult(diff);
    } catch (err: any) {
      setError(err.message || 'Failed to compute diff');
    } finally {
      setLoadingDiff(false);
    }
  };

  // Color helper for relationship type and edge category
  const getEdgeStyle = useCallback((edge: TemporalGraphEdge) => {
    const isHypothesis = edge.edge_category === 'analytical_hypothesis';

    if (isHypothesis) {
      return {
        color: '#c084fc', // purple-400
        dashArray: '6,4',
        label: 'HYPOTHESIS',
        badgeBg: 'rgba(88, 28, 135, 0.4)',
        badgeBorder: 'rgba(192, 132, 252, 0.6)',
      };
    }

    if (edge.edge_kind === 'causal_action' || edge.edge_kind === 'causal_impact') {
      return {
        color: '#38bdf8', // sky-400
        dashArray: undefined,
        label: (edge.relationship_type || 'CAUSAL').toUpperCase(),
        badgeBg: 'rgba(8, 145, 178, 0.3)',
        badgeBorder: 'rgba(56, 189, 248, 0.6)',
      };
    }

    switch (edge.relationship_type) {
      case 'allies':
        return {
          color: '#10b981', // emerald-500
          dashArray: undefined,
          label: 'ALLIES',
          badgeBg: 'rgba(6, 78, 59, 0.4)',
          badgeBorder: 'rgba(16, 185, 129, 0.6)',
        };
      case 'hostile':
        return {
          color: '#f43f5e', // rose-500
          dashArray: undefined,
          label: 'HOSTILE',
          badgeBg: 'rgba(136, 19, 55, 0.4)',
          badgeBorder: 'rgba(244, 63, 94, 0.6)',
        };
      case 'guarded':
        return {
          color: '#f59e0b', // amber-500
          dashArray: '4,4',
          label: 'GUARDED',
          badgeBg: 'rgba(120, 53, 15, 0.4)',
          badgeBorder: 'rgba(245, 158, 11, 0.6)',
        };
      case 'conflicted':
        return {
          color: '#a855f7', // purple-500
          dashArray: undefined,
          label: 'CONFLICTED',
          badgeBg: 'rgba(88, 28, 135, 0.4)',
          badgeBorder: 'rgba(168, 85, 247, 0.6)',
        };
      default:
        return {
          color: edge.aggregate_intensity > 0.4 ? '#38bdf8' : '#64748b',
          dashArray: undefined,
          label: (edge.relationship_type || 'NEUTRAL').toUpperCase(),
          badgeBg: 'rgba(30, 41, 59, 0.5)',
          badgeBorder: 'rgba(100, 116, 139, 0.5)',
        };
    }
  }, []);

  const canonicalCount = snapshot?.canonical_edge_count ?? snapshot?.edges.filter((e) => e.edge_category !== 'analytical_hypothesis').length ?? 0;
  const hypothesisCount = snapshot?.hypothesis_edge_count ?? snapshot?.edges.filter((e) => e.edge_category === 'analytical_hypothesis').length ?? 0;
  const causalEventsCount = snapshot?.causal_event_count ?? snapshot?.nodes.filter((n) => n.node_type === 'causal_event').length ?? 0;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col font-sans">
      {/* Top Controls Header */}
      <div className="p-4 bg-slate-950/90 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h3 className="text-base font-bold text-white tracking-wide uppercase">
              Temporal Character-Relationship Graph
            </h3>
            <span className="px-2 py-0.5 text-xs font-mono font-bold rounded bg-cyan-950 text-cyan-300 border border-cyan-800/80">
              Tick {currentTick} / {snapshot?.max_tick ?? 0}
            </span>
            <span className="px-2 py-0.5 text-xs font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
              Schema v{snapshot?.schema_version || '2.1.0'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            D3 force-directed projection distinguishing canonical ground-truth from analytical hypotheses.
          </p>
        </div>

        {/* Action Buttons & Badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Edge Category Counts */}
          <div className="flex items-center gap-1.5 text-xs font-mono">
            <span
              className="px-2 py-1 rounded bg-emerald-950/60 border border-emerald-800/80 text-emerald-300"
              title="Verified in WorldState & EventLog"
            >
              ● {canonicalCount} Canonical
            </span>
            <span
              className="px-2 py-1 rounded bg-purple-950/60 border border-purple-800/80 text-purple-300"
              title="Observer & Narrative Intelligence Inferences"
            >
              ◇ {hypothesisCount} Hypotheses
            </span>
            {causalEventsCount > 0 && (
              <span
                className="px-2 py-1 rounded bg-sky-950/60 border border-sky-800/80 text-sky-300"
                title="Pivotal Historical Events"
              >
                ⚡ {causalEventsCount} Causal Events
              </span>
            )}
          </div>

          <button
            onClick={() => setDiffMode(!diffMode)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              diffMode
                ? 'bg-purple-900/60 border-purple-500 text-purple-200'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-750'
            }`}
          >
            {diffMode ? 'Close Diff Mode' : 'Compare Snapshots (Diff)'}
          </button>
        </div>
      </div>

      {/* Epistemic Schema Bar & Category Toggles */}
      <div className="px-4 py-2.5 bg-slate-950/70 border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Edge Category Radio Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Epistemic Layer:
          </span>
          <div className="inline-flex rounded-lg p-0.5 bg-slate-900 border border-slate-800">
            <button
              onClick={() => setCategoryFilter('all')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                categoryFilter === 'all'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/50'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Edges ({snapshot?.edges.length ?? 0})
            </button>
            <button
              onClick={() => setCategoryFilter('canonical')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition flex items-center gap-1.5 ${
                categoryFilter === 'canonical'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="w-2 h-0.5 bg-emerald-400 rounded-full" />
              Canonical Ground Truth
            </button>
            <button
              onClick={() => setCategoryFilter('hypothesis')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition flex items-center gap-1.5 ${
                categoryFilter === 'hypothesis'
                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="w-2 h-0.5 bg-purple-400 rounded-full border-t border-dashed" />
              Analytical Hypotheses
            </button>
          </div>
        </div>

        {/* Entity Node Type Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Entities:
          </span>
          <div className="inline-flex rounded-lg p-0.5 bg-slate-900 border border-slate-800">
            <button
              onClick={() => setNodeTypeFilter('all')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                nodeTypeFilter === 'all'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Entities
            </button>
            <button
              onClick={() => setNodeTypeFilter('characters')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                nodeTypeFilter === 'characters'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Characters Only
            </button>
            <button
              onClick={() => setNodeTypeFilter('events')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                nodeTypeFilter === 'events'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Causal Events Only
            </button>
          </div>
        </div>

        {/* Confidence Threshold Slider for Hypotheses */}
        {categoryFilter !== 'canonical' && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="font-mono text-[11px]">Min Hypothesis Conf:</span>
            <input
              type="range"
              min={0}
              max={0.95}
              step={0.05}
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              className="w-20 accent-purple-400 h-1 bg-slate-700 rounded cursor-pointer"
            />
            <span className="font-mono text-purple-300 text-xs w-9">
              {Math.round(minConfidence * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* Scrubber Bar */}
      <div className="px-4 py-3 bg-slate-900/90 border-b border-slate-800/80 flex flex-wrap items-center gap-4">
        {/* Playback buttons */}
        <div className="flex items-center gap-1">
          <button
            disabled={currentTick <= 0}
            onClick={() => setCurrentTick((t) => Math.max(0, t - 1))}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs transition"
            title="Step Back"
          >
            ◀
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition"
          >
            {isPlaying ? 'PAUSE' : 'PLAY'}
          </button>
          <button
            disabled={snapshot ? currentTick >= snapshot.max_tick : true}
            onClick={() => setCurrentTick((t) => Math.min(snapshot?.max_tick || 0, t + 1))}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs transition"
            title="Step Forward"
          >
            ▶
          </button>
        </div>

        {/* Timeline Slider */}
        <div className="flex-1 flex items-center gap-3 min-w-[200px]">
          <span className="text-xs font-mono text-slate-400">0</span>
          <input
            type="range"
            min={0}
            max={snapshot?.max_tick || 1}
            value={currentTick}
            onChange={(e) => setCurrentTick(parseInt(e.target.value, 10))}
            className="w-full accent-cyan-400 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
          />
          <span className="text-xs font-mono text-cyan-300 font-bold">{currentTick}</span>
        </div>

        {/* Dimension Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-1">
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Dynamic:</span>
          {[
            { id: 'all', label: 'All Dynamics' },
            { id: 'high_intensity', label: 'High Tension' },
            { id: 'allies', label: 'Allies' },
            { id: 'hostile', label: 'Hostile' },
            { id: 'guarded', label: 'Guarded' },
            { id: 'causal', label: 'Causal Chain' },
            { id: 'suspicion', label: 'Suspicion' },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setDimensionFilter(pill.id)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono transition ${
                dimensionFilter === pill.id
                  ? 'bg-cyan-500/20 border border-cyan-400 text-cyan-300'
                  : 'bg-slate-800/80 border border-slate-700/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {/* Diff Mode Modal / Drawer */}
      {diffMode && (
        <div className="p-4 bg-purple-950/30 border-b border-purple-900/50 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-purple-400" />
              <h4 className="font-bold text-sm text-purple-200 uppercase tracking-wide">
                Temporal Snapshot Differential
              </h4>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">From Tick:</span>
                <input
                  type="number"
                  min={0}
                  max={snapshot?.max_tick || 0}
                  value={diffFromTick}
                  onChange={(e) => setDiffFromTick(parseInt(e.target.value, 10))}
                  className="w-14 px-2 py-1 bg-slate-900 border border-slate-700 rounded text-slate-200 font-mono"
                />
                <span className="text-slate-400">To Tick:</span>
                <input
                  type="number"
                  min={0}
                  max={snapshot?.max_tick || 0}
                  value={diffToTick}
                  onChange={(e) => setDiffToTick(parseInt(e.target.value, 10))}
                  className="w-14 px-2 py-1 bg-slate-900 border border-slate-700 rounded text-slate-200 font-mono"
                />
              </div>
              <button
                onClick={handleComputeDiff}
                disabled={loadingDiff}
                className="px-3 py-1 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded font-mono text-xs font-bold transition"
              >
                {loadingDiff ? 'Computing...' : 'Compute Diff'}
              </button>
            </div>
          </div>

          {diffResult && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs mt-3">
              <div className="p-3 bg-slate-900/90 border border-purple-900/30 rounded-lg">
                <h4 className="font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                  <span className="text-purple-400">●</span> Node State Deltas ({diffResult.node_changes.length})
                </h4>
                {diffResult.node_changes.length === 0 ? (
                  <p className="text-slate-500 italic">No node state shifts in this window.</p>
                ) : (
                  <ul className="space-y-1.5 mt-2">
                    {diffResult.node_changes.map((nc, idx) => (
                      <li key={idx} className="text-slate-300 bg-slate-800/60 p-1.5 rounded border border-slate-750">
                        {nc.description}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="p-3 bg-slate-900/90 border border-purple-900/30 rounded-lg">
                <h4 className="font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                  <span className="text-cyan-400">●</span> Relationship Edge Deltas ({diffResult.edge_changes.length})
                </h4>
                {diffResult.edge_changes.length === 0 ? (
                  <p className="text-slate-500 italic">Relationships remained stable across this simulation window.</p>
                ) : (
                  <ul className="space-y-1.5 mt-2">
                    {diffResult.edge_changes.map((ec, idx) => (
                      <li key={idx} className="text-slate-300 bg-slate-800/60 p-1.5 rounded border border-slate-750">
                        {ec.description}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main Graph Canvas & Inspector Layout */}
      <div className="relative flex flex-col lg:flex-row flex-1 min-h-[540px] w-full">
        {/* SVG Visualization Canvas */}
        <div className="flex-1 min-w-0 bg-slate-950 p-2 flex items-center justify-center relative overflow-hidden" style={{ minHeight: '520px' }}>
          {loading && (
            <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center z-20">
              <span className="text-cyan-400 font-mono text-sm animate-pulse">
                Projecting D3 temporal force graph at Tick {currentTick}...
              </span>
            </div>
          )}

          {error && (
            <div className="p-4 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-200 text-xs">
              {error}
            </div>
          )}

          {!loading && snapshot && snapshot.nodes.length === 0 && (
            <div className="text-center p-8 text-slate-500 font-mono text-sm">
              No character entities simulated in this world yet.
            </div>
          )}

          {/* D3 Zoom & Layout Viewport Overlay Controls */}
          <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 bg-slate-900/80 backdrop-blur p-1 rounded-lg border border-slate-800 text-slate-300 shadow-lg">
            <button
              onClick={handleZoomIn}
              className="w-7 h-7 flex items-center justify-center rounded hover:bg-slate-800 font-mono text-sm"
              title="Zoom In"
            >
              +
            </button>
            <button
              onClick={handleZoomOut}
              className="w-7 h-7 flex items-center justify-center rounded hover:bg-slate-800 font-mono text-sm"
              title="Zoom Out"
            >
              -
            </button>
            <button
              onClick={handleResetZoom}
              className="px-2 h-7 flex items-center justify-center rounded hover:bg-slate-800 font-mono text-xs"
              title="Reset View"
            >
              Reset
            </button>
            <div className="w-[1px] h-4 bg-slate-750 mx-0.5" />
            <button
              onClick={handleTogglePhysics}
              className={`px-2 h-7 flex items-center justify-center rounded font-mono text-xs transition ${
                isPhysicsPaused ? 'bg-amber-950/80 text-amber-300 border border-amber-800/70' : 'hover:bg-slate-800 text-slate-400'
              }`}
              title={isPhysicsPaused ? 'Resume D3 physics' : 'Pause D3 physics'}
            >
              {isPhysicsPaused ? 'Resume' : 'Freeze'}
            </button>
          </div>

          {/* D3 SVG Force Canvas */}
          {snapshot && snapshot.nodes.length > 0 && (
            <svg
              ref={svgRef}
              viewBox="0 0 760 520"
              className="w-full h-full min-h-[500px] max-h-[580px] select-none cursor-grab active:cursor-grabbing"
            >
              {/* SVG Defs for markers and gradients */}
              <defs>
                <radialGradient id="graphGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#0891b2" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#0891b2" stopOpacity="0" />
                </radialGradient>

                {/* Canonical Solid Arrowhead */}
                <marker
                  id="arrow-canonical"
                  viewBox="0 0 10 10"
                  refX="22"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#10b981" />
                </marker>

                {/* Analytical Hypothesis Dashed Arrowhead */}
                <marker
                  id="arrow-hypothesis"
                  viewBox="0 0 10 10"
                  refX="22"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#c084fc" />
                </marker>

                {/* Causal Action Cyan Arrowhead */}
                <marker
                  id="arrow-causal"
                  viewBox="0 0 10 10"
                  refX="22"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto"
                >
                  <path d="M 0 1 L 9 5 L 0 9 z" fill="#38bdf8" />
                </marker>
              </defs>

              <g ref={gRef}>
                {/* Background Ambient Glow */}
                <circle cx="380" cy="260" r="280" fill="url(#graphGlow)" pointerEvents="none" />

                {/* D3 LINKS / EDGES */}
                <g className="links-layer">
                  {simulationLinks.map((link) => {
                    const edge = link.data;
                    const src = typeof link.source === 'object' ? link.source : simulationNodes.find((n) => n.id === link.source);
                    const tgt = typeof link.target === 'object' ? link.target : simulationNodes.find((n) => n.id === link.target);
                    if (!src || !tgt || src.x === undefined || tgt.x === undefined) return null;

                    const isSelected = selectedEdge?.id === edge.id;
                    const style = getEdgeStyle(edge);
                    const isHypothesis = edge.edge_category === 'analytical_hypothesis';
                    const isCausal = edge.edge_kind === 'causal_action' || edge.edge_kind === 'causal_impact';

                    // Curved path calculations
                    const dx = tgt.x - src.x;
                    const dy = tgt.y - src.y;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    const normX = -dy / dist;
                    const normY = dx / dist;
                    const curvature = isHypothesis ? 28 : isCausal ? 18 : 22;
                    const midX = (src.x + tgt.x) / 2 + normX * curvature;
                    const midY = (src.y + tgt.y) / 2 + normY * curvature;

                    const strokeWidth = isSelected
                      ? 3.5
                      : isHypothesis
                      ? 2.2
                      : Math.max(1.8, Math.min(5, 1.8 + edge.aggregate_intensity * 3));

                    const markerId = isHypothesis
                      ? 'url(#arrow-hypothesis)'
                      : isCausal
                      ? 'url(#arrow-causal)'
                      : edge.relationship_type === 'hostile' || edge.relationship_type === 'allies'
                      ? 'url(#arrow-canonical)'
                      : undefined;

                    return (
                      <g
                        key={edge.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedEdge(edge);
                          setSelectedNode(null);
                        }}
                        className="cursor-pointer group"
                      >
                        {/* Invisible thick hover hit-box */}
                        <path
                          d={`M ${src.x} ${src.y} Q ${midX} ${midY} ${tgt.x} ${tgt.y}`}
                          fill="none"
                          stroke="transparent"
                          strokeWidth="16"
                        />

                        {/* Visible Link Path */}
                        <path
                          d={`M ${src.x} ${src.y} Q ${midX} ${midY} ${tgt.x} ${tgt.y}`}
                          fill="none"
                          stroke={style.color}
                          strokeWidth={strokeWidth}
                          strokeDasharray={style.dashArray}
                          strokeOpacity={isSelected ? 1.0 : isHypothesis ? 0.85 : 0.7}
                          markerEnd={markerId}
                          className="transition-all duration-150 group-hover:stroke-opacity-100"
                        />

                        {/* Edge Label Badge */}
                        <g transform={`translate(${midX}, ${midY})`}>
                          <rect
                            x={isHypothesis ? -44 : -32}
                            y="-9"
                            width={isHypothesis ? 88 : 64}
                            height="18"
                            rx="4"
                            fill="#0b0f17"
                            stroke={style.color}
                            strokeWidth={isSelected ? '1.5' : '1'}
                            strokeDasharray={isHypothesis ? '2,2' : undefined}
                            className="opacity-95"
                          />
                          <text
                            x="0"
                            y="3.5"
                            textAnchor="middle"
                            fontSize="8.5"
                            fill={style.color}
                            fontFamily="monospace"
                            fontWeight="bold"
                            className="pointer-events-none select-none"
                          >
                            {isHypothesis
                              ? `HYP ${Math.round((edge.confidence || 0.7) * 100)}%`
                              : style.label}
                          </text>
                        </g>
                      </g>
                    );
                  })}
                </g>

                {/* D3 NODES (CHARACTERS & CAUSAL EVENTS) */}
                <g className="nodes-layer">
                  {simulationNodes.map((node) => {
                    if (node.x === undefined || node.y === undefined) return null;
                    const isSelected = selectedNode?.id === node.id;
                    const isCausalEvent = node.node_type === 'causal_event';

                    if (isCausalEvent) {
                      // CAUSAL EVENT NODE RENDERING (Diamond / Hexagon geometry)
                      return (
                        <g
                          key={node.id}
                          transform={`translate(${node.x}, ${node.y})`}
                          onMouseDown={(e) => handleNodeMouseDown(e, node)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedNode(node);
                            setSelectedEdge(null);
                          }}
                          className="cursor-pointer group"
                        >
                          {/* Glow when selected */}
                          {isSelected && (
                            <polygon
                              points="0,-26 26,0 0,26 -26,0"
                              fill="none"
                              stroke="#38bdf8"
                              strokeWidth="2.5"
                              strokeDasharray="4,3"
                              className="animate-spin-slow"
                            />
                          )}

                          {/* Event Diamond Badge */}
                          <polygon
                            points="0,-20 20,0 0,20 -20,0"
                            fill="#082f49"
                            stroke={isSelected ? '#38bdf8' : '#0284c7'}
                            strokeWidth="2"
                            className="transition-colors group-hover:stroke-sky-300"
                          />

                          {/* Tick Badge in center */}
                          <text
                            textAnchor="middle"
                            dy="4"
                            fill="#bae6fd"
                            fontSize="10"
                            fontWeight="bold"
                            fontFamily="monospace"
                          >
                            T{node.tick ?? 0}
                          </text>

                          {/* Event Name Label */}
                          <text
                            textAnchor="middle"
                            dy="34"
                            fill="#e0f2fe"
                            fontSize="10"
                            fontWeight="600"
                            fontFamily="sans-serif"
                            className="select-none"
                          >
                            {node.name}
                          </text>

                          {/* Event Type Subtitle */}
                          <text
                            textAnchor="middle"
                            dy="46"
                            fill="#7dd3fc"
                            fontSize="8"
                            fontFamily="monospace"
                            className="select-none"
                          >
                            {node.event_type || 'HISTORICAL'}
                          </text>
                        </g>
                      );
                    }

                    // CHARACTER NODE RENDERING (Avatar circle with stats)
                    const initials = node.name
                      .split(' ')
                      .map((p) => p[0])
                      .join('')
                      .toUpperCase()
                      .slice(0, 2);

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x}, ${node.y})`}
                        onMouseDown={(e) => handleNodeMouseDown(e, node)}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedNode(node);
                          setSelectedEdge(null);
                          if (onSelectCharacter) onSelectCharacter(node.id);
                        }}
                        className="cursor-pointer group"
                      >
                        {/* Selection Halo */}
                        {isSelected && (
                          <circle
                            r="34"
                            fill="none"
                            stroke="#38bdf8"
                            strokeWidth="2.5"
                            strokeDasharray="4,4"
                            className="animate-spin-slow"
                          />
                        )}

                        {/* Outer Avatar Circle */}
                        <circle
                          r="26"
                          fill="#0f172a"
                          stroke={isSelected ? '#38bdf8' : '#334155'}
                          strokeWidth={isSelected ? '3' : '2'}
                          className="transition-colors group-hover:stroke-cyan-400"
                        />

                        {/* Character Initials */}
                        <text
                          textAnchor="middle"
                          dy="5"
                          fill="#f8fafc"
                          fontSize="13"
                          fontWeight="bold"
                          fontFamily="monospace"
                        >
                          {initials}
                        </text>

                        {/* Character Name Label */}
                        <text
                          textAnchor="middle"
                          dy="42"
                          fill="#e2e8f0"
                          fontSize="11"
                          fontWeight="600"
                          className="select-none"
                        >
                          {node.name}
                        </text>

                        {/* Character Role Pill */}
                        <text
                          textAnchor="middle"
                          dy="55"
                          fill="#94a3b8"
                          fontSize="9"
                          className="select-none"
                        >
                          {node.role}
                        </text>

                        {/* Active Conflict Badge if any */}
                        {node.active_conflicts && node.active_conflicts.length > 0 && (
                          <g transform="translate(18, -18)">
                            <circle r="8" fill="#e11d48" />
                            <text
                              textAnchor="middle"
                              dy="3"
                              fill="#ffffff"
                              fontSize="9"
                              fontWeight="bold"
                            >
                              {node.active_conflicts.length}
                            </text>
                          </g>
                        )}
                      </g>
                    );
                  })}
                </g>
              </g>
            </svg>
          )}

          {/* Canvas Bottom Legend */}
          <div className="absolute bottom-2 left-3 flex flex-wrap items-center gap-3 text-[11px] text-slate-400 bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800 backdrop-blur shadow-md">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-500 rounded" /> Canonical Allies
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-rose-500 rounded" /> Canonical Hostile
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-amber-500 rounded border-t border-dashed" /> Guarded
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-purple-400 rounded border-t border-dashed" /> Analytical Hypothesis
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 bg-sky-500 rotate-45 rounded-[1px]" /> Causal Event Node
            </span>
          </div>
        </div>

        {/* Side Inspector Drawer */}
        <div className="w-full lg:w-[360px] flex-shrink-0 bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 p-4 flex flex-col justify-between overflow-y-auto max-h-[580px]">
          {selectedNode ? (
            <div className="space-y-4">
              {selectedNode.node_type === 'causal_event' ? (
                // CAUSAL EVENT INSPECTION DETAILS
                <div>
                  <div className="border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-950 text-sky-300 border border-sky-800">
                        HISTORICAL EVENT · T{selectedNode.tick ?? 0}
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400 uppercase">
                        CANONICAL FACT
                      </span>
                    </div>
                    <h4 className="text-base font-bold text-white mt-1.5">{selectedNode.name}</h4>
                    <p className="text-xs text-slate-300 mt-1 leading-relaxed bg-slate-800/60 p-2.5 rounded border border-slate-750">
                      {selectedNode.description || 'Pivotal simulation event record.'}
                    </p>
                  </div>

                  <div className="space-y-3 mt-3 text-xs">
                    <div className="bg-slate-800/80 p-2 rounded border border-slate-750">
                      <span className="text-slate-400 text-[10px] uppercase font-mono block">Context Location</span>
                      <span className="text-slate-200 font-medium">{selectedNode.location_context || 'World Arena'}</span>
                    </div>

                    <div className="bg-slate-800/80 p-2 rounded border border-slate-750">
                      <span className="text-slate-400 text-[10px] uppercase font-mono block">Significance Rating</span>
                      <span className="text-cyan-300 font-mono font-bold">
                        {((selectedNode.significance || 0.7) * 100).toFixed(0)}% Dramatic Tension
                      </span>
                    </div>

                    <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded">
                      <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">
                        Causal Ground Truth
                      </span>
                      <p className="text-[11px] text-slate-300">
                        This event is immutably recorded in the WorldState EventLog. AI agents and Scribe cannot mutate or invent this occurrence.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                // CHARACTER INSPECTION DETAILS
                <div>
                  <div className="border-b border-slate-800 pb-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                        Character Inspection @ Tick {currentTick}
                      </span>
                      <span className="text-[10px] font-mono bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">
                        {selectedNode.id}
                      </span>
                    </div>
                    <h4 className="text-lg font-bold text-white mt-0.5">{selectedNode.name}</h4>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-xs font-medium">
                        {selectedNode.role}
                      </span>
                      <span className="text-xs text-slate-400">
                        Loc: {selectedNode.location_name || selectedNode.location_id || 'Harbor Bay'}
                      </span>
                    </div>
                  </div>

                  {/* Emotional State */}
                  <div className="mt-3">
                    <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-2">
                      Emotional State
                    </h5>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {Object.entries(selectedNode.emotional_state).map(([emo, val]) => (
                        <div key={emo} className="bg-slate-800/80 p-1.5 rounded border border-slate-750">
                          <div className="flex justify-between text-[11px] text-slate-400 capitalize">
                            <span>{emo}</span>
                            <span className="font-mono text-slate-200">{val.toFixed(2)}</span>
                          </div>
                          <div className="w-full bg-slate-700 h-1.5 rounded-full mt-1 overflow-hidden">
                            <div
                              className="bg-cyan-400 h-full rounded-full"
                              style={{ width: `${Math.max(0, Math.min(100, (val + 1) * 50))}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Private Subjective Beliefs */}
                  <div className="mt-3">
                    <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-1.5">
                      Subjective Beliefs ({Object.keys(selectedNode.beliefs).length})
                    </h5>
                    {Object.keys(selectedNode.beliefs).length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No propositions registered in knowledge state.</p>
                    ) : (
                      <ul className="space-y-1 text-xs">
                        {Object.entries(selectedNode.beliefs).map(([propId, truth]) => (
                          <li
                            key={propId}
                            className="bg-slate-800/60 p-1.5 rounded border border-slate-750 flex items-center justify-between"
                          >
                            <span className="font-mono text-slate-300">{propId}</span>
                            <span
                              className={`px-1.5 py-0.2 rounded font-mono text-[10px] ${
                                truth ? 'bg-emerald-950 text-emerald-300' : 'bg-rose-950 text-rose-300'
                              }`}
                            >
                              {truth ? 'TRUE' : 'FALSE'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Active Interpersonal Conflicts */}
                  <div className="mt-3">
                    <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-1.5">
                      Active Conflicts ({selectedNode.active_conflicts?.length || 0})
                    </h5>
                    {!selectedNode.active_conflicts || selectedNode.active_conflicts.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No acute interpersonal tensions recorded.</p>
                    ) : (
                      <ul className="space-y-1.5 text-xs">
                        {selectedNode.active_conflicts.map((conf, idx) => (
                          <li key={idx} className="bg-rose-950/20 border border-rose-900/40 p-2 rounded">
                            <div className="flex justify-between font-semibold text-rose-300">
                              <span>Peer: {conf.peer_id}</span>
                              <span className="font-mono">Intensity: {conf.aggregate_intensity.toFixed(2)}</span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : selectedEdge ? (
            // EDGE INSPECTION DETAILS (CANONICAL VS HYPOTHESIS DIFFERENTIATION)
            <div className="space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                    Edge Inspection @ Tick {currentTick}
                  </span>
                  {selectedEdge.edge_category === 'analytical_hypothesis' ? (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800">
                      ANALYTICAL HYPOTHESIS
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                      CANONICAL GROUND TRUTH
                    </span>
                  )}
                </div>

                <h4 className="text-base font-bold text-white mt-1">
                  {selectedEdge.source_name} ↔ {selectedEdge.target_name}
                </h4>

                <div className="flex items-center gap-2 mt-1.5">
                  <span
                    className="px-2 py-0.5 rounded text-xs font-bold uppercase font-mono"
                    style={{
                      backgroundColor: `${getEdgeStyle(selectedEdge).color}22`,
                      color: getEdgeStyle(selectedEdge).color,
                      border: `1px solid ${getEdgeStyle(selectedEdge).color}66`,
                    }}
                  >
                    {selectedEdge.relationship_type}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Intensity: {selectedEdge.aggregate_intensity.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Hypothesis Specific Rationale & Falsification Conditions */}
              {selectedEdge.edge_category === 'analytical_hypothesis' ? (
                <div className="space-y-3 p-3 bg-purple-950/30 border border-purple-900/60 rounded-lg text-xs">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-purple-300 font-bold block mb-1">
                      Hypothesis Confidence
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-purple-400 h-full rounded-full"
                          style={{ width: `${Math.round((selectedEdge.confidence || 0.75) * 100)}%` }}
                        />
                      </div>
                      <span className="font-mono text-purple-200 font-bold">
                        {Math.round((selectedEdge.confidence || 0.75) * 100)}%
                      </span>
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] font-mono uppercase text-purple-300 font-bold block mb-1">
                      Observer Rationale
                    </span>
                    <p className="text-slate-300 leading-relaxed bg-slate-900/80 p-2 rounded border border-purple-900/40">
                      {selectedEdge.hypothesis_rationale ||
                        'Narrative intelligence inferred relationship dynamic based on character goal divergences and emotional spikes.'}
                    </p>
                  </div>

                  {selectedEdge.falsification_conditions && selectedEdge.falsification_conditions.length > 0 && (
                    <div>
                      <span className="text-[10px] font-mono uppercase text-purple-300 font-bold block mb-1">
                        Falsification Criteria
                      </span>
                      <ul className="space-y-1 list-disc list-inside text-slate-300 text-[11px]">
                        {selectedEdge.falsification_conditions.map((fc, i) => (
                          <li key={i} className="text-slate-300">
                            {fc}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3 bg-emerald-950/20 border border-emerald-900/40 rounded-lg text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-emerald-400 font-mono text-[10px] font-bold uppercase">
                      Ground Truth Verification
                    </span>
                    <span className="px-1.5 py-0.2 bg-emerald-900/60 text-emerald-300 font-mono text-[9px] rounded">
                      100% CONFIDENCE
                    </span>
                  </div>
                  <p className="text-slate-300 text-[11px] leading-relaxed">
                    {selectedEdge.causal_mechanism ||
                      'Explicit relationship state directly recorded in the canonical WorldState matrix.'}
                  </p>
                </div>
              )}

              {/* Multidimensional Vector Breakdown */}
              <div>
                <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-2">
                  Multidimensional State
                </h5>
                <div className="space-y-1.5 text-xs">
                  {Object.entries(selectedEdge.dimensions).map(([dim, val]) => (
                    <div key={dim} className="bg-slate-800/80 p-1.5 rounded border border-slate-750">
                      <div className="flex justify-between text-[11px] text-slate-400 capitalize">
                        <span>{dim}</span>
                        <span className="font-mono text-slate-200">{(val || 0).toFixed(2)}</span>
                      </div>
                      <div className="w-full bg-slate-700 h-1.5 rounded-full mt-1 overflow-hidden">
                        <div
                          className="bg-cyan-400 h-full rounded-full"
                          style={{ width: `${Math.max(0, Math.min(100, ((val || 0) + 1) * 50))}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Causal Event Provenance */}
              <div>
                <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-1.5">
                  Event Provenance ({selectedEdge.evidence_event_ids.length})
                </h5>
                {selectedEdge.evidence_event_ids.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">Baseline design-time relationship without events.</p>
                ) : (
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {selectedEdge.evidence_event_ids.map((eid) => (
                      <div
                        key={eid}
                        className="bg-slate-800/60 px-2 py-1 rounded border border-slate-750 text-xs font-mono text-cyan-300 flex items-center justify-between"
                      >
                        <span>{eid}</span>
                        <span className="text-[10px] text-slate-400">VERIFIED</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
              <span className="text-3xl mb-2">⚡</span>
              <p className="text-xs font-medium text-slate-400">
                Click any Character Node, Causal Event, or Edge in the D3 force graph to inspect its verified provenance and analytical hypotheses.
              </p>
            </div>
          )}

          {/* Footer Metadata */}
          <div className="pt-3 border-t border-slate-800/80 text-[11px] text-slate-500 font-mono flex items-center justify-between">
            <span>Tick {currentTick}</span>
            <span>{snapshot?.event_count || 0} Events Logged</span>
          </div>
        </div>
      </div>
    </div>
  );
};
