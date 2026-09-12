export type StoryInputType = 'beginning' | 'midpoint' | 'ending' | 'full_concept';

export interface ProjectMetadata {
  id: string;
  title: string;
  seed_prompt: string;
  input_type?: string;
  target_duration_minutes?: number;
  created_at: string;
  updated_at: string;
  current_tick: number;
  total_events: number;
  total_scenes: number;
  total_panels?: number;
}

export interface ActorVisualProfile {
  character_id: string;
  name: string;
  age: string;
  face_traits: string;
  hairstyle: string;
  build: string;
  clothing: string;
  signature_items: string[];
  emotional_style: string;
}

export interface LocationVisualProfile {
  location_id: string;
  name: string;
  environment_type: string;
  lighting: string;
  layout: string;
  palette: string;
  mood: string;
}

export interface ObjectVisualProfile {
  object_id: string;
  name: string;
  material: string;
  size: string;
  color: string;
  condition: string;
  unique_markers: string;
}

export interface Location {
  id: string;
  name: string;
  description: string;
  connected_locations: string[];
  capacity?: number;
  visual_profile?: LocationVisualProfile;
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
  visual_profile?: ActorVisualProfile;
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
  visual_profile?: ObjectVisualProfile;
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

export interface ActBeat {
  beat_number: number;
  act: string;
  title: string;
  description: string;
  conflict: string;
  location_hint: string;
  tension_level: number;
}

export interface StoryOutline {
  input_type: StoryInputType;
  raw_input: string;
  episode_title: string;
  genre: string;
  tone: string;
  target_duration_minutes: number;
  premise: string;
  dramatic_question: string;
  act_structure: Record<string, string>;
  key_scenes: ActBeat[];
  climax: string;
  resolution: string;
  subplot_hooks: string[];
}

export interface StorySynopsis {
  title: string;
  logline: string;
  paragraph_summary: string;
  full_synopsis: string;
  dramatic_question: string;
  genre: string;
  tone: string;
  target_duration_minutes: number;
  acts: Record<string, string>;
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

export type ShotPurpose =
  | 'establish'
  | 'introduce_character'
  | 'action'
  | 'dialogue'
  | 'reaction'
  | 'revelation'
  | 'clue'
  | 'threat'
  | 'transition'
  | 'climax'
  | 'resolution';

export type StoryboardImageStatus =
  | 'planned'
  | 'queued'
  | 'generating'
  | 'ready'
  | 'failed'
  | 'fallback';

export type PageLayoutTemplate =
  | 'template_a'
  | 'template_b'
  | 'template_c'
  | 'template_d';

export interface StoryboardImageVersion {
  version: number;
  image_url: string;
  prompt_used?: string;
  negative_prompt?: string;
  provider?: string;
  mode?: 'ai_image' | 'fallback_comic';
  created_at?: string;
  is_selected?: boolean;
  render_metadata?: Record<string, any>;
}

export interface StoryboardStyleProfile {
  id: string;
  name: string;
  medium: string;
  linework: string;
  lighting_style: string;
  color_palette: string;
  composition_rules: string;
  artist_influences: string[];
  negative_constraints: string;
}

export interface CharacterVisualReference {
  character_id: string;
  name: string;
  role?: string;
  age?: string;
  build?: string;
  face_features?: string;
  hair?: string;
  clothing?: string;
  signature_props?: string[];
  color_accents?: string;
  expression_tendency?: string;
  reference_image_url?: string;
}

export interface ObjectVisualReference {
  object_id: string;
  name: string;
  form_factor?: string;
  materials?: string;
  colors?: string;
  unique_markings?: string;
  condition?: string;
  reference_image_url?: string;
}

export interface LocationVisualReference {
  location_id: string;
  name: string;
  environment_type?: string;
  architecture?: string;
  lighting_setup?: string;
  color_palette?: string;
  key_landmarks?: string[];
  mood?: string;
  reference_image_url?: string;
}

export interface VisualBible {
  style_profile: StoryboardStyleProfile;
  characters: Record<string, CharacterVisualReference>;
  objects: Record<string, ObjectVisualReference>;
  locations: Record<string, LocationVisualReference>;
}

export interface ContinuityIssue {
  panel_id: string;
  severity: 'warning' | 'info' | 'error';
  category: string;
  message: string;
  suggestion: string;
}

export interface ContinuityReport {
  score: number;
  is_valid: boolean;
  total_panels: number;
  issues: ContinuityIssue[];
  shot_variety_score: number;
  character_consistency_score: number;
  prop_tracking_score: number;
}

export interface StoryboardPanel {
  id: string;
  panel_id?: string;
  project_id?: string;
  scene_id?: string;
  scene_number: number;
  panel_number: number;
  shot_number?: number;
  page_number?: number;
  shot_type: string;
  camera_angle: string;
  narrative_purpose?: ShotPurpose | string;
  lens_feel?: string;
  composition?: string;
  subject_focus?: string;
  layout_slot?: string;
  location_id: string;
  location_name?: string;
  characters_present: string[];
  character_names?: string[];
  objects_in_frame?: string[];
  action?: string;
  action_description: string;
  visual_description?: string;
  lighting?: string;
  mood?: string;
  style_profile_id?: string;
  prompt?: string;
  image_prompt?: string;
  visual_prompt: string;
  compiled_prompt?: string;
  negative_prompt?: string;
  style_tags?: string[];
  character_references?: Record<string, string>;
  object_references?: Record<string, string>;
  location_reference?: string;
  caption?: string;
  dialogue_excerpt?: string | null;
  dialogue_bubble_type?: 'speech' | 'whisper' | 'shout' | 'thought' | 'caption';
  sfx_label?: string;
  continuity_notes?: string;
  image_asset_id?: string;
  image_url?: string | null;
  rendered_image_url?: string | null;
  rendered_svg?: string | null;
  image_status?: StoryboardImageStatus | string;
  provider?: string;
  generation_version?: number;
  selected_version?: number;
  versions?: StoryboardImageVersion[];
  aspect_ratio: string;
  source_event_ids: string[];
  source_screenplay_block_ids?: string[];
  metadata?: Record<string, any>;
}

export interface StoryboardPage {
  page_number: number;
  total_pages: number;
  title?: string;
  layout_template?: PageLayoutTemplate | string;
  panels: StoryboardPanel[];
}

export interface ShotPlan {
  project_title: string;
  total_panels: number;
  total_pages?: number;
  panels_per_page?: number;
  panels: StoryboardPanel[];
  pages?: StoryboardPage[];
  aspect_ratio: string;
  density_mode?: string;
  storyboard_coverage?: Record<string, any>;
}

export interface RenderedPanelData {
  panel_id?: string;
  panel_number?: number;
  scene_number?: number;
  shot_number?: number;
  page_number?: number;
  shot_type?: string;
  camera_angle?: string;
  image_url?: string;
  rendered_svg?: string;
  render_type?: string;
  provider?: string;
  mode?: string;
  status?: string;
  version?: number;
  svg_data?: string;
  prompt_used?: string;
  negative_prompt?: string;
  continuity_notes?: string;
  caption?: string;
  is_mock?: boolean;
  metadata?: Record<string, any>;
}

export interface StoryboardResponse {
  shot_plan: ShotPlan;
  rendered_panels: Array<string | RenderedPanelData>;
  continuity_report?: ContinuityReport;
}

export type ActiveView = 'home' | 'world' | 'actors' | 'simulation' | 'script' | 'storyboard' | 'export';

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
  story_outline?: StoryOutline;
  synopsis?: StorySynopsis;
  shot_plan?: ShotPlan;
  rendered_panels?: any[];
  storyboard?: StoryboardResponse;
}
