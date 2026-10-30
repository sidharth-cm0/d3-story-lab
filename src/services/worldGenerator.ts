/**
 * D3 Story Lab — Premise-Driven Procedural World Generator
 *
 * Constructs genuinely new, premise-specific worlds without hardcoded scenario
 * lock-in. Analyzes premise semantics and utilizes deterministic PRNG streams
 * to synthesize locations, sovereign characters, objects, goals, secrets,
 * and narrative blueprints.
 */

import {
  WorldState,
  Location,
  Character,
  WorldObject,
  Goal,
  Belief,
  Secret,
  Relationship,
  StoryBlueprint,
  StoryOutline,
  StorySynopsis,
  ProjectData,
  ProjectMetadata,
  StoryInputType,
  StoryStructureType,
  ArchetypeType,
} from '../types';
import { Mulberry32, createSimulationStreams } from './prng';
import { STORY_STRUCTURES } from './simulationEngine';

export interface WorldGenerationOptions {
  seedPrompt: string;
  title?: string;
  inputType?: StoryInputType;
  targetDurationMinutes?: number;
  structureMode?: string;
  structureType?: string;
  secondaryStructure?: string;
  presentationStrategy?: string;
  seed?: number | string;
  lifecycleMode?: 'new_simulation' | 'replay' | 'alternative_run' | 'branch';
  parentSimulationId?: string | null;
  forkTick?: number | null;
}

type GenreTheme =
  | 'SCI_FI'
  | 'MEDICAL'
  | 'WESTERN'
  | 'COURTROOM'
  | 'SUBMARINE'
  | 'GOTHIC_MYSTERY'
  | 'CYBERPUNK'
  | 'ESPIONAGE_NOIR'
  | 'GENERAL_DRAMA';

interface GenreOntology {
  theme: GenreTheme;
  genreName: string;
  tone: string;
  defaultLocations: Array<{ name: string; desc: string; capacity: number }>;
  maleNames: string[];
  femaleNames: string[];
  roles: Array<{ role: string; archetype: ArchetypeType; want: string; need: string; fear: string }>;
  objects: Array<{ name: string; desc: string; portable: boolean; properties: Record<string, any> }>;
  secretTemplates: string[];
  conflictTypes: string[];
}

