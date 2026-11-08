"""Read-only explanations of existing order state; never grants authority."""
from datetime import datetime, timezone


def describe(task, actor, last_event=None):
    selected = next((p for p in task['proposals'] if p['id'] == task['selected']), None)
    buyer = task['buyer']
    seller = selected['seller'] if selected else None
    role = 'buyer' if actor == buyer else 'seller' if actor == seller else 'bidder'
    state = task['status']
    mail = task.get('mail', {})
    addresses = mail.get('addresses', {})
    manifests = mail.get('manifests', [])
    latest = {kind: next((m for m in reversed(manifests) if m['kind'] == kind), None)
              for kind in ('input', 'delivery')}
    actions = []

    def add(action, owner, reason='', manifest=None, method='POST', optional=False):
        actions.append(dict(action=action, actor_id=owner,
            executable=owner == actor and not reason,
            blocked_by=[reason] if reason else [], optional=optional,
            requires_user_authorization=method != 'GET', revision=task['revision'],
            manifest_id=manifest['id'] if manifest else None,
            method=method, endpoint=f"/tasks/{task['id']}/{action}" if method else None,
            deadline=task['deadline']))

    # Evidence has the same meaning as server.receipt_matches, imported lazily to avoid a cycle.
    from server import receipt_matches

    def transfer(m):
        if not m.get('sent_at'):
            add('mail-sent', m['sender'], manifest=m)
            return 'awaiting_' + m['kind'] + '_send'
        if not receipt_matches(m):
            add('mail-received', m['recipient'], manifest=m)
            return 'awaiting_' + m['kind'] + '_receipt'
        return None

    if state in ('accepted', 'cancelled'):
        phase = state
    elif state == 'open':
        phase = 'awaiting_selection' if task['proposals'] else 'awaiting_quote'
        if actor == buyer:
            add('select', buyer, '' if task['proposals'] else 'no_proposal')
        elif not task['proposals']:
            add('proposals', actor)
        else:
            add('select', buyer)
    elif state == 'awaiting_confirmation':
        for party in (buyer, seller):
            if party not in addresses:
                add('mail-config', party, optional=not bool(addresses))
        # Structured-only orders need no mail. Once either party opts into mail,
        # guide both to configure before confirm closes that configuration window.
        missing = bool(addresses) and not all(p in addresses for p in (buyer, seller))
        phase = 'awaiting_mailboxes' if missing else 'awaiting_confirmation'
        add('confirm', seller, 'mailboxes_incomplete' if missing else '')
    else:
        phase = 'processing'
        if addresses and not all(p in addresses for p in (buyer, seller)):
            phase = 'blocked_mail_configuration'
            add('operator_review', buyer, 'mailboxes_locked_after_confirmation', method=None)
        else:
            for kind in ('input', 'delivery'):
                if latest[kind]:
                    pending = transfer(latest[kind])
                    if pending:
                        phase = pending
                        break
            else:
                if state == 'delivered':
                    phase = 'awaiting_review'
                    out = latest['delivery']
                    mismatch = out and task['delivery'].get('manifest_id') != out['id']
                    add('accept', buyer, 'delivery_manifest_not_bound' if mismatch else '')
                    add('request_changes', buyer)
                elif addresses and not latest['input']:
                    phase = 'awaiting_input_manifest'
                    add('mail-manifests', buyer)
                else:
                    # Business processing is not an HTTP call. New output versions
                    # are mandatory after request_changes when files were delivered.
                    add('process_work', seller, method=None)
                    old = latest['delivery']
                    rework = old and task.get('delivery') and task['delivery'].get('manifest_id') == old['id']
                    add('mail-manifests', seller, optional=not bool(addresses))
                    add('deliver', seller, 'new_delivery_manifest_required' if rework else '')
        # JSON submission does not wait for the buyer's receipt: otherwise a
        # buyer waiting for delivered and a seller waiting for receipt deadlock.
        out = latest['delivery']
        if state == 'working' and out and out.get('sent_at') and (
                not task.get('delivery') or task['delivery'].get('manifest_id') != out['id']):
            if not any(a['action'] == 'deliver' for a in actions):
                add('deliver', seller)
    return dict(schema_version=1, observed_at=datetime.now(timezone.utc).isoformat(),
        last_event_id=last_event['id'] if last_event else None,
        last_event_at=last_event['created_at'] if last_event else None,
        phase=phase, viewer_role=role, next_actions=actions,
        authority='guidance_only; re-read task and obtain authorization before mutations',
        runtime_status='unknown', mailbox_access_independently_certified=False)
