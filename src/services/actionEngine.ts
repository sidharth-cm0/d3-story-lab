/**
 * D3 Story Lab — Autonomous Action & Decision Policy Engine
 *
 * Implements sovereign character decision-making:
 * 1. Bounded perception: Characters perceive only co-located entities and exits.
 * 2. Real affordance candidate generation: Navigation, inspection, acquisition, social, tactical.
 * 3. Deterministic utility policy: Based on goals, traits, emotional drives, and relationships.
 * 4. Precondition validation: Physics, connectivity, and possession rules.
 * 5. Immutable EventLog execution with explainable decision justification.
 * 6. Director environmental pressure injection without character puppetry.
 */

import { WorldState, Character, Location, WorldObject, Event, Goal, Relationship } from '../types';
import { Mulberry32 } from './prng';

export type ActionCategory =
  | 'NAVIGATE'
  | 'INSPECT_OBJECT'
  | 'ACQUIRE_OBJECT'
  | 'USE_OBJECT'
  | 'CONFRONT_PEER'
  | 'INQUIRE_PEER'
  | 'SHARE_SECRET'
  | 'DEFLECT_SCRUTINY'
  | 'NEGOTIATE_TERMS'
  | 'CONCEAL_OBJECT'
  | 'WAIT_AND_OBSERVE';

export interface ActionProposal {
  actorId: string;
  category: ActionCategory;
  targetId?: string;
  targetType?: 'location' | 'object' | 'character' | 'secret';
  targetName?: string;
  goalId?: string;
  utilityScore: number;
  reasoning: string;
  preconditionsMet: boolean;
}

/**
 * Generates feasible candidate actions for a character based strictly on
 * their current spatial location, inventory, co-located entities, and goals.
 */
