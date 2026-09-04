import logging
import requests

from odoo import models, _

_logger = logging.getLogger(__name__)

TEXTBEE_API_URL = "https://api.textbee.dev/api/v1/gateway/send-sms"
TEXTBEE_DEFAULT_API_KEY = "txb_ayhHP7gzDPfybNq83Zqnt1R7BM6dT0Sp"


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_send_textbee_sms(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param(
            'textbee_sms.api_key', default=TEXTBEE_DEFAULT_API_KEY
        )
        for order in self:
            phone = order.partner_id.phone or order.partner_id.mobile
            if not phone:
                order.message_post(
                    body=_("Textbee SMS failed: No phone number found for %s.", order.partner_id.name),
                )
                continue

            previous_balance = order.partner_id.credit
            message = (
                "Hello %s, your Sale Order %s is confirmed!\n"
                "Order Amount: %.2f\n"
                "Previous Balance: %.2f\n"
                "Total Balance: %.2f"
            ) % (
                order.partner_id.name,
                order.name,
                order.amount_total,
                previous_balance,
                order.amount_total + previous_balance,
            )
            payload = {
                "recipients": [phone],
                "message": message,
            }
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(TEXTBEE_API_URL, json=payload, headers=headers, timeout=15)
                response.raise_for_status()
                order.message_post(
                    body=_("Textbee SMS sent successfully to %s.", phone),
                )
            except requests.exceptions.RequestException as e:
                _logger.error("Textbee SMS failed for %s: %s", order.name, e)
                order.message_post(
                    body=_("Textbee SMS failed: %s", e),
                )
