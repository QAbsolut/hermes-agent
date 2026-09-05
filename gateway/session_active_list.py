"""``session.active_list`` on the session authority: the live state of the turns it owns.

Desktop's silent-turn check (``session-states.ts`` ``onEventSilence``) and its sidebar poll read
this verb. Unregistered here, the WS fell back to the legacy sidecar's handler, which lists only
the sidecar's own ``_sessions`` and never an authority-owned session: a foreground tool quiet for
45 s read as a reaped turn, and Desktop painted "Hermes ended this turn without a reply" over a
turn that was still running. Rows keep ``server._session_live_item``'s shape; ``id`` and
``session_key`` are both the session id, as ``session.resume`` reports them.
"""
from __future__ import annotations

from hermes_state_runtime import RuntimeStoreError


def _status(live, handle, pending) -> str:
    if handle.execution_state == 'running':
        prompts = live.controls.snapshot(handle.ref.session_id, handle.execution_generation)
        return 'waiting' if prompts else 'working'
    # Admitted, not yet claimed by the drain: the turn exists, its agent has not started.
    return 'starting' if any(row['status'] == 'queued' for row in pending) else 'idle'


async def active_list(connection, ref, params):
    if set(params) - {'profile', 'current_session_id'}:
        raise RuntimeStoreError('invalid_params')
    if 'session:read' not in connection.actor.capabilities:
        raise RuntimeStoreError('permission_denied')
    from gateway.session_live_listing import live_entries
    from hermes_state_sessions import INTERNAL_LISTING_SOURCES
    authority = connection.authority
    current = str(params.get('current_session_id') or '')
    rows = []
    for entry in await live_entries(authority, connection.actor):
        row = entry.row
        # The same population as the live ``session.list`` feed, hidden chats included: a hidden
        # chat open in a pane still needs its turn's liveness.
        if row.get('source') in INTERNAL_LISTING_SOURCES or entry.closed:
            continue
        sid, started = entry.session_id, float(row.get('started_at') or 0)
        # Additive dashboard fields (Overwatch's session-status dot), matching the legacy sidecar
        # item's shape: `unread` off the same row this loop already fetched, workspace identity the
        # way projects.tree carries it, and live delegations from the registry.
        try:
            from tools.async_delegation import has_live_for_session
            delegations = has_live_for_session(session_key=sid, origin_ui_session_id=sid)
        except Exception:
            delegations = True  # a transient registry failure must not read as idle background work
        rows.append({'current': sid == current, 'id': sid, 'session_key': sid,
                     'last_active': float(row.get('ended_at') or started), 'started_at': started,
                     'message_count': int(row.get('message_count') or 0),
                     'model': str(row.get('model') or ''), 'preview': '', 'title': row.get('title') or '',
                     'source': row.get('source'), 'status': _status(entry.live, entry.handle, entry.pending),
                     'has_active_delegations': delegations,
                     'unread': bool(authority.db.session_unread(row)),
                     'cwd': row.get('cwd'), 'git_branch': row.get('git_branch'),
                     'git_repo_root': row.get('git_repo_root')})
    return {'sessions': rows}