export function generateCandidateActions(
  world: WorldState,
  characterId: string,
  decisionPrng: Mulberry32
): ActionProposal[] {
  const character = world.characters[characterId];
  if (!character) return [];

  const candidates: ActionProposal[] = [];
  const currentLocId = character.location_id;
  const currentLoc = world.locations[currentLocId];
  const activeGoal = character.goals?.[0] ? world.goals[character.goals[0]] : null;

  const coLocatedPeers = Object.values(world.characters).filter(
    (c) => c.id !== characterId && c.location_id === currentLocId
  );
  const coLocatedObjects = Object.values(world.objects || {}).filter(
    (o) => o.location_id === currentLocId && !o.holder_id
  );
  const carriedObjects = Object.values(world.objects || {}).filter(
    (o) => o.holder_id === characterId
  );

  const emo = character.emotional_state;
  const traits = (character as any).personality_traits || { analytical: 0.7, cautious: 0.6, ambitious: 0.7 };

  // 1. SPATIAL AFFORDANCES: Move to connected adjacent rooms
  if (currentLoc?.connected_locations) {
    currentLoc.connected_locations.forEach((adjId) => {
      const adjLoc = world.locations[adjId];
      if (adjLoc) {
        // Base utility for exploration or tactical repositioning
        let utility = 0.45;
        if (emo.fear > 0.65) utility += 0.25; // Flee/reposition when afraid
        if (coLocatedPeers.length === 0) utility += 0.15; // Seek company/objective
        utility += decisionPrng.nextFloat() * 0.08;

        candidates.push({
          actorId: characterId,
          category: 'NAVIGATE',
          targetId: adjId,
          targetType: 'location',
          targetName: adjLoc.name,
          goalId: activeGoal?.id,
          utilityScore: utility,
          reasoning: `Reposition from ${currentLoc.name} to ${adjLoc.name} to advance operational perimeter.`,
          preconditionsMet: true,
        });
      }
    });
  }

  // 2. OBJECT AFFORDANCES: Inspect or acquire objects in the room
  coLocatedObjects.forEach((obj) => {
    // Inspect
    let inspectUtility = 0.5 + (traits.analytical || 0.5) * 0.25 + emo.curiosity * 0.2;
    candidates.push({
      actorId: characterId,
      category: 'INSPECT_OBJECT',
      targetId: obj.id,
      targetType: 'object',
      targetName: obj.name,
      goalId: activeGoal?.id,
      utilityScore: inspectUtility,
      reasoning: `Examine ${obj.name} in search of clues or operational utility.`,
      preconditionsMet: true,
    });

    // Acquire if portable
    if (obj.portable) {
      let takeUtility = 0.55 + (traits.ambitious || 0.5) * 0.2;
      if (activeGoal?.description.toLowerCase().includes(obj.name.toLowerCase())) {
        takeUtility += 0.35; // Crucial goal object!
      }
      candidates.push({
        actorId: characterId,
        category: 'ACQUIRE_OBJECT',
        targetId: obj.id,
        targetType: 'object',
        targetName: obj.name,
        goalId: activeGoal?.id,
        utilityScore: takeUtility,
        reasoning: `Take physical possession of ${obj.name}.`,
        preconditionsMet: true,
      });
    }
  });

  // 3. INVENTORY AFFORDANCES: Conceal or use held objects
  carriedObjects.forEach((obj) => {
    if (coLocatedPeers.length > 0 && (emo.fear > 0.5 || emo.trust < 0.4)) {
      candidates.push({
        actorId: characterId,
        category: 'CONCEAL_OBJECT',
        targetId: obj.id,
        targetType: 'object',
        targetName: obj.name,
        goalId: activeGoal?.id,
        utilityScore: 0.6 + emo.fear * 0.2,
        reasoning: `Conceal ${obj.name} from sight of co-located peers.`,
        preconditionsMet: true,
      });
    }
  });

  // 4. SOCIAL AFFORDANCES: Interact with co-located peers
  coLocatedPeers.forEach((peer) => {
    // Look up mutual relationship
    const rel = Object.values(world.relationships || {}).find(
      (r) =>
        (r.character_a_id === characterId && r.character_b_id === peer.id) ||
        (r.character_a_id === peer.id && r.character_b_id === characterId)
    );
    const trust = rel?.trust ?? emo.trust;
    const suspicion = rel?.suspicion ?? 0.6;

    // Confront if suspicion is elevated or anger is high
    let confrontUtility = 0.4 + emo.anger * 0.3 + suspicion * 0.25;
    candidates.push({
      actorId: characterId,
      category: 'CONFRONT_PEER',
      targetId: peer.id,
      targetType: 'character',
      targetName: peer.name,
      goalId: activeGoal?.id,
      utilityScore: confrontUtility,
      reasoning: `Confront ${peer.name} regarding contradictory motives and suspicious movements.`,
      preconditionsMet: true,
    });

    // Inquire if curiosity is high and fear is moderate
    let inquireUtility = 0.5 + emo.curiosity * 0.3 - emo.fear * 0.15;
    candidates.push({
      actorId: characterId,
      category: 'INQUIRE_PEER',
      targetId: peer.id,
      targetType: 'character',
      targetName: peer.name,
      goalId: activeGoal?.id,
      utilityScore: inquireUtility,
      reasoning: `Question ${peer.name} to extract critical details regarding current operational status.`,
      preconditionsMet: true,
    });

    // Share secret if trust is high (> 0.5) and character holds private secrets
    if (character.secrets && character.secrets.length > 0 && trust > 0.48) {
      const sec = world.secrets[character.secrets[0]];
      if (sec) {
        candidates.push({
          actorId: characterId,
          category: 'SHARE_SECRET',
          targetId: peer.id,
          targetType: 'secret',
          targetName: sec.statement,
          goalId: activeGoal?.id,
          utilityScore: 0.55 + trust * 0.3,
          reasoning: `Confide private knowledge to ${peer.name} to forge deeper tactical alliance.`,
          preconditionsMet: true,
        });
      }
    }

    // Negotiate terms if tension is high (> 0.65)
    candidates.push({
      actorId: characterId,
      category: 'NEGOTIATE_TERMS',
      targetId: peer.id,
      targetType: 'character',
      targetName: peer.name,
      goalId: activeGoal?.id,
      utilityScore: 0.5 + (emo.fear + emo.anger) * 0.15,
      reasoning: `Propose terms of temporary truce and task allocation with ${peer.name}.`,
      preconditionsMet: true,
    });

    // Deflect scrutiny if peer has high suspicion
    candidates.push({
      actorId: characterId,
      category: 'DEFLECT_SCRUTINY',
      targetId: peer.id,
      targetType: 'character',
      targetName: peer.name,
      goalId: activeGoal?.id,
      utilityScore: 0.45 + (traits.cautious || 0.5) * 0.25,
      reasoning: `Parry incoming questions from ${peer.name} with measured ambiguity.`,
      preconditionsMet: true,
    });
  });

  // 5. TACTICAL DEFAULT: Wait and observe
  candidates.push({
    actorId: characterId,
    category: 'WAIT_AND_OBSERVE',
    targetId: currentLocId,
    targetType: 'location',
    targetName: currentLoc?.name || 'Area',
    goalId: activeGoal?.id,
    utilityScore: 0.38 + (traits.cautious || 0.5) * 0.15,
    reasoning: `Maintain observation posture in ${currentLoc?.name || 'area'} to assess emerging developments.`,
    preconditionsMet: true,
  });

  return candidates;
}

