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
import json
import base64
import requests

from odoo import models, fields, api, _
from urllib3.exceptions import HTTPError
_logger = logging.getLogger(__name__)

clicksend_send_sms_url = 'https://rest.clicksend.com/v3/sms/send'
clicksend_sms_history_url_for_REST_v3 = 'https://rest.clicksend.com/v3/sms/receipts'
clicksend_sms_history_url_for_REST_v2 = 'https://api-mapper.clicksend.com/rest/v2/delivery.json'

CLICKSEND_FAILURE_STATUS = [
    "MISSING_CREDENTIALS",
    "ACCOUNT_NOT_ACTIVATED",
    "INVALID_RECIPIENT",
    "THROTTLED",
    "INVALID_SENDER_ID",
    "INSUFFICIENT_CREDIT",
    "INVALID_CREDENTIALS",
    "ALREADY_EXISTS",
    "MISSING_REQUIRED_FIELDS",
    "TOO_MANY_RECIPIENTS",
    "EMPTY_MESSAGE",
    "NOT_ENOUGH_PERMISSION_TO_LIST_ID",
    "INTERNAL_ERROR",
    "INVALID_VOICE",
    "SUBJECT_REQUIRED",
    "INVALID_MEDIA_FILE",
    "SOMETHING_IS_WRONG"
]
CLICKSEND_SUCCESS_STATUS = ["SUCCESS"]


def send_sms_using_clicksend(
        body_sms, mob_no, from_mob=None, sms_gateway=None):
    '''
    This function is designed for sending sms using clicksend SMS API.

    :param body_sms: body of sms contains text
    :param mob_no: Here mob_no must be string having one or more number
     seprated by (,)
    :param from_mob: sender mobile number or id used in Clicksend API
    :param sms_gateway: sms.mail.server config object for Clicksend Credentials
    :return: response dictionary if sms successfully sent else empty dictionary
    '''
    if not sms_gateway or not body_sms or not mob_no:
        return {}
    if sms_gateway.gateway == "clicksend":
        clicksend_username = sms_gateway.clicksend_username
        clicksend_password = sms_gateway.clicksend_password
        clicksend_api_key = sms_gateway.clicksend_api_key
        try:
            if clicksend_username and clicksend_password and clicksend_api_key:
                pair_code = clicksend_username + ":" + clicksend_password
                encoded_code = base64.b64encode(pair_code.encode())
                encoded_code_with_basic = "Basic " + encoded_code.decode()
                headers = {'Content-Type': 'application/json',
                           'Authorization': encoded_code_with_basic}
                msg_list = []
                for mobi_no in mob_no.split(','):
                    msg_dict = {
                        "source": "python", "body": body_sms,
                        "to": str(mobi_no),"from":from_mob, "custom_string": "this is a test"}
                    msg_list.append(msg_dict)
                params = json.dumps({"messages": msg_list})
                request = requests.post(clicksend_send_sms_url,
                                        data=params, headers=headers)
                response_body = request.json()
                return response_body
        except HTTPError as e:
            _logger.info(
                "--------Clicksend HTTPError While Sending SMS ----%r----", e)
            return {}
        except Exception as e:
            _logger.info(
                "--------Clicksend Exception While Sending SMS ----%r----", e)
            return {}
    return {}


def get_sms_history_for_clicksend(data):
    if not data:
        return {}
    if "clicksend_message_id" in data \
            and "clicksend_username" in data and \
            "clicksend_password" in data and "clicksend_api_key" in data:
        try:
            pair_code = data["clicksend_username"] + \
                ":" + data["clicksend_password"]
            encoded_code = base64.b64encode(pair_code.encode())
            encoded_code_with_basic = "Basic " + encoded_code.decode()
            headers = {'Content-Type': 'application/json',
                       'Authorization': encoded_code_with_basic}
            urlencode_data = {
                "username": data["clicksend_username"],
                "key": data["clicksend_api_key"],
                "messageid": data["clicksend_message_id"]}
            request = requests.post(
                clicksend_sms_history_url_for_REST_v2, data=urlencode_data,
                headers=headers)
            response_body = request.json()
            return response_body
        except HTTPError as e:
            _logger.info(
                "----------Clicksend HTTPError For SMS History----%r-----", e)
            return {}
        except Exception as e:
            _logger.info(
                "---------Clicksend Exception For SMS History-----%r-----", e)
            return {}
    return {}


