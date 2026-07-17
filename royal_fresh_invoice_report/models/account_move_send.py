# -*- coding: utf-8 -*-
from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_pdf_report_id(self, move):
        """Override to use our custom invoice report."""
        return self.env.ref('royal_fresh_invoice_report.action_report_rfaf_invoice')
