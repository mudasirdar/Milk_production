from odoo import models


class WhatsappComposerSync(models.TransientModel):
    """Ensure bulk / broadcast template sends always go through the cron queue
    to avoid request timeouts.  The channel creation that now happens inside
    ``_post_message_in_active_channel`` adds extra DB work per message, so
    for batch sends we force the cron path.

    Overridden native methods
    -------------------------
    * ``whatsapp.composer._send_whatsapp_template``
    """

    _inherit = 'whatsapp.composer'

    def _send_whatsapp_template(self, force_send_by_cron=False):
        """Force cron-based sending whenever the composer is in batch mode
        (more than one record selected).  Single-record sends stay
        synchronous for instant feedback.
        """
        if self.batch_mode:
            force_send_by_cron = True
        return super()._send_whatsapp_template(force_send_by_cron=force_send_by_cron)