const GENRE_ONTOLOGIES: Record<GenreTheme, GenreOntology> = {
  SCI_FI: {
    theme: 'SCI_FI',
    genreName: 'Hard Sci-Fi Suspense',
    tone: 'Clinical, claustrophobic, high-stakes',
    defaultLocations: [
      { name: 'Command Bridge', desc: 'Central observation hub pressurized under emergency red auxiliary lighting.', capacity: 6 },
      { name: 'Atmospheric Airlock Beta', desc: 'Reinforced decompression chamber overlooking the planetary void.', capacity: 4 },
      { name: 'Sub-Core Engineering Bay', desc: 'Vibrating heavy deck housing the primary magnetic containment manifold.', capacity: 8 },
    ],
    maleNames: ['Cmdr. David Vance', 'Engineer Caleb Mercer', 'Dr. Julian Thorne', 'Specialist Marcus Kane'],
    femaleNames: ['Dr. Sarah Lin', 'Pilot Elena Rostova', 'Chief Engineer Maya Torres', 'Officer Teresa Chen'],
    roles: [
      { role: 'Mission Commander', archetype: 'RULER', want: 'Maintain mission parameters and stabilize the station', need: 'Accept that survival requires sacrificing the corporate payload', fear: 'Dereliction of duty and crew mutiny' },
      { role: 'Chief Science Officer', archetype: 'SAGE', want: 'Preserve the anomalous extraterrestrial specimen', need: 'Acknowledge the physical hazard the research presents to human life', fear: 'Destruction of decades of scientific breakthrough' },
      { role: 'Life-Support Specialist', archetype: 'HERO', want: 'Ration remaining oxygen reserves for all survivors', need: 'Make peace with the impossible triage decisions ahead', fear: 'Suffocating before exfiltration arrives' },
    ],
    objects: [
      { name: 'Cryogenic Specimen Container', desc: 'Hermetically sealed cannister with flashing warning diodes.', portable: true, properties: { biohazard: true, temperature_kelvin: 90 } },
      { name: 'Emergency Oxygen Bypass Regulator', desc: 'Heavy brass pneumatic valve with mechanical pressure gauge.', portable: true, properties: { functional: true, oxygen_flow_pct: 45 } },
      { name: 'Telemetry Flight Recorder', desc: 'Reinforced optical black box containing corrupted sensor data.', portable: true, properties: { encrypted: true, integrity_pct: 68 } },
      { name: 'Manual Bulkhead Override Terminal', desc: 'Hydraulic lever console welded to the bulkhead wall.', portable: false, properties: { power_active: false, key_required: true } },
    ],
    secretTemplates: [
      'Knows the catastrophic power failure was caused by unauthorized deep-core drilling.',
      'Secretly altered telemetry logs to conceal early contamination readings.',
      'Possesses the single override keycard capable of ejecting the compromised wing.',
    ],
    conflictTypes: ['resource_competition', 'moral_conflict', 'power_conflict'],
  },
  MEDICAL: {
    theme: 'MEDICAL',
    genreName: 'Clinical Bio-Medical Drama',
    tone: 'Tense, analytical, urgent',
    defaultLocations: [
      { name: 'Triage Intensive Care Ward', desc: 'Beeping monitors and curtained bays under sterile fluorescent illumination.', capacity: 10 },
      { name: 'Pathology Isolation Suite', desc: 'Negative-pressure laboratory with glove boxes and centrifuge racks.', capacity: 4 },
      { name: 'Administrative Boardroom', desc: 'Wood-paneled executive chamber overlooking the hospital ambulance bay.', capacity: 8 },
    ],
    maleNames: ['Dr. Robert Sterling', 'Chief Surgeon Alan Morales', 'Administrator Edward Hayes', 'Dr. Nathan Brooks'],
    femaleNames: ['Dr. Claire Bennett', 'Epidemiologist Miriam Vance', 'Director Naomi Patel', 'Nurse Supervisor Laura Cruz'],
    roles: [
      { role: 'Attending Physician', archetype: 'HERO', want: 'Administer experimental antidote to patient zero immediately', need: 'Recognize the risk of uncontrolled clinical trial failure', fear: 'Losing patients under their direct supervision' },
      { role: 'Hospital Bio-Ethicist', archetype: 'SAGE', want: 'Halt unapproved treatments until FDA emergency authorization clears', need: 'Understand that rigid ethics without empathy causes avoidable loss', fear: 'Legal catastrophe and institutional liability' },
      { role: 'Pharmaceutical Director', archetype: 'RULER', want: 'Protect company clinical patents and triage disclosure', need: 'Confront their complicity in suppressing side-effect data', fear: 'Criminal prosecution and public disgrace' },
    ],
    objects: [
      { name: 'Unlabeled Antiviral Vial', desc: 'Centrifuged amber serum labeled with clinical trial ID #904.', portable: true, properties: { doses_remaining: 3, temperature_sensitive: true } },
      { name: 'Electronic Medical Record Tablet', desc: 'Password-locked tablet displaying contradictory patient vitals.', portable: true, properties: { battery_pct: 35, confidential: true } },
      { name: 'Centrifuge Calibration Unit', desc: 'Stainless steel benchtop device with digital rpm readout.', portable: false, properties: { calibrated: true } },
    ],
    secretTemplates: [
      'Authorized early clinical trials knowing the serum was chemically unstable.',
      'Knows the contaminated vaccine batch originated in their private research lab.',
      'Withheld the patient diagnosis to prevent quarantine panic.',
    ],
    conflictTypes: ['value_opposition', 'moral_conflict', 'resource_competition'],
  },
  WESTERN: {
    theme: 'WESTERN',
    genreName: 'Frontier Noir Western',
    tone: 'Dusty, stoic, morally ambiguous',
    defaultLocations: [
      { name: 'Dusty Creek Saloon', desc: 'Weathered cedar bar with oil lanterns and swinging louvered batwing doors.', capacity: 12 },
      { name: 'Sheriff Office & Jail', desc: 'Adobe masonry building with two iron-barred cells and a potbelly stove.', capacity: 6 },
      { name: 'Overland Rail Depot', desc: 'Telegraph office and wooden passenger platform beside narrow-gauge tracks.', capacity: 10 },
    ],
    maleNames: ['Marshal Cole Callahan', 'Silas Vance', 'Preacher Thomas Wade', 'Doc Henry Holliday', 'Bounty Hunter Jesse Vance'],
    femaleNames: ['Saloon Proprietor Clara Ross', 'Widow Martha Sterling', 'Telegrapher Cora Bell', 'Judith Blackwood'],
    roles: [
      { role: 'Town Marshal', archetype: 'RULER', want: 'Hold the prisoner until the federal circuit judge arrives on the midnight train', need: 'Acknowledge that law and justice are no longer the same thing in this territory', fear: 'Vigilante mob hanging the prisoner and burning the town' },
      { role: 'Accused Outlaw', archetype: 'OUTLAW', want: 'Escape custody before corrupt deputies stage an attempted break', need: 'Take responsibility for the innocent lives endangered by the gang', fear: 'Facing the noose for a killing someone else committed' },
      { role: 'Disillusioned Banker', archetype: 'EVERYMAN', want: 'Recover the stolen land deeds before foreclosure notices publish', need: 'Stand up against the cattle baron syndicate', fear: 'Financial destitution and violence' },
    ],
    objects: [
      { name: 'Iron Safe Key', desc: 'Heavy brass skeleton key stamped with Wells Fargo emblem.', portable: true, properties: { brass: true, cuts: 4 } },
      { name: 'Water-Damaged Land Deed', desc: 'Parchment bearing county seal and controversial boundary survey lines.', portable: true, properties: { legally_binding: true, disputed: true } },
      { name: 'Winchester Model 1873 Carbine', desc: 'Well-oiled lever-action rifle with walnut stock.', portable: true, properties: { rounds_loaded: 8, caliber: '.44-40' } },
      { name: 'Western Union Telegraph Key', desc: 'Brass sounder mounted to oak desk in the depot corner.', portable: false, properties: { wire_cut: false } },
    ],
    secretTemplates: [
      'Personally pocketed half the bank payroll shipment during the robbery confusion.',
      'Knows the outlaw did not fire the fatal shot that killed the deputy.',
      'Received a coded wire warning that the rail company intends to burn the depot.',
    ],
    conflictTypes: ['goal_opposition', 'moral_conflict', 'historical_grievance'],
  },
  COURTROOM: {
    theme: 'COURTROOM',
    genreName: 'Judicial Legal Drama',
    tone: 'Deliberative, razor-sharp, forensic',
    defaultLocations: [
      { name: 'Superior Courtroom 4B', desc: 'High mahogany bench with witness stand, jury box, and spectators gallery.', capacity: 20 },
      { name: 'Judges Private Chambers', desc: 'Book-lined study with leather armchairs and legal volumes.', capacity: 6 },
      { name: 'Subterranean Evidence Locker', desc: 'Steel-mesh security repository under strict chain-of-custody logging.', capacity: 4 },
    ],
    maleNames: ['Defense Counsel Arthur Finch', 'Prosecutor Victor Cross', 'Judge Harold Sterling', 'Detective Ray Donovan'],
    femaleNames: ['Public Defender Rachel Stone', 'Lead Prosecutor Diana Mercer', 'Whistleblower Evelyn Ward', 'Judge Miriam Vance'],
    roles: [
      { role: 'Lead Defense Attorney', archetype: 'HERO', want: 'Expose the falsified forensics report and secure a full acquittal', need: 'Recognize that clearing the client may ruin their own career and family life', fear: 'An innocent defendant sentenced to maximum penalty' },
      { role: 'Special Prosecutor', archetype: 'RULER', want: 'Deliver an unassailable guilty verdict to consolidate public reputation', need: 'Accept that procedural shortcuts have corrupted the integrity of the prosecution', fear: 'Case dismissal and judicial sanction' },
      { role: 'Forensic Whistleblower', archetype: 'SAGE', want: 'Enter the unredacted digital audit logs into official court record', need: 'Overcome fear of retribution from police leadership', fear: 'Physical retaliation and disbarment' },
    ],
    objects: [
      { name: 'Chain-of-Custody Manifest', desc: 'Official blue folder detailing custody transfers and signature anomalies.', portable: true, properties: { stamped: true, evidence_id: 'EX-412' } },
      { name: 'Audio Dictaphone Cassette', desc: 'Magnetic tape containing off-the-record conversation with the star witness.', portable: true, properties: { playable: true, minutes: 18 } },
      { name: 'Judicial Gavel & Sound Block', desc: 'Polished walnut gavel resting on the high bench.', portable: false, properties: { official: true } },
    ],
    secretTemplates: [
      'Suppressed exculpatory blood splatter evidence during preliminary discovery.',
      'Knows the star witness was paid a consulting retainer by the prosecution.',
      'Personally drafted the disputed financial contract before switching to the bench.',
    ],
    conflictTypes: ['goal_opposition', 'value_opposition', 'secret_exposure_risk'],
  },
  SUBMARINE: {
    theme: 'SUBMARINE',
    genreName: 'Naval Sub-Surface Thriller',
    tone: 'Claustrophobic, hydraulic, atmospheric pressure',
    defaultLocations: [
      { name: 'Command Control Center', desc: 'Glow of sonar scopes, diving planes consoles, and periscope well.', capacity: 10 },
      { name: 'Forward Torpedo Room', desc: 'Racks of heavy ordnance beneath dripping condenser pipes.', capacity: 8 },
      { name: 'Reactor Auxiliary Space', desc: 'Shielded tunnel flanked by lead-lined cooling water conduits.', capacity: 5 },
    ],
    maleNames: ['Capt. Thomas Hayes', 'Executive Officer William Scott', 'Chief of the Boat Frank Russo', 'Sonarman Ryan Miller'],
    femaleNames: ['Lt. Cmdr. Kelly Vance', 'Reactor Officer Elena Voronin', 'Dr. Janet Thorne', 'Chief Engineer Maya Collins'],
    roles: [
      { role: 'Commanding Officer', archetype: 'RULER', want: 'Complete the covert reconnaissance patrol without acoustic detection', need: 'Relinquish authoritarian isolation and listen to junior officers warnings', fear: 'Loss of vessel and international confrontation' },
      { role: 'Executive Officer', archetype: 'HERO', want: 'Surface immediately to vent contaminated nitrogen from the bilge', need: 'Challenge the captain direct order before catastrophic hull failure occurs', fear: 'Being court-martialed for insubordination' },
      { role: 'Chief Sonar Operator', archetype: 'SAGE', want: 'Classify an anomalous acoustic contact tracking them in the thermocline', need: 'Trust acoustic instincts over faulty automated combat algorithms', fear: 'Leading the submarine into an unmapped underwater trench' },
    ],
    objects: [
      { name: 'Emergency Surface Key', desc: 'Double-bitted red brass key used to authorize ballast blow.', portable: true, properties: { critical: true, authorized: false } },
      { name: 'Atmospheric Gas Analyzer', desc: 'Portable sensor displaying rising carbon dioxide percentages.', portable: true, properties: { co2_ppm: 3400, battery_hrs: 2 } },
      { name: 'Acoustic Sonar Array Console', desc: 'Phosphor screen displaying active ping sweeps and contact tracks.', portable: false, properties: { operational: true } },
    ],
    secretTemplates: [
      'Knows the main ballast tank has a hairline fracture that will fail past crush depth.',
      'Received secret coded orders to abandon the distress submarine without transmitting.',
      'Deliberately jammed the sonar hydrophone to conceal an acoustic anomaly.',
    ],
    conflictTypes: ['power_conflict', 'resource_competition', 'moral_conflict'],
  },
  GOTHIC_MYSTERY: {
    theme: 'GOTHIC_MYSTERY',
    genreName: 'Gothic Noir Mystery',
    tone: 'Decadent, eerie, psychological suspense',
    defaultLocations: [
      { name: 'Manor Great Library', desc: 'Two-story book-lined chamber with tall mullioned windows rattling in the storm.', capacity: 12 },
      { name: 'Conservatory & Greenhouse', desc: 'Damp glass pavilion filled with overgrown rare orchids and dripping rainwater.', capacity: 8 },
      { name: 'Cellar Vault & Wine Crypt', desc: 'Cold vaulted brick cellar smelling of moss, damp earth, and aged port.', capacity: 6 },
    ],
    maleNames: ['Lord Alistair Sterling', 'Dr. Francis Crane', 'Valet Thomas Finch', 'Inspector Charles Vance'],
    femaleNames: ['Lady Eleanor Blackwood', 'Governess Margaret Ward', 'Heiress Beatrice Sinclair', 'Genevieve Thorne'],
    roles: [
      { role: 'Family Physician', archetype: 'SAGE', want: 'Determine the true physiological cause of the patriarch sudden collapse', need: 'Overcome fear of confronting high-society benefactors with ugly truths', fear: 'Being implicated in administering a lethal prescription' },
      { role: 'Disinherited Heir', archetype: 'OUTLAW', want: 'Locate and destroy the revised testamentary codicil before morning', need: 'Realize that inherited wealth will not redeem their damaged conscience', fear: 'Arrest for conspiracy to defraud the estate' },
      { role: 'Household Keeper', archetype: 'CAREGIVER', want: 'Shield the young heir from the dark history concealed within the manor', need: 'Reveal the family secret before someone else is poisoned', fear: 'Losing home and protection' },
    ],
    objects: [
      { name: 'Wax-Sealed Testamentary Codicil', desc: 'Vellum legal document altering inheritance distribution.', portable: true, properties: { sealed: true, dated: 'October 14' } },
      { name: 'Apothecary Poison Phial', desc: 'Dark cobalt glass bottle containing trace tincture of digitalis.', portable: true, properties: { poison: true, empty: false } },
      { name: 'Heavy Grandfather Clock', desc: 'Carved mahogany pendulum clock ticking loudly in the corner.', portable: false, properties: { secret_compartment: true } },
    ],
    secretTemplates: [
      'Knows the poison was slipped into the evening tea service by someone in this room.',
      'Forged the testator signature on the primary real estate deed.',
      'Possesses the original wedding registry proving the heir is illegitimate.',
    ],
    conflictTypes: ['secret_exposure_risk', 'historical_grievance', 'moral_conflict'],
  },
  CYBERPUNK: {
    theme: 'CYBERPUNK',
    genreName: 'Cyberpunk Corporate Noir',
    tone: 'Rain-soaked neon, chrome, ruthless corporate espionage',
    defaultLocations: [
      { name: 'Sub-Level Server Cleanroom', desc: 'Chilled nitrogen-cooled data vaults flanked by glowing fiber optic bundles.', capacity: 6 },
      { name: 'Chiba Alley Clinic', desc: 'Back-alley cybernetic surgical clinic beneath flickering holographic billboards.', capacity: 5 },
      { name: 'Penthouse Executive Helipad', desc: 'Wet asphalt platform buffeted by gale winds high above the megacity smog.', capacity: 10 },
    ],
    maleNames: ['Hacker Silas Reed', 'Enforcer Jaxson Cross', 'Dr. Kenji Sato', 'Fixer Victor Vance'],
    femaleNames: ['Infiltrator Nova Lin', 'Corpo Executive Lyra Sterling', 'Street Doc Riko Tanaka', 'Courier Maya Thorne'],
    roles: [
      { role: 'Netrunner Infiltrator', archetype: 'OUTLAW', want: 'Extract the neural architecture schematic before the ICE counter-hack fries their cortex', need: 'Learn to trust a team member rather than solo rogue survivalism', fear: 'Total neural wipe by corporate sentinels' },
      { role: 'Corporate Security Asset', archetype: 'RULER', want: 'Reclaim the proprietary algorithm and terminate the data leak at its source', need: 'Confront the reality that the corporation considers them entirely disposable', fear: 'Contract termination and neural deactivation' },
      { role: 'Street Ripperdoc', archetype: 'MAGICIAN', want: 'Secure enough raw bio-materials to keep the free clinic operational', need: 'Stop laundering stolen cyberware for criminal syndicates', fear: 'Raid by corporate tactical squads' },
    ],
    objects: [
      { name: 'Military-Grade Neural Shunt', desc: 'Gold-plated fiber optic jack with biometric authentication lights.', portable: true, properties: { bandwidth_tb: 100, military_spec: true } },
      { name: 'Encrypted Optical Storage Crystal', desc: 'Glowing glass prism containing 50 petabytes of synthetic memory data.', portable: true, properties: { encrypted: true, hardware_locked: true } },
      { name: 'Cybernetic Diagnostic Cradle', desc: 'Reclining surgical chair equipped with laser scalpels and neuro-monitors.', portable: false, properties: { powered: true } },
    ],
    secretTemplates: [
      'Engineered the system vulnerability that let the netrunner breach the security perimeter.',
      'Carries a sleeper neuro-virus in their neural cyberware that will erase all witnesses.',
      'Is acting as a double agent for a rival megacorporation.',
    ],
    conflictTypes: ['goal_opposition', 'resource_competition', 'secret_exposure_risk'],
  },
  ESPIONAGE_NOIR: {
    theme: 'ESPIONAGE_NOIR',
    genreName: 'Cold War Forensic Espionage',
    tone: 'Smoky, measured, paranoid, razor-sharp',
    defaultLocations: [
      { name: 'Safehouse Radio Room', desc: 'Basement sanctuary with blacked-out windows, cigarette smoke, and shortwave radio.', capacity: 6 },
      { name: 'Border Crossing Checkpoint', desc: 'Spotlit barrier arm between concrete guard booths in the driving rain.', capacity: 8 },
      { name: 'Diplomatic Archive Anteroom', desc: 'Quiet corridor outside consular offices with locked brass mail slots.', capacity: 6 },
    ],
    maleNames: ['Agent Donald Sterling', 'Director Vincent Kane', 'Operative Paul Ross', 'Attache Felix Vance'],
    femaleNames: ['Operative Evelyn Vance', 'Courier Anna Bell', 'Analyst Nadia Rostova', 'Diplomat Claire Morales'],
    roles: [
      { role: 'Covert Field Agent', archetype: 'HERO', want: 'Exfiltrate with verified intelligence before the border gate seals permanently', need: 'Recognize that intelligence agencies treat agents as expendable assets', fear: 'Interrogation in an undisclosed black site' },
      { role: 'Counter-Intelligence Chief', archetype: 'RULER', want: 'Plug the internal intelligence leak and protect agency political standing', need: 'Acknowledge that systemic corruption cannot be patched by hunting scapegoats', fear: 'Public exposure of administrative failures' },
      { role: 'Station Radio Operator', archetype: 'EVERYMAN', want: 'Transmit the distress message and evacuate before the location is raided', need: 'Choose moral duty over instinctive self-preservation', fear: 'Capture and summary execution' },
    ],
    objects: [
      { name: 'One-Time Cipher Pad', desc: 'Small paper booklet printed with random numerical groups for decryption.', portable: true, properties: { secret: true, pages_left: 4 } },
      { name: 'Miniature Surveillance Camera', desc: 'Matchbox-sized sub-miniature camera with spring-loaded shutter.', portable: true, properties: { film_exposures: 14, loaded: true } },
      { name: 'Shortwave Transceiver Console', desc: 'Heavy tube-powered radio chassis with headphone jacks and frequency dial.', portable: false, properties: { tuned_freq: '7.850 MHz' } },
    ],
    secretTemplates: [
      'Suppressed evidence that the enemy station was already abandoned.',
      'Ordered the execution of an asset to protect their personal cover.',
      'Holds duplicate microfilm containing unredacted list of double agents.',
    ],
    conflictTypes: ['goal_opposition', 'secret_exposure_risk', 'power_conflict'],
  },
  GENERAL_DRAMA: {
    theme: 'GENERAL_DRAMA',
    genreName: 'Grounded Character Drama',
    tone: 'Psychological, realistic, observant',
    defaultLocations: [
      { name: 'Family Living Quarters', desc: 'Warmly lit interior space cluttered with generational relics and unpacked crates.', capacity: 8 },
      { name: 'Administrative Office', desc: 'Modest office space with metal filing cabinets and an overcast street view.', capacity: 6 },
      { name: 'Public Courtyard Garden', desc: 'Open brick terrace flanked by cedar benches and autumn leaves.', capacity: 15 },
    ],
    maleNames: ['Arthur Vance', 'Marcus Reed', 'David Sterling', 'Thomas Ross'],
    femaleNames: ['Elena Mercer', 'Clara Hughes', 'Sarah Chen', 'Rachel Morales'],
    roles: [
      { role: 'Family Custodian', archetype: 'CAREGIVER', want: 'Keep the household united despite overwhelming economic and social debt', need: 'Stop shielding adult relatives from the consequences of their choices', fear: 'Complete fragmentation of the family' },
      { role: 'Ambitious Successor', archetype: 'EXPLORER', want: 'Sell the ancestral property to fund a transformative business venture', need: 'Recognize the human value of legacy and shared memories', fear: 'Stagnating in a dying hometown' },
      { role: 'Estranged Relative', archetype: 'OUTLAW', want: 'Demand their legal share of the estate settlement before moving on', need: 'Acknowledge their own guilt in the historical estrangement', fear: 'Remaining an unwanted outsider forever' },
    ],
    objects: [
      { name: 'Antique Ledger Book', desc: 'Leather-bound journal recording forty years of private family debts and gifts.', portable: true, properties: { handwritten: true, valuable: true } },
      { name: 'Sealed Envelope from Attorney', desc: 'Heavy parchment envelope with unsealed flap marked PERSONAL AND CONFIDENTIAL.', portable: true, properties: { unread: true } },
      { name: 'Iron Garden Bench', desc: 'Weathered wrought-iron bench bolted to the flagstone courtyard.', portable: false, properties: { solid: true } },
    ],
    secretTemplates: [
      'Sold the family land rights months ago without telling anyone.',
      'Knows the deceased relative left a private letter forgiving the debt.',
      'Secretly accepted a severance buyout conditioned on abandoning the lawsuit.',
    ],
    conflictTypes: ['value_opposition', 'historical_grievance', 'moral_conflict'],
  },
};

