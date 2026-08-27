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
from odoo.http import request
from odoo import http
_logger = logging.getLogger(__name__)


class ClickSendNotify(http.Controller):
    @http.route(['/clicksend/notification'], type='http', auth='public', website=True, csrf=False)
    def clicksend_notification(self, **post):
        """ Clicksend notification controller for Nudge"""
        _logger.info(
            "WEBKUL DEBUG FOR CLICKSEND: SUMMARY(POST DATA)%r", post)
        all_sms_report = request.env["sms.report"].search(
            [('state', 'in', ('sent', 'new'))])
        for sms in all_sms_report:
            if sms.clicksend_message_id and sms.clicksend_username and sms.clicksend_password and sms.clicksend_api_key:
                if post.has_key("dlrs") and post["dlrs"][0]:
                    sms_sms_obj = sms.sms_sms_id
                    if post["dlrs"][0]["status_code"] == 200:
                        sms.write(
                            {'state': 'sent', "status_hit_count": sms.status_hit_count + 1})
                    elif post["dlrs"][0]["status_code"] == 201:
                        if sms.auto_delete:
                            sms.unlink()
                            if sms_sms_obj.auto_delete and not sms_sms_obj.sms_report_ids:
                                sms_sms_obj.unlink()
                        else:
                            sms.write(
                                {'state': 'delivered', "status_hit_count": sms.status_hit_count + 1})
                    elif post["dlrs"][0]["status_code"] in [300, 301]:
                        sms.write(
                            {'state': 'undelivered', "status_hit_count": sms.status_hit_count + 1})
                    elif post["dlrs"][0]["status_code"] == 302:
                        sms.write(
                            {'state': 'Outgoing', "status_hit_count": sms.status_hit_count + 1})
        return