class SmsSms(models.Model):
    """SMS sending using Clicksend SMS Gateway."""

    _inherit = "wk.sms.sms"
    _name = "wk.sms.sms"
    _description = "ClickSend SMS"

    
    def send_sms_via_gateway(
            self, body_sms, mob_no, from_mob=None, sms_gateway=None):
        self.ensure_one()
        gateway_id = sms_gateway if sms_gateway else super(
            SmsSms, self).send_sms_via_gateway(
                body_sms, mob_no, from_mob=from_mob, sms_gateway=sms_gateway)
        if gateway_id:
            if gateway_id.gateway == 'clicksend':
                if gateway_id.use_companyname:
                    from_mob = self.env.company.name.replace(" ", "_")[:12]
                for element in mob_no:
                    response = send_sms_using_clicksend(
                        body_sms, element, from_mob=from_mob,
                        sms_gateway=gateway_id)
                    for mobi_no in element.split(','):
                        if "response_code" in response and \
                                response.get("response_code") == "SUCCESS":
                            if "data" in response and \
                                    "messages" in response["data"]:
                                for msg_report in response["data"]["messages"]:
                                    if mobi_no == msg_report["to"]:
                                        sms_report_obj = self.env[
                                            "sms.report"].create({
                                                'to': mobi_no, 'msg': body_sms,
                                                'sms_sms_id': self.id,
                                                "auto_delete":
                                                    self.auto_delete,
                                                'sms_gateway_config_id':
                                                    gateway_id.id
                                            })
                                        clicksend_message_id = msg_report[
                                            "message_id"]
                                        if msg_report["status"] in \
                                                CLICKSEND_SUCCESS_STATUS:
                                            sms_report_obj.write(
                                                {
                                                    'state': 'sent',
                                                    'clicksend_message_id':
                                                        clicksend_message_id})
                                        elif msg_report["status"] in \
                                                CLICKSEND_FAILURE_STATUS:
                                            sms_report_obj.write(
                                                {'state': 'undelivered',
                                                    'clicksend_message_id':
                                                        clicksend_message_id})
                                        else:
                                            sms_report_obj.write({
                                                'state': 'new',
                                                'clicksend_message_id':
                                                    clicksend_message_id})
                        else:
                            self.write({'state': 'error'})
                else:
                    self.write({'state': 'sent'})
            else:
                gateway_id = super(SmsSms, self).send_sms_via_gateway(
                    body_sms, mob_no, from_mob=from_mob,
                    sms_gateway=sms_gateway)
        else:
            _logger.info(
                "------------------- SMS Gateway not found -----------------")
        return gateway_id


