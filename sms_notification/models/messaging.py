# -*- coding: utf-8 -*-
##########################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2017-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
##########################################################################

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


def send_message_sms(self, partner_id=False, condition=''):
    """Code to send sms to customer."""
    if not (condition):
        return
    sms_template_objs = self.env["wk.sms.template"].search(
        [('condition', '=', condition), ('globally_access', '=', False)])
    for sms_template_obj in sms_template_objs:
        mobile = sms_template_obj._get_partner_mobile(partner_id)
        if mobile:
            sms_template_obj.send_sms_using_template(
                mobile, sms_template_obj, obj=self)
            
class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        result = super(SaleOrder, self).action_confirm()
        for res in self:
            send_message_sms(res, res.partner_id, 'order_confirm')
        return result

    def action_cancel(self):
        result = super(SaleOrder, self).action_cancel()
        for res in self:
            send_message_sms(res, res.partner_id, 'order_cancel')
        return result

    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        for res in self:
            if vals.get('state', False) == 'sent':
                send_message_sms(res, res.partner_id, 'order_placed')
        return result


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def write(self, vals):
        result = super(StockPicking, self).write(vals)
        for res in self:
            if vals.get('date_done', False):
                send_message_sms(res, res.partner_id, 'order_delivered')
        return result


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        result = super(AccountMove, self).action_post()
        for res in self:
            send_message_sms(res, res.partner_id, 'invoice_vaildate')
        return result

    def write(self, vals):
        result = super(AccountMove, self).write(vals)
        for res in self:
            if vals.get('payment_id'):
                send_message_sms(res, res.partner_id, 'invoice_paid')
        return result
