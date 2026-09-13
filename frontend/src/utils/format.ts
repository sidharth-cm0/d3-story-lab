/**
 * Safe formatting utilities to ensure no "[object Object]" ever renders in the UI.
 */

export function formatDisplayValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'string') {
    return value.trim() === '' ? '—' : value;
  }

  if (typeof value === 'number') {
    return String(value);
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return '—';
    const formattedItems = value.map((item) => formatDisplayValue(item)).filter((s) => s !== '—');
    return formattedItems.length > 0 ? formattedItems.join(', ') : '—';
  }

  if (typeof value === 'object') {
    const obj = value as Record<string, any>;

    // Priority keys for known narrative domain objects
    if (typeof obj.name === 'string' && obj.name.trim()) return obj.name.trim();
    if (typeof obj.title === 'string' && obj.title.trim()) return obj.title.trim();
    if (typeof obj.statement === 'string' && obj.statement.trim()) return obj.statement.trim();
    if (typeof obj.description === 'string' && obj.description.trim()) return obj.description.trim();
    if (typeof obj.summary === 'string' && obj.summary.trim()) return obj.summary.trim();
    if (typeof obj.text === 'string' && obj.text.trim()) return obj.text.trim();
    if (typeof obj.action === 'string' && obj.action.trim()) return obj.action.trim();
    if (typeof obj.prompt === 'string' && obj.prompt.trim()) return obj.prompt.trim();

    // Fallback: format key-value pairs without [object Object]
    const entries = Object.entries(obj)
      .filter(([_, v]) => v !== undefined && v !== null && typeof v !== 'function')
      .slice(0, 5)
      .map(([k, v]) => {
        const valStr = typeof v === 'object' ? (v?.name || v?.title || v?.statement || v?.description || '...') : String(v);
        return `${k}: ${valStr}`;
      });

    if (entries.length > 0) {
      return entries.join('; ');
    }

    return '—';
  }

  return String(value);
}

export function safeExtractSvg(item: unknown): string {
  if (!item) return '';
  if (typeof item === 'string') return item;
  if (typeof item === 'object') {
    const obj = item as Record<string, any>;
    if (typeof obj.svg_content === 'string') return obj.svg_content;
    if (typeof obj.svg_data === 'string') return obj.svg_data;
    if (typeof obj.svg === 'string') return obj.svg;
    if (typeof obj.data === 'string') return obj.data;
    if (typeof obj.content === 'string') return obj.content;
    if (typeof obj.rendered_svg === 'string') return obj.rendered_svg;
    if (typeof obj.previs_svg === 'string') return obj.previs_svg;
  }
  return '';
}
