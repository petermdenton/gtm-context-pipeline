# Mail drafts, CRM records and verified sends

This is an agent workflow for available supported tools, not a bundled adapter.
There is no mail/CRM schema or provider connection implemented in this toolkit.
Use the client's chosen mailbox/project, inspect its current schema and access,
and map fields deliberately. Do not copy source-project IDs, enum values or
table names into a different CRM. Portal contacts are not CRM enrollment.

Read only the records needed to reconcile identity, suppression, prior sends,
replies and existing drafts. Preserve user edits, ownership and lifecycle state.
Do not clear suppression, reactivate holds or advance a sales stage because
research or a draft was created. Resolve ambiguous identity before external writes.

Local preparation does not authorize provider drafts, CRM writes or sending.
Use established session scope without asking again. If an action is outside
scope, finish the concrete reviewable copy first. Missing external access need
not block local drafts. Do not install a provider or widen credentials merely
to finish an ordinary drafting request.

For authorized external work:

1. Resolve sender account, actual recipient address, message content and requested
   sequence steps. Do not substitute another provider or invent an address.
2. Use stable private sequence/contact/step keys and content versions/hashes.
   Reconcile existing contacts/messages before creating rows; names alone are
   insufficient, and a missing email is not permission to duplicate a contact.
3. Create only the requested drafts/records. Preserve sent history and manual
   edits. Read back provider content and CRM state; record observed IDs or URLs
   without fabricating unavailable API IDs. A prepared CRM row is not a mailbox
   draft, and neither is a send. Unsent records have no actual send timestamp.
4. If one system succeeds and another fails, retain the successful reference and
   retry only the missing authorized operation. On ambiguous creation, inspect
   existing drafts/rows first. Cross-provider writes are not atomic.

For an explicitly authorized send, verify final recipient/sender/content and
available suppression/prior-send evidence. Use the supported sending tool and
record its observed result. On ambiguity, inspect Sent/provider evidence before
any retry. A disappearing draft does not prove delivery. Preserve actual sent
content and time, which may differ from the earlier draft.

Record provider acceptance separately from inbox delivery, replies and meetings.
Reconcile outcomes with stable event IDs, occurred-at timestamps and evidence
linking the event to the contact. Bounces, opt-outs and corrections remain explicit.
An opt-out changes eligibility; handle suppression/cancellation within authorized
scope and flag any missing write capability. Do not keep preparing active sends
against a known opt-out.

Follow-up recommendations are not scheduled emails. Use actual task/scheduling
tools only when requested with concrete timing. On-demand reconciliation is not
continuous monitoring. Report local drafts, provider drafts, CRM rows, sends and
partial failures separately, with links to private evidence.