function hasKeyword(text: string, keywords: string[]): boolean {
  return keywords.some((kw) => {
    if (kw.includes(' ') || kw.includes('-')) {
      return text.includes(kw);
    }
    return new RegExp(`\\b${kw}\\b`, 'i').test(text);
  });
}

/**
 * Detects the genre theme from semantic prompt analysis.
 */
export function detectGenreTheme(prompt: string): GenreTheme {
  const p = prompt.toLowerCase();

  if (
    hasKeyword(p, [
      'space', 'orbital', 'alien', 'planet', 'station', 'starship', 'astronaut',
      'europa', 'outpost', 'sub-surface', 'airlock', 'telemetry', 'astrobiologist',
      'lunar', 'mars', 'cryo', 'shuttle', 'zero-g', 'spacecraft'
    ])
  ) {
    return 'SCI_FI';
  }
  if (
    hasKeyword(p, [
      'hospital', 'doctor', 'surgeon', 'patient', 'virus', 'vaccine', 'triage',
      'clinic', 'sanatorium', 'antiviral', 'epidemic', 'pathology', 'operating room'
    ])
  ) {
    return 'MEDICAL';
  }
  if (
    hasKeyword(p, [
      'saloon', 'sheriff', 'outlaw', 'cowboy', 'marshal', 'frontier', 'western',
      'desert', 'ranch', 'dusty creek', 'winchester', 'revolver', 'gunslinger'
    ])
  ) {
    return 'WESTERN';
  }
  if (
    hasKeyword(p, [
      'court', 'courtroom', 'trial', 'judge', 'lawyer', 'attorney', 'prosecutor',
      'prosecution', 'verdict', 'jury', 'indictment', 'subpoena'
    ])
  ) {
    return 'COURTROOM';
  }
  if (
    hasKeyword(p, [
      'submarine', 'torpedo', 'sonar', 'dive', 'depth', 'naval', 'hull',
      'periscope', 'ballast'
    ])
  ) {
    return 'SUBMARINE';
  }
  if (
    hasKeyword(p, [
      'manor', 'mansion', 'poison', 'will', 'inheritance', 'gothic', 'curse',
      'estate', 'seance', 'crypt', 'ancestral'
    ])
  ) {
    return 'GOTHIC_MYSTERY';
  }
  if (
    hasKeyword(p, [
      'cyber', 'hacker', 'megacorp', 'neural', 'ai', 'android', 'neon',
      'implant', 'omnicorp', 'netrunner', 'cyberware', 'cyberspace'
    ])
  ) {
    return 'CYBERPUNK';
  }
  if (
    hasKeyword(p, [
      'infiltrate', 'infiltration', 'dossier', 'operative', 'spy', 'covert',
      'counter-intelligence', 'vault', 'wiretap', 'espionage', 'kgb', 'cia', 'safehouse'
    ])
  ) {
    return 'ESPIONAGE_NOIR';
  }
  return 'GENERAL_DRAMA';
}