class SmsReport(models.Model):
    """SMS report."""

    _inherit = "sms.report"

    clicksend_message_id = fields.Char("Clicksend SMS ID")

    @api.model
    def cron_function_for_sms(self):
        _logger.info(
            "************** Cron Function For Clicksend SMS ****************")

        all_sms_report = self.search([('state', 'in', ('sent', 'new')),('sms_gateway','=','clicksend')])
        for sms in all_sms_report:
            gateway = sms.sms_gateway_config_id
            if sms.clicksend_message_id:
                msg_report = get_sms_history_for_clicksend(
                    {"clicksend_message_id": sms.clicksend_message_id,
                        "clicksend_username": gateway.clicksend_username,
                        "clicksend_password": gateway.clicksend_password,
                        "clicksend_api_key": gateway.clicksend_api_key})
                if 'dlrs' in msg_report and msg_report["dlrs"][0]:
                    sms_sms_obj = sms.sms_sms_id
                    if msg_report["dlrs"][0]["status"] == "Delivered":
                        if sms.auto_delete:
                            sms.unlink()
                            if sms_sms_obj.auto_delete and not \
                                    sms_sms_obj.sms_report_ids:
                                sms_sms_obj.unlink()
                        else:
                            sms.write({
                                'state': 'delivered',
                                "status_hit_count": sms.status_hit_count + 1})
                    elif msg_report["dlrs"][0]["status"] == "Undelivered":
                        sms.write({
                            'state': 'undelivered',
                            "status_hit_count": sms.status_hit_count + 1})
                    elif msg_report["dlrs"][0]["status_code"] == 200:
                        sms.write({
                            'state': 'sent',
                            "status_hit_count": sms.status_hit_count + 1})
                    elif msg_report["dlrs"][0]["status_code"] == 201:
                        if sms.auto_delete:
                            sms.unlink()
                            if sms_sms_obj.auto_delete and not \
                                    sms_sms_obj.sms_report_ids:
                                sms_sms_obj.unlink()
                        else:
                            sms.write({
                                'state': 'delivered',
                                "status_hit_count": sms.status_hit_count + 1})
                    elif msg_report["dlrs"][0]["status_code"] in [300, 301]:
                        sms.write({
                            'state': 'undelivered',
                            "status_hit_count": sms.status_hit_count + 1})
                    elif msg_report["dlrs"][0]["status_code"] == 302:
                        sms.write({
                            'state': 'Outgoing',
                            "status_hit_count": sms.status_hit_count + 1})
            else:
                sms.send_now()
        super(SmsReport, self).cron_function_for_sms()
        return True

    
    def send_sms_via_gateway(
            self, body_sms, mob_no, from_mob=None, sms_gateway=None):
        self.ensure_one()
        gateway_id = sms_gateway if sms_gateway else super(
            SmsReport, self).send_sms_via_gateway(
            body_sms, mob_no, from_mob=from_mob, sms_gateway=sms_gateway)
        if gateway_id:
            if gateway_id.gateway == 'clicksend':
                for element in mob_no:
                    count = 1
                    for mobi_no in element.split(','):
                        if count == 1:
                            self.to = mobi_no
                            rec = self
                        else:
                            rec = self.create({
                                'to': mobi_no, 'msg': body_sms,
                                "auto_delete": self.auto_delete,
                                'sms_gateway_config_id': gateway_id.id})
                        response = send_sms_using_clicksend(
                            body_sms, mobi_no, from_mob=from_mob,
                            sms_gateway=gateway_id)
                        if 'response_code' in response and \
                                response["response_code"] == "SUCCESS":
                            if 'data' in response and 'messages' in \
                                    response["data"]:
                                for msg_report in response["data"]["messages"]:
                                    if mobi_no == msg_report["to"]:
                                        clicksend_message_id = msg_report[
                                            "message_id"]
                                        if msg_report["status"] in \
                                                CLICKSEND_SUCCESS_STATUS:
                                            rec.write({
                                                'state': 'sent',
                                                'clicksend_message_id':
                                                    clicksend_message_id})
                                        elif msg_report["status"] in \
                                                CLICKSEND_FAILURE_STATUS:
                                            rec.write({
                                                'state': 'undelivered',
                                                'clicksend_message_id':
                                                    clicksend_message_id,})
                                        else:
                                            rec.write({
                                                'state': 'new',
                                                'clicksend_message_id':
                                                    clicksend_message_id})
                        else:
                            rec.write({'state': 'undelivered'})
                        count += 1
            else:
                gateway_id = super(SmsReport, self).send_sms_via_gateway(
                    body_sms, mob_no, from_mob=from_mob,
                    sms_gateway=sms_gateway)
        return gateway_id
