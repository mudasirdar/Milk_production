# -*- coding: utf-8 -*-
##########################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
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

from odoo import models, fields, api, _
from odoo.exceptions import  UserError
from .clicksend_messaging import send_sms_using_clicksend

_logger = logging.getLogger(__name__)


class SmsMailServer(models.Model):
    """Configure the clicksend sms gateway."""

    _inherit = "sms.mail.server"
    _name = "sms.mail.server"
    _description = "Clicksend"

    clicksend_username = fields.Char(string="Clicksend Username")
    clicksend_password = fields.Char(string="Clicksend Password")
    clicksend_api_key = fields.Char(string="Clicksend Api key")
    use_companyname = fields.Boolean(string="Want to use Company Name in From", help="You can purchase a ClickSend dedicated number. You can setup rules for incoming SMS, anything is possible")

    
    def test_conn_clicksend(self):
        sms_body = "Clicksend Test Connection Successful........"
        mobile_number = self.user_mobile_no
        response = send_sms_using_clicksend(
            sms_body, mobile_number, sms_gateway=self)
        if "response_code" in response and \
                response["response_code"] == "SUCCESS":
            if self.sms_debug:
                _logger.info(
                    "===========Test Connection status has been sent on \
                    %r mobile number", mobile_number)
            raise UserError(
                "Test Connection status has been sent on %s \
                mobile number" % mobile_number)

        if 'response_code' in response and response["response_code"] \
                in ("BAD_REQUEST", "UNAUTHORIZED"):
            if self.sms_debug:
                _logger.error(
                    "==========One of the information given by you is wrong. \
                    It may be [Mobile Number] [Username] or [Password] or \
                    [Api key]")
            raise UserError(
                "One of the information given by you is wrong. It may be \
                [Mobile Number] [Username] or [Password] or [Api key]")

    @api.model
    def get_reference_type(self):
        selection = super(SmsMailServer, self).get_reference_type()
        selection.append(('clicksend', 'ClickSend'))
        return selection