const LOCATION_AND_ORG_TERMS = new Set([
  'Tower', 'Building', 'Outpost', 'Station', 'Facility', 'Hospital',
  'Sanatorium', 'Clinic', 'Center', 'Deck', 'Bay', 'Office', 'Corp',
  'Room', 'Alley', 'Street', 'Avenue', 'Sector', 'Vault', 'Sub-Surface',
  'SubSurface', 'Compound', 'Corridor', 'Lab', 'Laboratory', 'Ward', 'Hotel'
]);

const LEADING_PREPOSITIONS = new Set([
  'The', 'An', 'A', 'In', 'On', 'At', 'When', 'After', 'Before', 'And', 'Or', 'If', 'Within', 'During', 'Under'
]);

/**
 * Extracts explicit character names from a prompt while filtering out location/org phrases.
 */
export function extractNamesFromPrompt(prompt: string): string[] {
  const matches: string[] = [];
  const words = prompt.split(/\s+/);

  for (let i = 0; i < words.length - 1; i++) {
    const w1 = words[i].replace(/[^a-zA-Z]/g, '');
    const w2 = words[i + 1].replace(/[^a-zA-Z]/g, '');
    if (w1 && w2 && w1[0] === w1[0].toUpperCase() && w2[0] === w2[0].toUpperCase()) {
      if (!LEADING_PREPOSITIONS.has(w1) && !LOCATION_AND_ORG_TERMS.has(w2) && !LOCATION_AND_ORG_TERMS.has(w1)) {
        matches.push(`${w1} ${w2}`);
      }
    }
  }

  // Also catch single names following professional titles: Dr. Vance, Chief Miller, Auditor Vane, etc.
  for (let i = 0; i < words.length - 1; i++) {
    const w1 = words[i].replace(/[^a-zA-Z.]/g, '');
    const w2 = words[i + 1].replace(/[^a-zA-Z]/g, '');
    if (['Dr.', 'Doctor', 'Chief', 'Marshal', 'Officer', 'Agent', 'Surgeon', 'Auditor', 'Courier', 'Baron'].includes(w1)) {
      if (w2 && w2[0] === w2[0].toUpperCase() && !LOCATION_AND_ORG_TERMS.has(w2)) {
        const titleName = `${w1} ${w2}`;
        if (!matches.some((m) => m.includes(w2))) {
          matches.push(titleName);
        }
      }
    }
  }

  return matches;
}

