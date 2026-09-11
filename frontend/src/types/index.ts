export interface ProjectMetadata {
  id: string;
  title: string;
  seed_prompt: string;
  created_at: string;
  updated_at: string;
  current_tick: number;
  total_events: number;
  total_scenes: number;
}

export interface Location {
  id: string;
  name: string;
  description: string;
  connected_locations: string[];
  capacity?: number;
}

export interface EmotionalState {
  happiness: number;
  fear: number;
  anger: number;
  trust: number;
  curiosity: number;
}

export interface DiscoveredFact {
  id: string;
  statement: string;
  source: string;
  confidence: number;
  discovered_by: string;
  tick: number;
  related_entities: string[];
  metadata?: Record<string, any>;
}

export interface Character {
  id: string;
  name: string;
  role: string;
  location_id: string;
  goals: string[];
  beliefs: string[];
  secrets: string[];
  relationships: string[];
  emotional_state: EmotionalState;
  known_facts?: string[];
  inventory?: string[];
}

export interface WorldObject {
  id: string;
  name: string;
  description: string;
  location_id: string | null;
  holder_id: string | null;
  portable: boolean;
  properties: Record<string, any>;
  inspected_by?: string[];
}

export interface Goal {
  id: string;
  character_id: string;
  description: string;
  priority: number;
  status: string;
  reason?: string;
  progress?: number;
}

export interface Belief {
  id: string;
  character_id: string;
  statement: string;
  confidence: number;
  source?: string;
}

export interface Secret {
  id: string;
  character_id: string;
  statement: string;
  known_by: string[];
  importance: number;
}

export interface Event {
  id: string;
  tick: number;
  event_type: string;
  actor_ids: string[];
  location_id: string | null;
  description: string;
  metadata: Record<string, any>;
}

export interface WorldState {
  id: string;
  name: string;
  description: string;
  current_tick: number;
  locations: Record<string, Location>;
  characters: Record<string, Character>;
  objects: Record<string, WorldObject>;
  goals: Record<string, Goal>;
  beliefs: Record<string, Belief>;
  secrets: Record<string, Secret>;
  events: Record<string, Event>;
  facts?: Record<string, DiscoveredFact>;
}

export interface NarrativeBeat {
  id: string;
  beat_type: string;
  start_tick: number;
  end_tick: number;
  location_id: string;
  character_ids: string[];
  dramatic_score: number;
  summary: string;
  source_event_ids: string[];
}

export interface NarrativeEventSelection {
  total_events_observed: number;
  filtered_beats: NarrativeBeat[];
  dramatic_arc_summary: string;
  tension_progression: number[];
}

export interface ScreenplayBlock {
  id: string;
  block_type: string;
  text: string;
  source_event_ids: string[];
  character_id?: string;
}

export interface ScreenplayScene {
  scene_number: number;
  location_id: string;
  heading: string;
  blocks: ScreenplayBlock[];
  source_event_ids: string[];
}

export interface ScreenplayDocument {
  title: string;
  credit: string;
  author: string;
  draft_date: string;
  scenes: ScreenplayScene[];
}

export interface StoryboardPanel {
  id: string;
  scene_number: number;
  panel_number: number;
  shot_number?: number;
  shot_type: string;
  camera_angle: string;
  location_id: string;
  location_name?: string;
  characters_present: string[];
  character_names?: string[];
  action?: string;
  action_description: string;
  visual_description?: string;
  lighting?: string;
  mood?: string;
  prompt?: string;
  dialogue_excerpt?: string | null;
  visual_prompt: string;
  aspect_ratio: string;
  source_event_ids: string[];
  source_screenplay_block_ids?: string[];
  metadata?: Record<string, any>;
}

export interface ShotPlan {
  project_title: string;
  total_panels: number;
  panels: StoryboardPanel[];
  aspect_ratio: string;
}

export interface RenderedPanelData {
  panel_id?: string;
  panel_number?: number;
  render_type?: string;
  svg_data?: string;
  prompt_used?: string;
  is_mock?: boolean;
}

export interface StoryboardResponse {
  shot_plan: ShotPlan;
  rendered_panels: Array<string | RenderedPanelData>;
}

export type ActiveView = 'home' | 'world' | 'actors' | 'simulation' | 'script' | 'storyboard';

export interface EventCausality {
  eventId: string;
  actorName: string;
  actorRole: string;
  goalDescription: string;
  beliefStatement: string;
  memoryExcerpt: string;
  emotionalSummary: string;
  actionSummary: string;
  resultSummary: string;
  stateDelta: string;
}

export interface ProjectData {
  metadata: ProjectMetadata;
  world: WorldState;
  selection?: NarrativeEventSelection;
  screenplay?: ScreenplayDocument;
  fountain_text?: string;
  storyboard?: StoryboardResponse;
}
