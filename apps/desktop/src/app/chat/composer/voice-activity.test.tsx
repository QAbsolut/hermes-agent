import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { I18nProvider } from '@/i18n'
import { setVoicePlaybackState, type VoicePlaybackState } from '@/store/voice-playback'

import { VoiceActivity, VoicePlaybackActivity } from './voice-activity'

afterEach(cleanup)

describe('VoiceActivity accessibility', () => {
  it('keeps the dictation timer visible without announcing every tick', () => {
    render(
      <I18nProvider configClient={null} initialLocale="en">
        <VoiceActivity state={{ elapsedSeconds: 65, level: 0.5, status: 'recording' }} />
      </I18nProvider>
    )

    const status = screen.getByRole('status')
    const timer = screen.getByText('1:05')

    expect(status.getAttribute('aria-live')).toBe('polite')
    expect(status.textContent).toContain('Dictating')
    expect(status.textContent).toContain('1:05')
    expect(timer.getAttribute('aria-hidden')).toBe('true')
  })
})

function renderPlaybackBox(sessionId: string | null) {
  return render(
    <I18nProvider configClient={null} initialLocale="en">
      <VoicePlaybackActivity sessionId={sessionId} />
    </I18nProvider>
  )
}

function speaking(sessionId: string | null): VoicePlaybackState {
  return {
    audioElement: null,
    messageId: 'msg-1',
    sessionId,
    sequence: 1,
    source: 'read-aloud',
    status: 'speaking'
  }
}

// The playback box must scope to the session that started playback. Before
// this, the global store carried no session id, so the box lit up above EVERY
// open session's composer while a single answer played.
describe('VoicePlaybackActivity — session scoping', () => {
  afterEach(() => {
    cleanup()
    setVoicePlaybackState({ audioElement: null, messageId: null, sequence: 0, source: null, status: 'idle' })
  })

  it('renders the box for the session that started playback', () => {
    setVoicePlaybackState(speaking('session-A'))
    renderPlaybackBox('session-A')
    expect(screen.getByRole('status')).toBeTruthy()
  })

  it('does NOT render the box in other open sessions', () => {
    setVoicePlaybackState(speaking('session-A'))
    renderPlaybackBox('session-B')
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('renders nothing when playback is idle', () => {
    setVoicePlaybackState({ audioElement: null, messageId: null, sequence: 0, source: null, status: 'idle' })
    const { container } = renderPlaybackBox('session-A')
    expect(container.firstChild).toBeNull()
  })
})