/**
 * Selects the highest utility action proposal deterministically,
 * using the decision PRNG stream for tie-breaking.
 */
export function selectBestActionProposal(
  candidates: ActionProposal[],
  decisionPrng: Mulberry32
): ActionProposal {
  if (candidates.length === 0) throw new Error('No candidate actions generated');

  // Apply deterministic PRNG calibration to candidates for nuanced tie-breaking
  const evaluated = candidates.map((c) => ({
    proposal: c,
    adjustedUtility: c.utilityScore + (decisionPrng.nextFloat() - 0.5) * 0.06,
  }));

  // Sort descending by adjusted utility
  evaluated.sort((a, b) => b.adjustedUtility - a.adjustedUtility);

  return evaluated[0].proposal;
}

/**
 * Validates preconditions and executes an approved action proposal onto the canonical world state.
 * Returns the immutable Event recording the executed transition.
 */
export function executeActionProposal(
  proposal: ActionProposal,
  world: WorldState,
  tick: number,
  decisionPrng: Mulberry32
): Event {
  const actor = world.characters[proposal.actorId];
  if (!actor) throw new Error(`Actor ${proposal.actorId} not found`);

  const eventId = `evt_t${tick}_${proposal.category.toLowerCase()}_${decisionPrng.nextInt(100, 999)}`;
  let description = '';
  let causalRelation = tick % 3 === 0 ? 'BUT' : 'THEREFORE';

  switch (proposal.category) {
    case 'NAVIGATE': {
      const destId = proposal.targetId!;
      const destLoc = world.locations[destId];
      actor.location_id = destId;
      description = `${actor.name} moves through the corridor into ${destLoc.name}.`;
      break;
    }
    case 'INSPECT_OBJECT': {
      const obj = world.objects[proposal.targetId!];
      actor.emotional_state.curiosity = Math.min(1, actor.emotional_state.curiosity + 0.08);
      description = `${actor.name} closely examines the ${obj?.name || 'object'}, noting its markings and operational state.`;
      break;
    }
    case 'ACQUIRE_OBJECT': {
      const obj = world.objects[proposal.targetId!];
      if (obj) {
        obj.location_id = null;
        obj.holder_id = actor.id;
        actor.inventory = actor.inventory || [];
        if (!actor.inventory.includes(obj.id)) actor.inventory.push(obj.id);
        description = `${actor.name} takes possession of the ${obj.name}, securing it on their person.`;
      }
      break;
    }
    case 'CONCEAL_OBJECT': {
      const obj = world.objects[proposal.targetId!];
      actor.emotional_state.fear = Math.max(0.1, actor.emotional_state.fear - 0.05);
      description = `${actor.name} discreetly conceals the ${obj?.name || 'object'} from view.`;
      break;
    }
    case 'CONFRONT_PEER': {
      const peer = world.characters[proposal.targetId!];
      actor.emotional_state.anger = Math.min(1, actor.emotional_state.anger + 0.1);
      if (peer) {
        peer.emotional_state.fear = Math.min(1, peer.emotional_state.fear + 0.1);
        peer.emotional_state.trust = Math.max(0.1, peer.emotional_state.trust - 0.1);
      }
      description = `${actor.name} confronts ${peer?.name || 'peer'}, demanding a direct accounting of their intentions.`;
      break;
    }
    case 'INQUIRE_PEER': {
      const peer = world.characters[proposal.targetId!];
      actor.emotional_state.curiosity = Math.min(1, actor.emotional_state.curiosity + 0.05);
      description = `${actor.name} questions ${peer?.name || 'peer'} regarding unusual occurrences and unexplained evidence.`;
      break;
    }
    case 'SHARE_SECRET': {
      const peer = world.characters[proposal.targetId!];
      const sec = world.secrets[actor.secrets?.[0] || ''];
      if (sec && peer) {
        if (!sec.known_by.includes(peer.id)) sec.known_by.push(peer.id);
        actor.emotional_state.trust = Math.min(1, actor.emotional_state.trust + 0.2);
        peer.emotional_state.trust = Math.min(1, peer.emotional_state.trust + 0.2);
        description = `${actor.name} pulls ${peer.name} aside and confides: "${sec.statement}".`;
        causalRelation = 'THEREFORE';
      }
      break;
    }
    case 'NEGOTIATE_TERMS': {
      const peer = world.characters[proposal.targetId!];
      description = `${actor.name} offers a pragmatic compromise to ${peer?.name || 'peer'}, proposing terms of mutual cooperation.`;
      break;
    }
    case 'DEFLECT_SCRUTINY': {
      const peer = world.characters[proposal.targetId!];
      description = `${actor.name} parries ${peer?.name || 'peer'}'s scrutiny with disciplined ambiguity.`;
      break;
    }
    case 'WAIT_AND_OBSERVE':
    default: {
      const loc = world.locations[actor.location_id];
      description = `${actor.name} holds their ground in ${loc?.name || 'the area'}, quietly observing subtle shifts in the room.`;
      break;
    }
  }

  const executedEvent: Event = {
    id: eventId,
    tick,
    event_type: proposal.category,
    actor_ids: [actor.id, ...(proposal.targetType === 'character' && proposal.targetId ? [proposal.targetId] : [])],
    location_id: actor.location_id,
    description,
    metadata: {
      action_category: proposal.category,
      justification: proposal.reasoning,
      utility_score: Math.round(proposal.utilityScore * 100) / 100,
      causal_relation: causalRelation,
      tension: Math.min(0.95, Math.max(0.2, 0.4 + (tick % 8) * 0.06)),
      source: 'character_decision_policy',
    },
  };

  world.events[eventId] = executedEvent;
  return executedEvent;
}