/**
 * Generates an initial state fingerprint for validation and reproducibility checking.
 * Evaluates canonical world state structure (actors, locations, objects, goals, secrets).
 */
export function computeWorldFingerprint(world: WorldState): string {
  const charSummary = Object.values(world.characters)
    .map((c) => `${c.id}:${c.name}:${c.role}:${c.location_id}:${(c.inventory || []).join(',')}`)
    .sort()
    .join('|');
  const locSummary = Object.values(world.locations)
    .map((l) => `${l.id}:${l.name}:${(l.connected_locations || []).join(',')}`)
    .sort()
    .join('|');
  const objSummary = Object.values(world.objects)
    .map((o) => `${o.id}:${o.name}:${o.location_id || ''}:${o.holder_id || ''}`)
    .sort()
    .join('|');
  const goalSummary = Object.values(world.goals)
    .map((g) => `${g.id}:${g.character_id}:${g.description}`)
    .sort()
    .join('|');
  const secretSummary = Object.values(world.secrets)
    .map((s) => `${s.id}:${s.character_id}:${s.statement}`)
    .sort()
    .join('|');
  return Mulberry32.hashString(`${charSummary}#${locSummary}#${objSummary}#${goalSummary}#${secretSummary}`).toString(16);
}

let projectInstanceSeq = 0;

