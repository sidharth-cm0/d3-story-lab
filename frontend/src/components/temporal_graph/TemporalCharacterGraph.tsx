import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  TemporalGraphSnapshot,
  TemporalGraphNode,
  TemporalGraphEdge,
  TemporalGraphDiff,
} from '../../types';
import { fetchTemporalGraph, fetchTemporalGraphDiff } from '../../api';

interface TemporalCharacterGraphProps {
  projectId: string;
  initialTick?: number;
  onSelectCharacter?: (charId: string) => void;
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

  // Dimension filter
  const [dimensionFilter, setDimensionFilter] = useState<string>('all');

  // Load graph snapshot at currentTick with race condition cancellation
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
          // Sync selection if still in snapshot
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

  // Handle Playback
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

  // Calculate layout coordinates for nodes in SVG canvas (radial layout)
  const nodePositions = useMemo(() => {
    if (!snapshot || snapshot.nodes.length === 0) return new Map<string, { x: number; y: number }>();
    const positions = new Map<string, { x: number; y: number }>();
    const count = snapshot.nodes.length;
    const centerX = 360;
    const centerY = 260;
    const radius = Math.min(centerX, centerY) - 80;

    snapshot.nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / count - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      positions.set(node.id, { x, y });
    });
    return positions;
  }, [snapshot]);

  // Filter edges based on selected dimension filter
  const visibleEdges = useMemo(() => {
    if (!snapshot) return [];
    if (dimensionFilter === 'all') return snapshot.edges;
    if (dimensionFilter === 'high_intensity') {
      return snapshot.edges.filter((e) => e.aggregate_intensity >= 0.4);
    }
    if (dimensionFilter === 'allies') {
      return snapshot.edges.filter((e) => e.relationship_type === 'allies');
    }
    if (dimensionFilter === 'hostile') {
      return snapshot.edges.filter((e) => e.relationship_type === 'hostile');
    }
    if (dimensionFilter === 'guarded') {
      return snapshot.edges.filter((e) => e.relationship_type === 'guarded');
    }
    return snapshot.edges.filter((e) => {
      const val = e.dimensions[dimensionFilter];
      return val !== undefined && Math.abs(val) >= 0.3;
    });
  }, [snapshot, dimensionFilter]);

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

  // Color helper for relationship type
  const getEdgeColor = (type: string, intensity: number) => {
    switch (type) {
      case 'allies':
        return '#10b981'; // emerald-500
      case 'hostile':
        return '#f43f5e'; // rose-500
      case 'guarded':
        return '#f59e0b'; // amber-500
      case 'conflicted':
        return '#a855f7'; // purple-500
      default:
        return intensity > 0.4 ? '#38bdf8' : '#64748b'; // sky-400 / slate-500
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl flex flex-col">
      {/* Top Controls Header */}
      <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
            <h3 className="text-base font-bold text-white tracking-wide uppercase">
              Temporal Character-Relationship Graph
            </h3>
            <span className="px-2 py-0.5 text-xs font-mono rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60">
              Tick {currentTick} / {snapshot?.max_tick ?? 0}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic state projection with multidimensional dynamic edges & event provenance.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
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

      {/* Scrubber Bar */}
      <div className="px-4 py-3 bg-slate-900/90 border-b border-slate-800/80 flex flex-wrap items-center gap-4">
        {/* Playback buttons */}
        <div className="flex items-center gap-1">
          <button
            disabled={currentTick <= 0}
            onClick={() => setCurrentTick((t) => Math.max(0, t - 1))}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs"
            title="Step Back"
          >
            ◀
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold"
          >
            {isPlaying ? 'PAUSE' : 'PLAY'}
          </button>
          <button
            disabled={snapshot ? currentTick >= snapshot.max_tick : true}
            onClick={() => setCurrentTick((t) => Math.min(snapshot?.max_tick || 0, t + 1))}
            className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 text-xs"
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
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Filter:</span>
          {[
            { id: 'all', label: 'All Edges' },
            { id: 'high_intensity', label: 'High Tension' },
            { id: 'allies', label: 'Allies' },
            { id: 'hostile', label: 'Hostile' },
            { id: 'guarded', label: 'Guarded' },
            { id: 'trust', label: 'Trust' },
            { id: 'suspicion', label: 'Suspicion' },
            { id: 'fear', label: 'Fear' },
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
        <div className="p-4 bg-purple-950/20 border-b border-purple-900/40">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-purple-300 uppercase tracking-wide">Diff Range:</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">From Tick</span>
                <input
                  type="number"
                  min={0}
                  max={snapshot?.max_tick || 0}
                  value={diffFromTick}
                  onChange={(e) => setDiffFromTick(parseInt(e.target.value, 10) || 0)}
                  className="w-16 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-slate-200 font-mono"
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">To Tick</span>
                <input
                  type="number"
                  min={0}
                  max={snapshot?.max_tick || 0}
                  value={diffToTick}
                  onChange={(e) => setDiffToTick(parseInt(e.target.value, 10) || 0)}
                  className="w-16 px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs text-slate-200 font-mono"
                />
              </div>
              <button
                onClick={handleComputeDiff}
                disabled={loadingDiff}
                className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded text-xs font-semibold shadow disabled:opacity-50"
              >
                {loadingDiff ? 'Calculating...' : 'Compute Diff'}
              </button>
            </div>
            {diffResult && (
              <span className="text-xs text-purple-300 font-mono">
                {diffResult.causal_event_ids.length} intervening events found
              </span>
            )}
          </div>

          {diffResult && (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-900/90 border border-purple-900/30 rounded-lg">
                <h4 className="font-bold text-slate-200 mb-1 flex items-center gap-1.5">
                  <span className="text-purple-400">●</span> Character Node Shifts ({diffResult.node_changes.length})
                </h4>
                {diffResult.node_changes.length === 0 ? (
                  <p className="text-slate-500 italic">No character movements or emotional shifts in this interval.</p>
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
      <div className="relative flex flex-col lg:flex-row flex-1 min-h-[520px]">
        {/* SVG Visualization Canvas */}
        <div className="flex-1 bg-slate-950 p-2 flex items-center justify-center relative overflow-hidden">
          {loading && (
            <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center z-20">
              <span className="text-cyan-400 font-mono text-sm animate-pulse">
                Projecting temporal graph at Tick {currentTick}...
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

          {snapshot && snapshot.nodes.length > 0 && (
            <svg
              viewBox="0 0 720 520"
              className="w-full h-auto max-h-[540px] select-none"
            >
              {/* Background ambient grid */}
              <defs>
                <radialGradient id="graphGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#0891b2" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#0891b2" stopOpacity="0" />
                </radialGradient>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="18"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                </marker>
              </defs>

              <circle cx="360" cy="260" r="220" fill="url(#graphGlow)" />

              {/* Edges */}
              {visibleEdges.map((edge) => {
                const posA = nodePositions.get(edge.source_id);
                const posB = nodePositions.get(edge.target_id);
                if (!posA || !posB) return null;

                const isSelected = selectedEdge?.id === edge.id;
                const strokeColor = getEdgeColor(edge.relationship_type, edge.aggregate_intensity);
                const strokeWidth = Math.max(1.5, Math.min(6, 1.5 + edge.aggregate_intensity * 5));

                // Slight curve for visual elegance
                const midX = (posA.x + posB.x) / 2;
                const midY = (posA.y + posB.y) / 2;
                const offset = (edge.aggregate_intensity || 0.2) * 15;
                const curveX = midX + offset;
                const curveY = midY - offset;

                return (
                  <g
                    key={edge.id}
                    onClick={() => {
                      setSelectedEdge(edge);
                      setSelectedNode(null);
                    }}
                    className="cursor-pointer group"
                  >
                    <path
                      d={`M ${posA.x} ${posA.y} Q ${curveX} ${curveY} ${posB.x} ${posB.y}`}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={isSelected ? strokeWidth + 2 : strokeWidth}
                      strokeDasharray={edge.relationship_type === 'guarded' ? '4,4' : undefined}
                      opacity={isSelected ? 1 : 0.75}
                      className="transition-all duration-200 group-hover:opacity-100"
                    />

                    {/* Edge Label badge */}
                    <g transform={`translate(${curveX}, ${curveY})`}>
                      <rect
                        x="-30"
                        y="-10"
                        width="60"
                        height="20"
                        rx="4"
                        fill="#0f172a"
                        stroke={strokeColor}
                        strokeWidth="1"
                        className="opacity-90"
                      />
                      <text
                        x="0"
                        y="4"
                        textAnchor="middle"
                        fontSize="9"
                        fill="#f8fafc"
                        fontFamily="monospace"
                        className="font-bold pointer-events-none"
                      >
                        {edge.relationship_type.toUpperCase()}
                      </text>
                    </g>
                  </g>
                );
              })}

              {/* Nodes */}
              {snapshot.nodes.map((node) => {
                const pos = nodePositions.get(node.id);
                if (!pos) return null;

                const isSelected = selectedNode?.id === node.id;
                const initials = node.name
                  .split(' ')
                  .map((p) => p[0])
                  .join('')
                  .toUpperCase()
                  .slice(0, 2);

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onClick={() => {
                      setSelectedNode(node);
                      setSelectedEdge(null);
                      if (onSelectCharacter) onSelectCharacter(node.id);
                    }}
                    className="cursor-pointer group"
                  >
                    {/* Glow when selected */}
                    {isSelected && (
                      <circle
                        r="34"
                        fill="none"
                        stroke="#38bdf8"
                        strokeWidth="2"
                        strokeDasharray="3,3"
                        className="animate-spin-slow"
                      />
                    )}

                    {/* Outer Circle */}
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
                      fill="#f1f5f9"
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
                      className="pointer-events-none"
                    >
                      {node.name}
                    </text>

                    {/* Character Role Pill */}
                    <text
                      textAnchor="middle"
                      dy="55"
                      fill="#94a3b8"
                      fontSize="9"
                      className="pointer-events-none"
                    >
                      {node.role}
                    </text>

                    {/* Active Conflict Badge if any */}
                    {node.active_conflicts.length > 0 && (
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
            </svg>
          )}

          {/* Canvas Bottom Legend */}
          <div className="absolute bottom-2 left-3 flex flex-wrap items-center gap-3 text-[11px] text-slate-400 bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-emerald-500 rounded" /> Allies
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-rose-500 rounded" /> Hostile
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-amber-500 rounded" /> Guarded
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-purple-500 rounded" /> Conflicted
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-0.5 bg-sky-400 rounded" /> Neutral/Complex
            </span>
          </div>
        </div>

        {/* Side Inspector Drawer */}
        <div className="w-full lg:w-80 bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 p-4 flex flex-col justify-between overflow-y-auto max-h-[540px]">
          {selectedNode ? (
            <div className="space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                  Character Inspection @ Tick {currentTick}
                </span>
                <h4 className="text-lg font-bold text-white mt-0.5">{selectedNode.name}</h4>
                <div className="flex items-center gap-2 mt-1">
                  <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-xs font-medium">
                    {selectedNode.role}
                  </span>
                  <span className="text-xs text-slate-400">
                    Loc: {selectedNode.location_name || selectedNode.location_id || 'Unknown'}
                  </span>
                </div>
              </div>

              {/* Emotional State */}
              <div>
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
              <div>
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
              <div>
                <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-1.5">
                  Active Conflicts ({selectedNode.active_conflicts.length})
                </h5>
                {selectedNode.active_conflicts.length === 0 ? (
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
          ) : selectedEdge ? (
            <div className="space-y-4">
              <div className="border-b border-slate-800 pb-3">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                  Relationship Edge @ Tick {currentTick}
                </span>
                <h4 className="text-base font-bold text-white mt-0.5">
                  {selectedEdge.source_name} ↔ {selectedEdge.target_name}
                </h4>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className="px-2 py-0.5 rounded text-xs font-bold uppercase font-mono"
                    style={{
                      backgroundColor: `${getEdgeColor(selectedEdge.relationship_type, selectedEdge.aggregate_intensity)}22`,
                      color: getEdgeColor(selectedEdge.relationship_type, selectedEdge.aggregate_intensity),
                      border: `1px solid ${getEdgeColor(selectedEdge.relationship_type, selectedEdge.aggregate_intensity)}66`,
                    }}
                  >
                    {selectedEdge.relationship_type}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    Intensity: {selectedEdge.aggregate_intensity.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* 9-Dimensional Breakdown */}
              <div>
                <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wide mb-2">
                  Multidimensional State
                </h5>
                <div className="space-y-2 text-xs">
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
                  <div className="max-h-36 overflow-y-auto space-y-1">
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
              <span className="text-2xl mb-2">🔍</span>
              <p className="text-xs font-medium text-slate-400">
                Click a Character Node or Relationship Edge to inspect its temporal state and causal provenance.
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
