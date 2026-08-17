import logging

from markupsafe import Markup, escape

from odoo import Command, models, tools, _
from odoo.addons.whatsapp.tools import phone_validation as wa_phone_validation

_logger = logging.getLogger(__name__)


class WhatsappMessageSync(models.Model):
    """Override outbound message handling so that every sent WhatsApp template
    message immediately appears in a discuss.channel.

    Native behaviour
    ----------------
    ``_post_message_in_active_channel`` is called after a template message is
    successfully sent (see ``_send_message`` in the core *whatsapp* addon).
    It only posts a *notification* into an **already existing** channel — it
    never creates one.  The channel is only created later, when the customer
    replies via the webhook (``_find_active_channel`` with
    ``create_if_not_found=True``).

    What this override does
    -----------------------
    * When no channel exists yet, creates one using the same matching key
      ``(whatsapp_number, wa_account_id)`` that the inbound webhook uses, so
      the customer's future reply finds this same channel (no duplicate).
    * Adds the sending user as a channel member.
    * Creates the message body directly (bypassing ``message_post``) and calls
      ``_broadcast`` **last**, so that when the frontend's OWL reactive system
      processes the bus notification the channel Store already contains the
      ``wa_account_id`` relation the Composer needs.

    Why not ``_get_whatsapp_channel`` + ``message_post``?
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``_get_whatsapp_channel`` internally calls ``message_post`` on the new
    channel (system notes about the related document).  When called
    synchronously from the user's RPC (our case), those bus notifications
    reach the Discuss frontend *before* the Store has the full channel data
    (specifically ``wa_account_id``), causing:

        TypeError: can't access property "name",
                   this.thread.wa_account_id is undefined

    In the native flow this never happens because ``_get_whatsapp_channel``
    is only called from the **webhook controller** (server-to-server), so no
    browser is listening for bus events at that moment.

    Overridden native methods
    -------------------------
    * ``whatsapp.message._post_message_in_active_channel``
    """

    _inherit = 'whatsapp.message'

    def _post_message_in_active_channel(self):
        """Find or create a discuss.channel and insert the template body so
        the sender sees it in Discuss immediately."""
        self.ensure_one()

        if not self.wa_template_id:
            return

        wa_account = self.wa_account_id
        number = self.mobile_number_formatted
        if not number or not wa_account:
            return

        # ------------------------------------------------------------------
        # 1. Try to find an existing channel (native helper, no side-effects)
        # ------------------------------------------------------------------
        channel = wa_account._find_active_channel(number)

        if channel:
            # Channel already exists (and wa_account_id is already in the JS
            # store from a prior load).  Safe to use message_post here.
            self._sync_post_to_existing_channel(channel)
            return

        # ------------------------------------------------------------------
        # 2. Create a new channel directly (without _get_whatsapp_channel)
        # ------------------------------------------------------------------
        channel = self._sync_create_channel(wa_account, number)
        if not channel:
            return

        # ------------------------------------------------------------------
        # 3. Create the template body as a mail.message directly — avoids
        #    bus notifications that would trigger a premature OWL render.
        # ------------------------------------------------------------------
        body = self.body
        if body:
            self.env['mail.message'].sudo().create({
                'author_id': self.env.user.partner_id.id,
                'body': body,
                'message_type': 'comment',
                'model': 'discuss.channel',
                'res_id': channel.id,
                'subtype_id': self.env.ref('mail.mt_comment').id,
            })

        # ------------------------------------------------------------------
        # 4. Broadcast LAST — the channel record (including wa_account_id)
        #    will be fully formed when the JS Store processes this event.
        # ------------------------------------------------------------------
        all_members = channel.channel_member_ids.partner_id
        channel._broadcast(all_members.ids)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sync_post_to_existing_channel(self, channel):
        """Post the template body (or a notification) into a channel that
        already existed before this send."""
        sending_partner = self.env.user.partner_id

        # Ensure the sender is a channel member
        if sending_partner and not channel.sudo().channel_member_ids.filtered(
            lambda m: m.partner_id == sending_partner
        ):
            channel.sudo().write({
                'channel_member_ids': [Command.create({'partner_id': sending_partner.id})],
            })
            channel.sudo()._broadcast(sending_partner.ids)

        # Re-check membership after potential addition
        if channel.with_user(self.env.user).is_member:
            body = self.body
            message_type = 'comment'
            silent = False
        else:
            if self.mail_message_id.model and self.mail_message_id.res_id:
                record_name = self.mail_message_id.record_name
                url = (
                    f"{self.get_base_url()}/odoo/"
                    f"{self.mail_message_id.model}/{self.mail_message_id.res_id}"
                )
                record_link = Markup(
                    "<a target='_blank' href='{url}'>{name}</a>"
                ).format(url=url, name=escape(record_name))
            else:
                record_link = _("another document")
            body = Markup(_(
                "A new template was sent on %(record_link)s.<br>"
                "Future replies will be transferred to a new chat.",
                record_link=record_link,
            ))
            message_type = 'notification'
            silent = True

        if body:
            channel.sudo().message_post(
                body=body,
                message_type=message_type,
                silent=silent,
                subtype_xmlid='mail.mt_comment',
            )

    def _sync_create_channel(self, wa_account, number):
        """Create a WhatsApp discuss.channel without calling message_post
        (which would trigger bus notifications before the JS Store is ready).

        Returns the new channel or an empty recordset on failure.
        """
        DiscussChannel = self.env['discuss.channel'].sudo()

        # --- format number -------------------------------------------------
        base_number = number if number.startswith('+') else f'+{number}'
        wa_number = base_number.lstrip('+')
        wa_formatted = wa_phone_validation.wa_phone_format(
            self.env.company,
            number=base_number,
            force_format='WHATSAPP',
            raise_exception=False,
        ) or wa_number

        # --- double-check no channel appeared in the meantime --------------
        existing = DiscussChannel.search([
            ('whatsapp_number', '=', wa_formatted),
            ('wa_account_id', '=', wa_account.id),
        ], limit=1, order='create_date desc')
        if existing:
            return existing

        # --- find / create partner -----------------------------------------
        recipient_partner = self.env['res.partner']._find_or_create_from_number(
            wa_formatted, False,
        )
        recipient_name = (
            recipient_partner.name
            if recipient_partner.name != recipient_partner.phone
            else False
        )

        # --- create channel ------------------------------------------------
        channel = DiscussChannel.with_context(
            tools.clean_context(self.env.context),
        ).create({
            'channel_type': 'whatsapp',
            'name': (
                f"{recipient_name} ({wa_formatted})"
                if recipient_name else wa_formatted
            ),
            'wa_account_id': wa_account.id,
            'whatsapp_number': wa_formatted,
            'whatsapp_partner_id': recipient_partner.id,
        })

        # --- determine members ---------------------------------------------
        related_record = False
        responsible_partners = self.env['res.partner']
        if self.mail_message_id.model and self.mail_message_id.res_id:
            try:
                related_record = self.env[self.mail_message_id.model].browse(
                    self.mail_message_id.res_id,
                )
                responsible_partners = related_record._whatsapp_get_responsible(
                    related_message=self.mail_message_id,
                    related_record=related_record,
                    whatsapp_account=wa_account,
                ).partner_id
            except Exception:
                _logger.debug(
                    "whatsapp_discuss_sync: could not resolve responsible "
                    "users for %s,%s", self.mail_message_id.model,
                    self.mail_message_id.res_id, exc_info=True,
                )

        sending_partner = self.env.user.partner_id
        partners = responsible_partners | channel.whatsapp_partner_id | sending_partner

        # If only the customer + sender, also add the WA account notify users
        internal_partners = partners.filtered(
            lambda p: not p.partner_share
        )
        if not internal_partners - sending_partner:
            partners |= wa_account.notify_user_ids.partner_id

        channel.channel_member_ids = (
            [Command.clear()]
            + [Command.create({'partner_id': p.id}) for p in partners]
        )

        # --- create "Related document" system note directly ----------------
        if related_record and hasattr(related_record, 'message_post'):
            info = _(
                "Related %(model_name)s: ",
                model_name=self.env['ir.model']._get(
                    self.mail_message_id.model,
                ).display_name,
            )
            url = Markup('{base_url}/odoo/{model}/{res_id}').format(
                base_url=channel.get_base_url(),
                model=self.mail_message_id.model,
                res_id=self.mail_message_id.res_id,
            )
            record_name = self.mail_message_id.record_name
            self.env['mail.message'].sudo().create({
                'author_id': self.env.ref('base.partner_root').id,
                'body': Markup(
                    '<p>{info}<a target="_blank" href="{url}">'
                    '{record_name}</a></p>'
                ).format(info=info, url=url, record_name=record_name),
                'message_type': 'comment',
                'model': 'discuss.channel',
                'res_id': channel.id,
                'subtype_id': self.env.ref('mail.mt_note').id,
            })

            # Notification in the original document about the new channel
            ch_info = _("A new WhatsApp channel is created for this document")
            ch_url = Markup('{base_url}/odoo/discuss.channel/{cid}').format(
                base_url=channel.get_base_url(), cid=channel.id,
            )
            related_record.message_post(
                author_id=self.env.ref('base.partner_root').id,
                body=Markup(
                    '<p>{info} <a target="_blank" '
                    'class="o_whatsapp_channel_redirect" '
                    'data-oe-id="{cid}" href="{url}">{cname}</a></p>'
                ).format(
                    info=ch_info, url=ch_url,
                    cid=channel.id, cname=channel.display_name,
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        return channel
