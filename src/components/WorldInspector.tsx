import React, { useState } from 'react';
import { WorldState } from '../types';
import { formatDisplayValue } from '../utils/format';
import { GranularField } from './granular';

interface WorldInspectorProps {
  world: WorldState;
}

type WorldTab = 'places' | 'objects' | 'facts' | 'unknown';

export const WorldInspector: React.FC<WorldInspectorProps> = ({ world }) => {
  const [tab, setTab] = useState<WorldTab>('places');
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(null);

  const locations = Object.values(world.locations || {});
  const objects = Object.values(world.objects || {});
  const facts = Object.values(world.facts || {});

  // Unknown entities: uninspected objects or unvisited places
  const uninspected = objects.filter((o) => !o.inspected_by || o.inspected_by.length === 0);

  return (
    <div className="world-inspector-pane" style={{ position: 'relative' }}>
      {/* Granular Topology Backdrop (§11) */}
      <GranularField
        seed={202}
        pointCount={75}
        className="granular-topology-bg"
        style={{ opacity: selectedLocationId ? 0.38 : 0.22 }}
        color="rgba(235, 235, 235, 0.4)"
        accentColor="var(--accent-amber, #d89c38)"
      />

      <div className="pane-header" style={{ position: 'relative', zIndex: 1 }}>
        <div>
          <span className="pane-kicker">SANDBOX TOPOLOGY</span>
          <h2 className="pane-title">WORLD</h2>
        </div>
        <div className="tab-pill-group">
          <button
            className={`pill-btn ${tab === 'places' ? 'active' : ''}`}
            onClick={() => setTab('places')}
          >
            PLACES ({locations.length})
          </button>
          <button
            className={`pill-btn ${tab === 'objects' ? 'active' : ''}`}
            onClick={() => setTab('objects')}
          >
            OBJECTS / Props ({objects.length})
          </button>
          <button
            className={`pill-btn ${tab === 'facts' ? 'active' : ''}`}
            onClick={() => setTab('facts')}
          >
            FACTS ({facts.length})
          </button>
          <button
            className={`pill-btn ${tab === 'unknown' ? 'active' : ''}`}
            onClick={() => setTab('unknown')}
          >
            UNKNOWN ({uninspected.length})
          </button>
        </div>
      </div>

      <div className="world-cards-grid" style={{ position: 'relative', zIndex: 1 }}>
        {tab === 'places' && (
          locations.length === 0 ? (
            <div className="empty-quiet">NO LOCATIONS DEFINED</div>
          ) : (
            locations.map((loc) => {
              const isSelected = selectedLocationId === loc.id;
              return (
                <div
                  key={loc.id}
                  className={`noir-card ${isSelected ? 'selected-shot-granular-frame' : ''}`}
                  onClick={() => setSelectedLocationId(isSelected ? null : loc.id)}
                  style={{ cursor: 'pointer' }}
                  title="Click to focus topology node"
                >
                  <div className="card-topline">
                    <span className="card-item-title">{formatDisplayValue(loc.name)}</span>
                    <span className="card-sub-tag">{isSelected ? 'FOCUSED NODE' : 'ROOM'}</span>
                  </div>
                  <p className="card-desc">{formatDisplayValue(loc.description)}</p>
                  {loc.visual_profile && (
                    <div className="card-visual-profile-box">
                      <span className="visual-profile-tag">VISUAL ENVIRONMENT:</span>
                      <span className="visual-profile-desc">
                        {formatDisplayValue(`${loc.visual_profile.environment_type} • ${loc.visual_profile.palette} • ${loc.visual_profile.lighting}`)}
                      </span>
                    </div>
                  )}
                  <div className="card-meta-line">
                    <span className="meta-label">CONNECTIVITY</span>
                    <span className="meta-value">
                      Connected to {loc.connected_locations.length > 0
                        ? loc.connected_locations.map((cid) => formatDisplayValue(world.locations[cid]?.name || cid)).join(', ')
                        : 'None (Isolated)'}
                    </span>
                  </div>
                </div>
              );
            })
          )
        )}

        {tab === 'objects' && (
          objects.length === 0 ? (
            <div className="empty-quiet">NO OBJECTS PRESENT</div>
          ) : (
            objects.map((obj) => {
              const holder = obj.holder_id ? world.characters[obj.holder_id]?.name : null;
              const loc = obj.location_id ? world.locations[obj.location_id]?.name : null;
              return (
                <div key={obj.id} className="noir-card">
                  <div className="card-topline">
                    <span className="card-item-title text-amber">{formatDisplayValue(obj.name)}</span>
                    <span className="card-sub-tag">{obj.portable ? 'PORTABLE' : 'FIXED'}</span>
                  </div>
                  <p className="card-desc">{formatDisplayValue(obj.description)}</p>
                  {obj.visual_profile && (
                    <div className="card-visual-profile-box">
                      <span className="visual-profile-tag">VISUAL PROP CONTINUITY:</span>
                      <span className="visual-profile-desc">
                        {formatDisplayValue(`${obj.visual_profile.color} ${obj.visual_profile.material} (${obj.visual_profile.size}). Marker: ${obj.visual_profile.unique_markers}`)}
                      </span>
                    </div>
                  )}
                  <div className="card-meta-line">
                    <span className="meta-label">STATUS</span>
                    <span className="meta-value">
                      {holder ? `Held by ${formatDisplayValue(holder).toUpperCase()}` : (loc ? `Present in ${formatDisplayValue(loc).toUpperCase()}` : 'Unknown')}
                    </span>
                  </div>
                </div>
              );
            })
          )
        )}


        {tab === 'facts' && (
          facts.length === 0 ? (
            <div className="empty-quiet">NO DISCOVERED FACTS YET. CHARACTERS DISCOVER FACTS AS THEY INSPECT OBJECTS & SPEAK.</div>
          ) : (
            facts.map((fact) => (
              <div key={fact.id} className="noir-card">
                <div className="card-topline">
                  <span className="card-item-title text-technical">T{fact.tick} / {formatDisplayValue(fact.source).toUpperCase()}</span>
                  <span className="card-sub-tag">CONFIDENCE {Math.round(fact.confidence * 100)}%</span>
                </div>
                <p className="card-desc">{formatDisplayValue(fact.statement)}</p>
                <div className="card-meta-line">
                  <span className="meta-label">DISCOVERER</span>
                  <span className="meta-value">{formatDisplayValue(world.characters[fact.discovered_by]?.name || fact.discovered_by)}</span>
                </div>
              </div>
            ))
          )
        )}

        {tab === 'unknown' && (
          uninspected.length === 0 ? (
            <div className="empty-quiet">ALL OBJECTS HAVE BEEN INSPECTED.</div>
          ) : (
            uninspected.map((obj) => (
              <div key={obj.id} className="noir-card mystery-card">
                <div className="card-topline">
                  <span className="card-item-title">{formatDisplayValue(obj.name)}</span>
                  <span className="card-sub-tag text-muted">UNINSPECTED</span>
                </div>
                <p className="card-desc">Properties unknown. No character has observed this item closely.</p>
                <div className="card-meta-line">
                  <span className="meta-label">PRESENCE</span>
                  <span className="meta-value">
                    {obj.location_id ? formatDisplayValue(world.locations[obj.location_id]?.name || 'Container') : 'Unknown'}
                  </span>
                </div>
              </div>
            ))
          )
        )}
      </div>
    </div>
  );
};
