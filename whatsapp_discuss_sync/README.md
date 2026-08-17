# WhatsApp Discuss Sync

Odoo 19 module that makes outbound WhatsApp messages (sent from a record's
Chatter or the WhatsApp composer) immediately visible in a `discuss.channel`,
instead of waiting for the customer to reply.

## Problem

In the native `whatsapp` addon, a Discuss channel for a WhatsApp conversation
is only created when the **customer replies** via the webhook.  Until then the
sending user has no way to see the sent message in Discuss.

## How it works

This module uses `_inherit` (no core file edits) to override two methods:

| Method | Model | What changed |
|--------|-------|-------------|
| `_post_message_in_active_channel` | `whatsapp.message` | Finds or creates a channel on every outbound template send, adds the sending user as a channel member, and inserts the full template body. For **new** channels the channel and messages are created directly (bypassing `_get_whatsapp_channel` and `message_post`) to avoid a bus-notification race that crashes the Discuss Composer (`wa_account_id is undefined`). `_broadcast` is called **last** so the JS Store already has the full channel data. For **existing** channels the native `message_post` path is safe and is used as before. |
| `_send_whatsapp_template` | `whatsapp.composer` | Forces `force_send_by_cron=True` when `batch_mode` is active so bulk/broadcast sends go through the async cron queue and avoid HTTP timeouts. |

### No-duplicate guarantee

The native `_get_whatsapp_channel()` matches channels by
`(whatsapp_number, wa_account_id)`.  Because we reuse this exact method, when
the customer's reply later arrives via webhook the inbound flow finds the
**same channel** — no duplicate is created.

### Multi-company scoping

Channels are scoped via `wa_account_id`, which is inherently tied to a company.
Two different WhatsApp Business Accounts will produce separate channels even for
the same phone number.

### WhatsApp session rules preserved

This module only changes **where** the sent message is displayed inside Odoo.
It does not alter Meta's 24-hour customer-service window or the 15-day template
reply window.  The `whatsapp_channel_valid_until` compute and the
`_ACTIVE_THRESHOLD_DAYS` constant remain untouched.

## Edge cases handled

- **Brand-new contact** — `_get_whatsapp_channel` calls
  `res.partner._find_or_create_from_number()` to create a partner if none
  exists for the phone number.
- **Bulk/broadcast sends** — routed through the `ir_cron_send_whatsapp_queue`
  cron to avoid request timeouts.
- **Multi-company** — channel lookup is filtered by `wa_account_id`.

## Upgrade notes

After upgrading to a new Odoo version, verify that these native methods still
exist and have the same signatures:

1. `whatsapp.message._post_message_in_active_channel` (called from `_send_message`)
2. `whatsapp.composer._send_whatsapp_template`
3. `whatsapp.account._find_active_channel` (channel lookup by phone number — called, not overridden)
4. `res.partner._find_or_create_from_number` (partner creation — called, not overridden)
5. `base._whatsapp_get_responsible` (responsible user lookup — called, not overridden)

## Installation

Copy the `whatsapp_discuss_sync` folder into your custom addons path and
install it from the Odoo Apps menu.  Requires the `whatsapp` module.

## Tests

```
./odoo-bin -d <db> --test-tags whatsapp_discuss_sync -i whatsapp_discuss_sync --stop-after-init
```
