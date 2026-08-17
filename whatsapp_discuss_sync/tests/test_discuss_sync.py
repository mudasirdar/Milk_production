from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockOutgoingWhatsApp
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDiscussSync(WhatsAppCommon, MockOutgoingWhatsApp):
    """Tests for the whatsapp_discuss_sync module.

    Verifies that outbound WhatsApp template messages create / post into
    a discuss.channel immediately, without waiting for the customer to reply.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A simple template linked to res.partner
        cls.partner_template = cls.env['whatsapp.template'].sudo().create({
            'body': 'Hello {{1}}, your order is ready.',
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'name': 'sync_test_template',
            'quality': 'green',
            'status': 'approved',
            'template_name': 'sync_test_template',
            'variable_ids': [
                (0, 0, {
                    'name': '{{1}}',
                    'line_type': 'body',
                    'field_type': 'free_text',
                    'demo_value': 'Customer',
                }),
            ],
            'wa_account_id': cls.whatsapp_account.id,
            'wa_template_uid': 'sync_test_template',
        })

    def test_01_outbound_creates_channel(self):
        """Sending a template to a partner with no prior WhatsApp history
        must create a discuss.channel and post the message body there."""
        customer = self.whatsapp_customer
        number_formatted = customer.phone.strip().replace(' ', '')

        # No WhatsApp channel should exist yet
        channels_before = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'whatsapp'),
            ('wa_account_id', '=', self.whatsapp_account.id),
        ])

        composer = self.env['whatsapp.composer'].with_user(self.user_wa_admin).with_context({
            'active_model': 'res.partner',
            'active_id': customer.id,
            'active_ids': [customer.id],
        }).create({
            'wa_template_id': self.partner_template.id,
            'phone': customer.phone,
        })

        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        # A WhatsApp channel should now exist
        channels_after = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'whatsapp'),
            ('wa_account_id', '=', self.whatsapp_account.id),
        ])
        new_channels = channels_after - channels_before
        self.assertTrue(
            new_channels,
            "A discuss.channel should have been created on outbound send",
        )

        # The channel should have a comment message with the template body
        channel = new_channels[0]
        comment_messages = channel.message_ids.filtered(
            lambda m: m.message_type == 'comment' and m.author_id == self.user_wa_admin.partner_id
        )
        self.assertTrue(
            comment_messages,
            "The template body should be posted as a comment in the channel",
        )

    def test_02_no_duplicate_channel_on_second_send(self):
        """Sending a second template to the same number must reuse the
        existing channel, not create a duplicate."""
        customer = self.whatsapp_customer

        composer_ctx = {
            'active_model': 'res.partner',
            'active_id': customer.id,
            'active_ids': [customer.id],
        }

        # First send
        composer1 = self.env['whatsapp.composer'].with_user(self.user_wa_admin).with_context(
            composer_ctx
        ).create({
            'wa_template_id': self.partner_template.id,
            'phone': customer.phone,
        })
        with self.mockWhatsappGateway():
            composer1.action_send_whatsapp_template()

        channels_after_first = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'whatsapp'),
            ('wa_account_id', '=', self.whatsapp_account.id),
        ])

        # Second send
        composer2 = self.env['whatsapp.composer'].with_user(self.user_wa_admin).with_context(
            composer_ctx
        ).create({
            'wa_template_id': self.partner_template.id,
            'phone': customer.phone,
        })
        with self.mockWhatsappGateway():
            composer2.action_send_whatsapp_template()

        channels_after_second = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'whatsapp'),
            ('wa_account_id', '=', self.whatsapp_account.id),
        ])
        self.assertEqual(
            len(channels_after_second), len(channels_after_first),
            "No duplicate channel should be created on a second outbound send",
        )

    def test_03_sender_is_channel_member(self):
        """The user who sends the template must be added as a channel member."""
        customer = self.whatsapp_customer

        composer = self.env['whatsapp.composer'].with_user(self.user_wa_admin).with_context({
            'active_model': 'res.partner',
            'active_id': customer.id,
            'active_ids': [customer.id],
        }).create({
            'wa_template_id': self.partner_template.id,
            'phone': customer.phone,
        })

        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        channel = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'whatsapp'),
            ('wa_account_id', '=', self.whatsapp_account.id),
        ], limit=1, order='id desc')

        member_partners = channel.channel_member_ids.partner_id
        self.assertIn(
            self.user_wa_admin.partner_id, member_partners,
            "The sending user must be a member of the channel",
        )

    def test_04_batch_mode_forces_cron(self):
        """Batch sends should use the cron path to avoid timeouts."""
        customer = self.whatsapp_customer
        customer2 = self.env['res.partner'].create({
            'country_id': self.env.ref('base.in').id,
            'name': 'Wa Customer 2',
            'phone': "+91 98765 43210",
        })

        composer = self.env['whatsapp.composer'].with_user(self.user_wa_admin).with_context({
            'active_model': 'res.partner',
            'active_ids': [customer.id, customer2.id],
        }).create({
            'wa_template_id': self.partner_template.id,
            'batch_mode': True,
        })

        with self.mockWhatsappGateway(), self.patchWhatsappCronTrigger():
            composer.action_send_whatsapp_template()

        # Both messages should have been sent (via cron)
        wa_messages = self.env['whatsapp.message'].sudo().search([
            ('wa_template_id', '=', self.partner_template.id),
            ('state', '=', 'sent'),
        ])
        self.assertGreaterEqual(
            len(wa_messages), 2,
            "Both batch messages should be sent via the cron",
        )

    def test_05_multi_company_scoping(self):
        """Channels should be scoped by wa_account_id which is inherently
        company-scoped. Two sends from different accounts must create
        separate channels even for the same phone number."""
        customer = self.whatsapp_customer

        # Create a template on the second account
        template_2 = self.env['whatsapp.template'].sudo().create({
            'body': 'Hello from account 2',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'name': 'sync_test_template_2',
            'quality': 'green',
            'status': 'approved',
            'template_name': 'sync_test_template_2',
            'wa_account_id': self.whatsapp_account_2.id,
            'wa_template_uid': 'sync_test_template_2',
        })

        composer_ctx = {
            'active_model': 'res.partner',
            'active_id': customer.id,
            'active_ids': [customer.id],
        }

        # Send from account 1
        composer1 = self.env['whatsapp.composer'].with_user(self.user_wa_admin).with_context(
            composer_ctx
        ).create({
            'wa_template_id': self.partner_template.id,
            'phone': customer.phone,
        })
        with self.mockWhatsappGateway():
            composer1.action_send_whatsapp_template()

        # Send from account 2
        composer2 = self.env['whatsapp.composer'].with_user(self.user_wa_admin).with_context(
            composer_ctx
        ).create({
            'wa_template_id': template_2.id,
            'phone': customer.phone,
        })
        with self.mockWhatsappGateway():
            composer2.action_send_whatsapp_template()

        channels = self.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'whatsapp'),
        ])
        account_ids = channels.mapped('wa_account_id.id')
        self.assertIn(self.whatsapp_account.id, account_ids)
        self.assertIn(self.whatsapp_account_2.id, account_ids)