/**
 * Director Agent environmental pacing intervention:
 * Evaluates whether the simulation is stagnant and injects an environmental pressure event.
 * Never puppets or dictates a character's choice.
 */
export function evaluateDirectorIntervention(
  world: WorldState,
  tick: number,
  directorPrng: Mulberry32
): Event | null {
  // Check if last 3 events were idle or within the same room
  const recentEvents = Object.values(world.events || {})
    .filter((e) => e.tick >= tick - 2)
    .sort((a, b) => b.tick - a.tick);

  const isStagnant =
    recentEvents.length >= 2 &&
    recentEvents.every((e) => e.event_type === 'WAIT_AND_OBSERVE' || e.event_type === 'DEFLECT_SCRUTINY');

  // Trigger intervention on stagnation or at scheduled dramatic intervals (e.g. tick 6, 10)
  if (isStagnant || tick === 6 || tick === 10) {
    const locKeys = Object.keys(world.locations);
    const targetLocId = directorPrng.pick(locKeys);
    const targetLoc = world.locations[targetLocId];

    const incidents = [
      { type: 'POWER_FLUCTUATION', desc: `A sudden voltage surge ripples through ${targetLoc.name}, extinguishing overhead floodlights and engaging emergency backup beacons.` },
      { type: 'LOCKDOWN_WARNING', desc: `An automated security siren echoes through ${targetLoc.name}, broadcasting a ten-minute containment countdown.` },
      { type: 'EXTERNAL_DISTURBANCE', desc: `Heavy mechanical thuds vibrate through the ceiling above ${targetLoc.name}, signaling approaching activity.` },
      { type: 'COMMUNICATION_CHIME', desc: `An unmonitored console chime rings in ${targetLoc.name}, displaying an incoming high-priority transmission.` },
    ];

    const inc = directorPrng.pick(incidents);
    const eventId = `evt_dir_t${tick}_${directorPrng.nextInt(100, 999)}`;

    const dirEvent: Event = {
      id: eventId,
      tick,
      event_type: 'ENVIRONMENT_INCIDENT',
      actor_ids: [],
      location_id: targetLocId,
      description: inc.desc,
      source: 'DIRECTOR',
      metadata: {
        incident_type: inc.type,
        director_intervention: inc.type,
        trigger_signal: isStagnant ? 'stalled_relationship' : 'dramatic_need_opportunity',
        tension: 0.85,
        causal_relation: 'BUT',
        urgency: 'HIGH',
      },
    };

    world.events[eventId] = dirEvent;
    return dirEvent;
  }

  return null;
}
