# -*- coding: utf-8 -*-
#################################################################################
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
#################################################################################
{
  "name"                 :  "Clicksend SMS Gateway",
  "summary"              :  """Odoo Clicksend SMS Gateway module allows Odoo admin to send SMS using ClickSend SMS. The user can send easy text message to clients.""",
  "category"             :  "Marketing",
  "version"              :  "19.0.1.0.0",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "OPL-1",
  "website"              :  "https://store.webkul.com/Odoo-ClickSend-SMS-Gateway.html",
  "description"          :  """https://webkul.com/blog/odoo-clicksend-sms-gateway/
ClickSend communication
Odoo ClickSend SMS Gateway
Click Send SMS Gateway
ClickSend SMS alert
Use ClickSend in Odoo
Integrate SMS Gateways with Odoo
Bulk SMS send
Send Bulk SMS
ClickSend communication
ClickSend Odoo
Click Send
Odoo SMS Notification
Send Text Messages to mobile
Integrate SMS Gateways with Odoo
SMS Gateway
SMS Notification
Notify with Odoo SMS 
Mobile message send
Send Mobile messages
Mobile notifications to customers
Mobile Notifications to Users
How to get SMS notification in Odoo
module to get SMS notification in Odoo
SMS Notification app in Odoo
Notify SMS in Odoo
Add SMS notification feature to your Odoo
Mobile SMS feature
How Odoo can help to get SMS notification,
Odoo SMS OTP Authentication,
Marketplace SMS
Plivo SMS Gateway
Skebby SMS Gateway
Mobily SMS Gateway
MSG91 SMS Gateway
Netelip SMS Gateway
Twilio SMS Gateway""",
  "live_test_url"        :  "https://www.youtube.com/watch?v=wYCwiTkdGGE&feature=youtu.be",
  "depends"              :  ['sms_notification'],
  "data"                 :  [
                             'views/clicksend_config_view.xml',
                             'views/sms_report.xml',
                            ],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  50,
  "currency"             :  "USD",
  "external_dependencies":  {'python': ['urllib3']},
}
