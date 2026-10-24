import React, { useState } from 'react';
import { GroundedRAGResponse } from '../../types';
import { queryNarrativeRAG, fetchNarrativeRAGBenchmark } from '../../api';

interface GroundedRAGInquiryProps {
  projectId: string;
}

const PRESET_QUERIES = [
  'What narrative patterns resemble the current conflict?',
  'Which setups have not yet received a payoff?',
  'What environmental pressures can be applied?',
  'Which conflicts have been developing for too long?',
];

export const GroundedRAGInquiry: React.FC<GroundedRAGInquiryProps> = ({ projectId }) => {
  const [queryText, setQueryText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<GroundedRAGResponse | null>(null);

  // Benchmark modal/state
  const [benchmarkOpen, setBenchmarkOpen] = useState<boolean>(false);
  const [benchmarkData, setBenchmarkData] = useState<any | null>(null);
  const [loadingBenchmark, setLoadingBenchmark] = useState<boolean>(false);

  const handleRunQuery = async (queryToRun?: string) => {
    const q = (queryToRun ?? queryText).trim();
    if (!q) return;

    setLoading(true);
    setError(null);
    try {
      const res = await queryNarrativeRAG(projectId, q);
      setResponse(res);
      setQueryText(q);
    } catch (err: any) {
      setError(err.message || 'Failed to execute grounded RAG query');
    } finally {
      setLoading(false);
    }
  };

  const handleRunBenchmark = async () => {
    const q = queryText.trim() || 'confrontation revelation';
    setLoadingBenchmark(true);
    try {
      const data = await fetchNarrativeRAGBenchmark(q);
      setBenchmarkData(data);
      setBenchmarkOpen(true);
    } catch (err: any) {
      setError(err.message || 'Failed to run retrieval benchmark');
    } finally {
      setLoadingBenchmark(false);
    }
  };

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case 'canonical_fact':
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'character_belief':
        return 'bg-cyan-950 text-cyan-300 border-cyan-800';
      case 'narrative_interpretation':
        return 'bg-purple-950 text-purple-300 border-purple-800';
      case 'retrieved_principle':
        return 'bg-blue-950 text-blue-300 border-blue-800';
      case 'advisory_hypothesis':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl p-5 space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
            <h3 className="text-base font-bold text-white tracking-wide uppercase">
              Narrative Intelligence & Grounded RAG
            </h3>
            <span className="px-2 py-0.5 text-xs font-mono rounded bg-blue-950 text-blue-300 border border-blue-800/60">
              Evidence Firewall v1.0
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Answers narrative questions backed by verifiable simulation facts, subjective character worldviews, and curated patterns.
          </p>
        </div>

        {/* Benchmark Button */}
        <button
          onClick={handleRunBenchmark}
          disabled={loadingBenchmark}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-750 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition flex items-center gap-1.5"
        >
          <span>⚖️</span>
          <span>{loadingBenchmark ? 'Benchmarking...' : 'BM25 vs Embedding Benchmark'}</span>
        </button>
      </div>

      {/* Preset Queries */}
      <div className="space-y-1.5">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          Recommended Inquiries:
        </span>
        <div className="flex flex-wrap gap-2">
          {PRESET_QUERIES.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => handleRunQuery(preset)}
              disabled={loading}
              className="px-3 py-1 bg-slate-800/80 hover:bg-slate-750 text-slate-300 hover:text-white border border-slate-750 rounded-full text-xs transition disabled:opacity-50 text-left"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* Freeform Query Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          placeholder="Ask a narrative intelligence question (e.g., 'What setups lack payoff?')..."
          onKeyDown={(e) => e.key === 'Enter' && handleRunQuery()}
          className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
        />
        <button
          onClick={() => handleRunQuery()}
          disabled={loading || !queryText.trim()}
          className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-bold shadow-lg transition disabled:opacity-40"
        >
          {loading ? 'Grounding...' : 'Inquire'}
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="p-3 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-200 text-xs">
          {error}
        </div>
      )}

      {/* Response Panel */}
      {response && (
        <div className="space-y-4 pt-2">
          {/* Answer Card */}
          <div className="p-4 bg-slate-950 border border-cyan-900/40 rounded-xl relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-cyan-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                <span>🛡️</span> Grounded Synthesis
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                STATUS: {response.status}
              </span>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed font-sans">{response.answer}</p>
          </div>

          {/* Grounded Claims List */}
          {response.claims.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wide flex items-center justify-between">
                <span>Verified Claims & Evidence Breakdown ({response.claims.length})</span>
                <span className="text-[10px] font-mono text-slate-500">CANONICAL / ANALYTICAL FIREWALL</span>
              </h4>

              <div className="space-y-2">
                {response.claims.map((claim, idx) => (
                  <div
                    key={claim.claim_id || idx}
                    className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${getCategoryBadge(
                            claim.category
                          )}`}
                        >
                          {claim.category.replace('_', ' ')}
                        </span>
                        <span className="px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded text-[10px] font-mono">
                          {claim.verification_status.toUpperCase()}
                        </span>
                      </div>
                      {claim.cited_evidence_ids.length > 0 && (
                        <div className="flex items-center gap-1">
                          <span className="text-[10px] text-slate-500">Citations:</span>
                          {claim.cited_evidence_ids.map((cid) => (
                            <span
                              key={cid}
                              className="px-1.5 py-0.2 bg-cyan-950 text-cyan-300 border border-cyan-800/60 rounded text-[10px] font-mono"
                            >
                              {cid}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{claim.claim_text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence Catalog */}
          {response.evidence.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wide">
                Referenced Traceable Evidence ({response.evidence.length})
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                {response.evidence.map((ev) => (
                  <div
                    key={ev.id}
                    className="p-2.5 bg-slate-950/50 border border-slate-800/80 rounded-lg flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-mono text-cyan-400 font-bold">{ev.id}</span>
                        <span className="text-[10px] text-slate-400 uppercase font-mono">
                          {ev.source_type} {ev.tick !== null && ev.tick !== undefined ? `@ T${ev.tick}` : ''}
                        </span>
                      </div>
                      <p className="text-slate-300 text-[11px]">{ev.summary}</p>
                    </div>
                    <div className="mt-2 pt-1 border-t border-slate-850 flex justify-between text-[10px] text-slate-500 font-mono">
                      <span>Source: {ev.source_id}</span>
                      <span className="text-emerald-400">VERIFIED</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Retrieval Benchmark Drawer */}
      {benchmarkOpen && benchmarkData && (
        <div className="mt-4 p-4 bg-slate-950 border border-blue-900/40 rounded-xl space-y-3">
          <div className="flex justify-between items-center border-b border-slate-800 pb-2">
            <h4 className="text-xs font-bold text-blue-300 uppercase tracking-wide flex items-center gap-1.5">
              <span>⚖️</span> Retrieval Benchmark: BM25 Lexical vs Local Feature Embeddings
            </h4>
            <button
              onClick={() => setBenchmarkOpen(false)}
              className="text-slate-400 hover:text-white text-xs font-mono"
            >
              ✕ CLOSE
            </button>
          </div>

          <div className="text-xs font-mono text-slate-400">
            Query: &quot;{benchmarkData.query}&quot; | Model: {benchmarkData.embedding_model} (v{benchmarkData.index_version})
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            {/* BM25 Lexical */}
            <div className="p-3 bg-slate-900 rounded border border-slate-800">
              <span className="font-bold text-slate-200 block mb-2">BM25 Lexical Hits</span>
              <ul className="space-y-1.5">
                {benchmarkData.lexical.map((r: any) => (
                  <li key={r.id} className="p-1.5 bg-slate-950 rounded flex justify-between">
                    <span className="text-cyan-300 font-mono truncate mr-2">{r.id}: {r.title}</span>
                    <span className="text-slate-400 font-mono">{r.score.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Semantic Embeddings */}
            <div className="p-3 bg-slate-900 rounded border border-slate-800">
              <span className="font-bold text-slate-200 block mb-2">Local Semantic Hits</span>
              <ul className="space-y-1.5">
                {benchmarkData.semantic.map((r: any) => (
                  <li key={r.id} className="p-1.5 bg-slate-950 rounded flex justify-between">
                    <span className="text-purple-300 font-mono truncate mr-2">{r.id}: {r.title}</span>
                    <span className="text-slate-400 font-mono">{r.score.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Hybrid Ranking */}
            <div className="p-3 bg-slate-900 rounded border border-slate-800">
              <span className="font-bold text-slate-200 block mb-2">Hybrid Merged Ranking</span>
              <ul className="space-y-1.5">
                {benchmarkData.hybrid.map((r: any) => (
                  <li key={r.id} className="p-1.5 bg-slate-950 rounded flex justify-between">
                    <span className="text-emerald-300 font-mono truncate mr-2">{r.id}: {r.title}</span>
                    <span className="text-slate-400 font-mono">{r.score.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
