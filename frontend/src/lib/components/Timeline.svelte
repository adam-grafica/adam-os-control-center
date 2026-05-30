<script lang="ts">
  /**
   * Timeline - Event timeline component.
   * Props:
   *   events - array of DashboardEvent objects
   */
  import { formatDate } from '$lib/utils/format';
  import { capitalizeFirst } from '$lib/utils/format';

  interface TimelineEvent {
    id: string;
    timestamp: string;
    source: string;
    type: string;
    severity: string;
    payload?: Record<string, unknown>;
    preview?: string;
  }

  let { events = [] }: { events?: TimelineEvent[] } = $props();

  // Sort events by timestamp descending (newest first)
  const sortedEvents = $derived(
    [...events].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    )
  );

  // Get source emoji
  function getSourceEmoji(source: string): string {
    const map: Record<string, string> = {
      heart: '❤️',
      autonomic: '⚡',
      immune: '🛡️',
      proprioception: '🧭',
      reflexes: '🔄',
      dreams: '💭',
      growth: '🌱',
      system: '🔧',
      security: '🔒',
      threat: '⚠️'
    };
    return map[source.toLowerCase()] ?? '📡';
  }

  // Severity color
  function getSeverityColor(severity: string): string {
    const map: Record<string, string> = {
      info: 'var(--color-primary, #3b82f6)',
      low: 'var(--color-text-tertiary, #9ca3af)',
      medium: 'var(--color-warning, #f59e0b)',
      high: 'var(--color-danger, #ef4444)',
      critical: 'var(--color-danger, #ef4444)',
      success: 'var(--color-success, #10b981)',
      debug: '#6b7280',
      error: 'var(--color-danger, #ef4444)',
      warning: 'var(--color-warning, #f59e0b)'
    };
    return map[severity.toLowerCase()] ?? 'var(--color-text-tertiary, #9ca3af)';
  }
</script>

<div class="timeline-container">
  {#if sortedEvents.length === 0}
    <div class="timeline-empty">
      <span class="empty-icon">📭</span>
      <span class="empty-text">No events yet</span>
    </div>
  {:else}
    <div class="timeline-list">
      {#each sortedEvents as event (event.id)}
        <div class="timeline-event animate-slide-in">
          <!-- Timeline connector -->
          <div class="timeline-connector">
            <div
              class="timeline-dot"
              style="background-color: {getSeverityColor(event.severity)};"
            ></div>
            <div class="timeline-line"></div>
          </div>

          <!-- Event content -->
          <div class="timeline-content">
            <div class="timeline-header">
              <span class="timeline-source">{getSourceEmoji(event.source)}</span>
              <span class="timeline-type">{capitalizeFirst(event.type.replace(/_/g, ' '))}</span>
              <span
                class="timeline-severity"
                style="--sev-color: {getSeverityColor(event.severity)};"
              >
                {capitalizeFirst(event.severity)}
              </span>
              <span class="timeline-time">{formatDate(event.timestamp)}</span>
            </div>
            {#if event.preview}
              <p class="timeline-preview">{event.preview}</p>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .timeline-container {
    width: 100%;
    max-height: 600px;
    overflow-y: auto;
    padding-right: 4px;
  }

  .timeline-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 32px 16px;
    gap: 8px;
  }

  .empty-icon {
    font-size: 2rem;
  }

  .empty-text {
    color: var(--color-text-tertiary, #9ca3af);
    font-size: 0.875rem;
  }

  .timeline-list {
    display: flex;
    flex-direction: column;
    gap: 0;
    padding-left: 8px;
  }

  .timeline-event {
    display: flex;
    gap: 12px;
    padding: 8px 0;
    animation: slideIn 0.3s ease forwards;
  }

  .timeline-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;
    width: 12px;
  }

  .timeline-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 6px;
    box-shadow: 0 0 6px currentColor;
  }

  .timeline-line {
    width: 1px;
    flex: 1;
    background: var(--color-border, #374151);
    margin-top: 4px;
    min-height: 100%;
  }

  .timeline-event:last-child .timeline-line {
    display: none;
  }

  .timeline-content {
    flex: 1;
    min-width: 0;
  }

  .timeline-header {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .timeline-source {
    font-size: 1rem;
    line-height: 1;
  }

  .timeline-type {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--color-text-primary, #f3f4f6);
  }

  .timeline-severity {
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--sev-color, var(--color-text-tertiary));
    padding: 1px 6px;
    border-radius: 4px;
    background: color-mix(in srgb, var(--sev-color, transparent) 15%, transparent);
    border: 1px solid color-mix(in srgb, var(--sev-color, transparent) 30%, transparent);
  }

  .timeline-time {
    font-size: 0.75rem;
    color: var(--color-text-tertiary, #9ca3af);
    font-family: var(--font-mono, monospace);
    margin-left: auto;
    flex-shrink: 0;
  }

  .timeline-preview {
    font-size: 0.8125rem;
    color: var(--color-text-secondary, #e5e7eb);
    margin-top: 2px;
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
