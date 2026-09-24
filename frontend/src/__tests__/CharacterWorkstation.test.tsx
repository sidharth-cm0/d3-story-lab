import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CharacterWorkstation } from '../components/CharacterWorkstation';
import * as api from '../api';
import { CharacterProfileDraft, CompletenessReport, CharacterInput } from '../types';

vi.mock('../api', async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    intakeCharacter: vi.fn(),
    enrichCharacterDraft: vi.fn(),
    lockCharacterField: vi.fn(),
    unlockCharacterField: vi.fn(),
    acceptCharacterDraft: vi.fn(),
  };
});

describe('CharacterWorkstation Component (Phase A)', () => {
  const mockProjectId = 'proj_test_001';

  const mockDraft: CharacterProfileDraft = {
    id: 'draft_123',
    project_id: mockProjectId,
    name: 'Marcus Vance',
    role: 'Homicide Detective',
    description: 'A sharp investigator',
    personality_traits: { cautious: 0.8, observant: 0.9 },
    goals: ['Solve the docks murder'],
    secrets: ['Was at the crime scene'],
    beliefs: ['Partner is withholding files'],
    emotional_state: { fear: 0.2, anger: 0.1, trust: -0.3, curiosity: 0.7 },
    provenance: {
      name: {
        field_name: 'name',
        authority: 'USER_PREFERRED',
        source_snippet: 'Marcus Vance',
        created_at: '2026-09-24T12:00:00Z',
      },
      role: {
        field_name: 'role',
        authority: 'USER_PREFERRED',
        source_snippet: 'Detective',
        created_at: '2026-09-24T12:00:00Z',
      },
      goals: {
        field_name: 'goals',
        authority: 'USER_PREFERRED',
        source_snippet: 'Solve the docks murder',
        created_at: '2026-09-24T12:00:00Z',
      },
      secrets: {
        field_name: 'secrets',
        authority: 'USER_PREFERRED',
        source_snippet: 'Was at the crime scene',
        created_at: '2026-09-24T12:00:00Z',
      },
    },
    created_at: '2026-09-24T12:00:00Z',
    updated_at: '2026-09-24T12:00:00Z',
  };

  const mockCompleteness: CompletenessReport = {
    score: 85.0,
    normalized_score: 0.85,
    is_complete: true,
    missing_fields: ['visual_profile'],
    present_fields: ['name', 'role', 'goals', 'secrets', 'beliefs', 'personality_traits'],
    field_scores: { name: 15, role: 15, goals: 20, secrets: 15, beliefs: 5, personality_traits: 15 },
    weights: { name: 15, role: 15, goals: 20, secrets: 15, beliefs: 5, personality_traits: 15, visual_profile: 15 },
  };

  const mockInput: CharacterInput = {
    id: 'cinp_999',
    project_id: mockProjectId,
    raw_text: 'Detective Marcus Vance...',
    created_at: '2026-09-24T12:00:00Z',
    linked_character_id: 'draft_123',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders initial Quick Description mode by default', () => {
    render(<CharacterWorkstation projectId={mockProjectId} />);
    expect(screen.getByText(/CHARACTER WORKSTATION/i)).toBeTruthy();
    expect(screen.getByText(/Quick Description \(NL\)/i)).toBeTruthy();
    expect(screen.getByText(/Guided Profile \(Form\)/i)).toBeTruthy();
    expect(screen.getByPlaceholderText(/e\.g\. Detective Marcus Vance/i)).toBeTruthy();
  });

  it('switches to Guided Profile mode when tab is clicked', () => {
    render(<CharacterWorkstation projectId={mockProjectId} />);
    const guidedTab = screen.getByText(/Guided Profile \(Form\)/i);
    fireEvent.click(guidedTab);

    expect(screen.getByText(/Character Name \*/i)).toBeTruthy();
    expect(screen.getByText(/Role \/ Profession \*/i)).toBeTruthy();
    expect(screen.getAllByText(/🔒 Lock Value/i).length).toBeGreaterThan(0);
  });

  it('normalizes free-text description and transitions to Review Panel', async () => {
    vi.mocked(api.intakeCharacter).mockResolvedValueOnce({
      input: mockInput,
      draft: mockDraft,
      completeness: mockCompleteness,
    });

    render(<CharacterWorkstation projectId={mockProjectId} />);
    const textarea = screen.getByPlaceholderText(/e\.g\. Detective Marcus Vance/i);
    fireEvent.change(textarea, { target: { value: 'Detective Marcus Vance wants to solve the murder.' } });

    const normalizeBtn = screen.getByText(/Normalize & Review Profile/i);
    fireEvent.click(normalizeBtn);

    await waitFor(() => {
      expect(api.intakeCharacter).toHaveBeenCalledWith(
        mockProjectId,
        'Detective Marcus Vance wants to solve the murder.',
        undefined,
        false
      );
    });

    // Review Panel elements
    expect(await screen.findByText(/PROFILE COMPLETENESS/i)).toBeTruthy();
    expect(screen.getByText('85%')).toBeTruthy();
    expect(screen.getByText(/READY FOR CAST/i)).toBeTruthy();
    expect(screen.getAllByText(/Marcus Vance/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Homicide Detective/i)).toBeTruthy();
    expect(screen.getAllByText(/👤 USER/i).length).toBeGreaterThan(0);
  });

  it('toggles field lock in Review Panel', async () => {
    vi.mocked(api.intakeCharacter).mockResolvedValueOnce({
      input: mockInput,
      draft: mockDraft,
      completeness: mockCompleteness,
    });

    const lockedDraft = {
      ...mockDraft,
      provenance: {
        ...mockDraft.provenance,
        name: {
          ...mockDraft.provenance.name,
          authority: 'USER_LOCKED' as const,
        },
      },
    };

    vi.mocked(api.lockCharacterField).mockResolvedValueOnce({
      draft: lockedDraft,
      field_name: 'name',
      authority: 'USER_LOCKED',
    });

    render(<CharacterWorkstation projectId={mockProjectId} />);
    const textarea = screen.getByPlaceholderText(/e\.g\. Detective Marcus Vance/i);
    fireEvent.change(textarea, { target: { value: 'Sample text' } });
    fireEvent.click(screen.getByText(/Normalize & Review Profile/i));

    await screen.findByText(/PROFILE COMPLETENESS/i);

    const lockButtons = screen.getAllByText(/🔒 Lock/i);
    fireEvent.click(lockButtons[0]);

    await waitFor(() => {
      expect(api.lockCharacterField).toHaveBeenCalledWith(mockProjectId, 'draft_123', 'name');
    });

    // Should now show locked badge and unlock button
    expect(await screen.findByText(/🔒 LOCKED/i)).toBeTruthy();
  });

  it('triggers enrichment when Enrich Missing Fields button is clicked', async () => {
    vi.mocked(api.intakeCharacter).mockResolvedValueOnce({
      input: mockInput,
      draft: mockDraft,
      completeness: mockCompleteness,
    });

    const enrichedDraft = {
      ...mockDraft,
      provenance: {
        ...mockDraft.provenance,
        visual_profile: {
          field_name: 'visual_profile',
          authority: 'SYSTEM_INFERRED' as const,
          inference_rule: 'role_inference:visual_profile',
          created_at: '2026-09-24T12:00:00Z',
        },
      },
      visual_profile: {
        character_id: 'char_1',
        name: 'Marcus Vance',
        age: 'Late 30s',
        clothing: 'Charcoal trench coat',
        face_traits: 'Angular jaw',
        hairstyle: 'Short',
        build: 'Athletic',
        signature_items: [],
        emotional_style: 'Vigilant',
      },
    };

    const enrichedCompleteness = {
      ...mockCompleteness,
      score: 100.0,
      missing_fields: [],
    };

    vi.mocked(api.enrichCharacterDraft).mockResolvedValueOnce({
      draft: enrichedDraft,
      completeness: enrichedCompleteness,
    });

    render(<CharacterWorkstation projectId={mockProjectId} />);
    fireEvent.change(screen.getByPlaceholderText(/e\.g\. Detective Marcus Vance/i), {
      target: { value: 'Sample' },
    });
    fireEvent.click(screen.getByText(/Normalize & Review Profile/i));

    await screen.findByText(/PROFILE COMPLETENESS/i);

    const enrichBtn = screen.getByText(/Enrich Missing Fields/i);
    fireEvent.click(enrichBtn);

    await waitFor(() => {
      expect(api.enrichCharacterDraft).toHaveBeenCalledWith(mockProjectId, 'draft_123');
    });

    expect(await screen.findByText('100%')).toBeTruthy();
    expect(screen.getByText(/Charcoal trench coat/i)).toBeTruthy();
  });

  it('accepts character draft and calls onCharacterCreated', async () => {
    vi.mocked(api.intakeCharacter).mockResolvedValueOnce({
      input: mockInput,
      draft: mockDraft,
      completeness: mockCompleteness,
    });

    vi.mocked(api.acceptCharacterDraft).mockResolvedValueOnce({
      character: { id: 'char_marcus_vance', name: 'Marcus Vance' },
      character_id: 'char_marcus_vance',
      draft_id: 'draft_123',
    });

    const onCreated = vi.fn();
    render(<CharacterWorkstation projectId={mockProjectId} onCharacterCreated={onCreated} />);

    fireEvent.change(screen.getByPlaceholderText(/e\.g\. Detective Marcus Vance/i), {
      target: { value: 'Sample' },
    });
    fireEvent.click(screen.getByText(/Normalize & Review Profile/i));

    await screen.findByText(/PROFILE COMPLETENESS/i);

    const acceptBtn = screen.getByText(/Accept & Add to Simulation Cast/i);
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(api.acceptCharacterDraft).toHaveBeenCalledWith(mockProjectId, 'draft_123');
      expect(onCreated).toHaveBeenCalledWith('char_marcus_vance');
    });
  });

  it('allows returning to Edit Raw Input from Review Panel', async () => {
    vi.mocked(api.intakeCharacter).mockResolvedValueOnce({
      input: mockInput,
      draft: mockDraft,
      completeness: mockCompleteness,
    });

    render(<CharacterWorkstation projectId={mockProjectId} />);
    const textarea = screen.getByPlaceholderText(/e\.g\. Detective Marcus Vance/i);
    fireEvent.change(textarea, { target: { value: 'Original raw text' } });
    fireEvent.click(screen.getByText(/Normalize & Review Profile/i));

    await screen.findByText(/PROFILE COMPLETENESS/i);

    const editBtn = screen.getByText(/← Edit Raw Input/i);
    fireEvent.click(editBtn);

    // Returns to input step with original text preserved
    expect(screen.getByDisplayValue('Original raw text')).toBeTruthy();
  });
});