/**
 * Procedurally generates a complete, validated WorldState from prompt & seed.
 */
export function generateProceduralWorld(options: WorldGenerationOptions): ProjectData {
  const seedVal = options.seed !== undefined ? options.seed : Date.now();
  const streams = createSimulationStreams(seedVal);
  const theme = detectGenreTheme(options.seedPrompt);
  const ontology = GENRE_ONTOLOGIES[theme];

  const projectId = `proj_${Date.now().toString(36)}_${(++projectInstanceSeq).toString(36)}_${streams.worldGen.nextInt(1000, 9999).toString(36)}`;

  // 1. Determine Title
  const computedTitle =
    options.title && options.title.trim()
      ? options.title.trim()
      : options.seedPrompt.length > 38
      ? options.seedPrompt.substring(0, 35).trim() + '...'
      : options.seedPrompt.trim() || `${ontology.genreName} Incident`;

  // 2. Generate Locations with Topological Adjacency
  const locations: Record<string, Location> = {};
  const locDefs = ontology.defaultLocations;
  const locIds = locDefs.map((_, i) => `loc_${i + 1}`);

  locDefs.forEach((def, i) => {
    const connected: string[] = [];
    if (i > 0) connected.push(locIds[i - 1]);
    if (i < locDefs.length - 1) connected.push(locIds[i + 1]);

    locations[locIds[i]] = {
      id: locIds[i],
      name: def.name,
      description: def.desc,
      connected_locations: connected,
      capacity: def.capacity,
    };
  });

  // 3. Generate Sovereign Characters
  const explicitNames = extractNamesFromPrompt(options.seedPrompt);
  const numCharacters = 2; // Strict 2-3 character focus for high dramatic tension
  const characters: Record<string, Character> = {};
  const goals: Record<string, Goal> = {};
  const beliefs: Record<string, Belief> = {};
  const secrets: Record<string, Secret> = {};

  const namePool = streams.characterInit.shuffle([...ontology.femaleNames, ...ontology.maleNames]);

  for (let c = 0; c < numCharacters; c++) {
    const charId = `char_${c + 1}`;
    const name = explicitNames[c] || namePool[c] || `Agent ${c + 1}`;
    const roleDef = ontology.roles[c % ontology.roles.length];

    // Assign starting locations with deterministic PRNG influence
    // Character 1 starts at loc 0; Character 2 starts at loc 0 or loc 1 based on PRNG stream
    const startLocId = c === 0 ? locIds[0] : locIds[streams.characterInit.nextInt(0, Math.min(1, locIds.length - 1))];

    // Character Goal
    const goalId = `goal_${c + 1}`;
    goals[goalId] = {
      id: goalId,
      character_id: charId,
      description: roleDef.want,
      priority: 0.9 + c * 0.05,
      status: 'ACTIVE',
      reason: roleDef.need,
    };

    // Character Private Secret
    const secretId = `sec_${c + 1}`;
    secrets[secretId] = {
      id: secretId,
      character_id: charId,
      statement: ontology.secretTemplates[c % ontology.secretTemplates.length],
      known_by: [], // Strictly private
      importance: 0.85 + c * 0.05,
    };

    // Character Subjective Belief
    const beliefId = `bel_${c + 1}`;
    beliefs[beliefId] = {
      id: beliefId,
      character_id: charId,
      statement: c === 0
        ? `Adversaries are actively monitoring operations in ${locations[startLocId].name}.`
        : `Immediate tactical compromise is required before external pressure escalates.`,
      confidence: 0.8 + streams.characterInit.nextFloat() * 0.15,
      source: 'initial_briefing',
    };

    characters[charId] = {
      id: charId,
      name,
      role: roleDef.role,
      location_id: startLocId,
      goals: [goalId],
      beliefs: [beliefId],
      secrets: [secretId],
      relationships: ['rel_primary'],
      emotional_state: {
        happiness: 0.2 + streams.characterInit.nextFloat() * 0.2,
        fear: 0.4 + streams.characterInit.nextFloat() * 0.3,
        anger: 0.2 + streams.characterInit.nextFloat() * 0.3,
        trust: 0.3 + streams.characterInit.nextFloat() * 0.2,
        curiosity: 0.7 + streams.characterInit.nextFloat() * 0.25,
      },
      inventory: [],
      dynamics: {
        core_value: roleDef.archetype === 'HERO' ? 'Integrity' : roleDef.archetype === 'RULER' ? 'Order' : 'Discovery',
        conscious_want: roleDef.want,
        dramatic_need: roleDef.need,
        fear: roleDef.fear,
        primary_archetype: roleDef.archetype,
        secondary_archetype: 'OUTLAW',
      },
      reference_profile: {
        apparent_age_range: c === 0 ? '30-36' : '45-52',
        build: 'Operational, disciplined posture',
        face_description: 'Focused expression, alert gaze',
        baseline_wardrobe: theme === 'SCI_FI' ? 'Pressurized utility flight suit' : theme === 'WESTERN' ? 'Weathered canvas duster over denim' : 'Tailored charcoal woolen overcoat',
        signature_objects: [c === 0 ? 'Analog chronometer' : 'Signet ring'],
        reference_mode: 'TEXT_ONLY',
      },
    };
  }

  // 4. Generate Interactive Objects
  const objects: Record<string, WorldObject> = {};
  ontology.objects.forEach((objDef, idx) => {
    const objId = `obj_${idx + 1}`;
    // First object in initial location; others distributed based on world PRNG stream
    const locId = idx === 0 ? locIds[0] : locIds[streams.worldGen.nextInt(0, locIds.length - 1)];
    // Give one object directly to Character 1
    const holderId = idx === 0 && objDef.portable ? Object.keys(characters)[0] : null;

    objects[objId] = {
      id: objId,
      name: objDef.name,
      description: objDef.desc,
      location_id: holderId ? null : locId,
      holder_id: holderId,
      portable: objDef.portable,
      properties: objDef.properties,
    };

    if (holderId && characters[holderId]) {
      characters[holderId].inventory = characters[holderId].inventory || [];
      characters[holderId].inventory!.push(objId);
    }
  });

  // 5. Generate Initial Interpersonal Relationship
  const charKeys = Object.keys(characters);
  const relationships: Record<string, Relationship> = {
    rel_primary: {
      id: 'rel_primary',
      character_a_id: charKeys[0],
      character_b_id: charKeys[1],
      affinity: 0.35 + streams.characterInit.nextFloat() * 0.2,
      trust: 0.25 + streams.characterInit.nextFloat() * 0.2,
      suspicion: 0.65 + streams.characterInit.nextFloat() * 0.2,
      power_imbalance: 0.4,
      history: `Longstanding professional association in ${ontology.genreName}, now strained by conflicting mandates regarding ${objects[Object.keys(objects)[0]].name}.`,
    },
  };

  // 6. Generate Initial Inciting Event
  const initialEventId = `evt_initial_0`;
  const initialEvent = {
    id: initialEventId,
    tick: 1,
    event_type: 'INITIAL_BREACH',
    actor_ids: [charKeys[0]],
    location_id: characters[charKeys[0]].location_id,
    description: `${characters[charKeys[0]].name} enters ${locations[characters[charKeys[0]].location_id].name} to begin operations as the crisis unfolds.`,
    metadata: {
      tension: 0.45,
      source: 'initial_premise',
      seed: streams.masterSeed,
      causal_relation: 'SETUP',
    },
  };

  const world: WorldState = {
    id: projectId,
    name: computedTitle,
    description: options.seedPrompt,
    current_tick: 1,
    locations,
    characters,
    objects,
    goals,
    beliefs,
    secrets,
    relationships,
    events: { [initialEventId]: initialEvent },
  };

  // 7. Derive Story Blueprint
  const structType: StoryStructureType = (options.structureType as StoryStructureType) || 'THREE_ACT';
  const matchingDef = STORY_STRUCTURES.find((s) => s.structure_type === structType) || STORY_STRUCTURES[0];

  const blueprint: StoryBlueprint = {
    story_title: computedTitle,
    primary_structure: structType,
    secondary_structure: (options.secondaryStructure as StoryStructureType) || null,
    presentation_strategy: options.presentationStrategy || 'CHRONOLOGICAL',
    target_duration_minutes: options.targetDurationMinutes || 20,
    thematic_premise: `${characters[charKeys[0]].name} must reconcile duty with survival when confronting ${characters[charKeys[1]].name}.`,
    dramatic_question: `Will ${characters[charKeys[0]].name} achieve their objective before ${locations[locIds[locIds.length - 1]].name} is permanently lost?`,
    stakes: `Catastrophic operational failure in ${ontology.genreName}`,
    expected_beats: matchingDef.beats,
    soft_constraints: {
      max_ticks: 25,
      allowed_interventions: ['director_pressure_check', 'external_deadline'],
    },
    metadata: {
      seed: streams.masterSeed,
      genre_theme: theme,
      lifecycle_mode: options.lifecycleMode || 'new_simulation',
      initial_fingerprint: computeWorldFingerprint(world),
    },
  };

  // 8. Construct Metadata
  const metadata: ProjectMetadata = {
    id: projectId,
    title: computedTitle,
    seed_prompt: options.seedPrompt,
    input_type: options.inputType || 'beginning',
    target_duration_minutes: options.targetDurationMinutes || 20,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    current_tick: 1,
    total_events: 1,
    total_scenes: 0,
    total_panels: 0,
  };

  // Attach seed & lifecycle metadata extensions
  (metadata as any).seed = streams.masterSeed;
  (metadata as any).lifecycle_mode = options.lifecycleMode || 'new_simulation';
  (metadata as any).parent_simulation_id = options.parentSimulationId || null;
  (metadata as any).initial_state_fingerprint = computeWorldFingerprint(world);
  (metadata as any).genre_theme = theme;

  const project: ProjectData = {
    metadata,
    world,
    story_blueprint: blueprint,
    story_outline: {
      input_type: options.inputType || 'beginning',
      raw_input: options.seedPrompt,
      episode_title: computedTitle,
      genre: ontology.genreName,
      tone: ontology.tone,
      target_duration_minutes: options.targetDurationMinutes || 20,
      premise: options.seedPrompt,
      dramatic_question: blueprint.dramatic_question,
      act_structure: {
        'Act I': `Setup in ${locations[locIds[0]].name}`,
        'Act II': `Confrontation over ${objects[Object.keys(objects)[0]].name}`,
        'Act III': `Final resolution at ${locations[locIds[locIds.length - 1]].name}`,
      },
      key_scenes: [],
      climax: `Direct moral confrontation between ${characters[charKeys[0]].name} and ${characters[charKeys[1]].name}`,
      resolution: `New operational status established under verified evidence`,
      subplot_hooks: [`Secret discovery regarding ${secrets[Object.keys(secrets)[0]].statement}`],
    },
    synopsis: {
      title: computedTitle,
      logline: options.seedPrompt,
      paragraph_summary: `In a tense ${ontology.genreName} scenario, ${characters[charKeys[0]].name} and ${characters[charKeys[1]].name} collide within ${locations[locIds[0]].name}. Their autonomous interactions govern the emergence of an organic narrative without puppetry.`,
      full_synopsis: `An emergent story unfolding across ${locDefs.length} distinct locations, guided by bounded perception and verifiable causal events.`,
      dramatic_question: blueprint.dramatic_question,
      genre: ontology.genreName,
      tone: ontology.tone,
      target_duration_minutes: options.targetDurationMinutes || 20,
      acts: { 'Act I': 'The Threshold', 'Act II': 'The Impasse', 'Act III': 'The Reckoning' },
    },
  };

  return project;
}
