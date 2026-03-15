# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PropertyInquiry(models.Model):
    _name = 'property.inquiry'
    _description = 'Property Inquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Subject', required=True, tracking=True)
    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        tracking=True,
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True
    )
    email = fields.Char(
        string='Email',
        related='partner_id.email',
        store=True,
        readonly=False
    )
    phone = fields.Char(
        string='Phone',
        related='partner_id.phone',
        store=True,
        readonly=False
    )
    message = fields.Text(string='Message', required=True)
    state = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    ], string='Status', default='new', required=True, tracking=True)

    property_owner_id = fields.Many2one(
        'res.partner',
        string='Property Owner',
        related='property_id.owner_id',
        store=True,
        readonly=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True
    )

    response = fields.Html(string='Response')
    response_date = fields.Datetime(string='Response Date', readonly=True)

    # CRM Integration (only if CRM module is installed)
    lead_id = fields.Integer(string='CRM Lead ID', readonly=True,
                             help='ID of the automatically created CRM lead from this inquiry')
    create_lead = fields.Boolean(string='Create CRM Lead', default=False,
                                 help='Automatically create a lead in CRM when inquiry is submitted (requires CRM module)')

    # Computed fields
    property_name = fields.Char(
        string='Property Name',
        related='property_id.name',
        store=True,
        readonly=True
    )
    property_reference = fields.Char(
        string='Property Reference',
        related='property_id.reference',
        store=True,
        readonly=True
    )

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_replied(self):
        self.write({
            'state': 'replied',
            'response_date': fields.Datetime.now()
        })

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'new'})

    def action_create_lead(self):
        """Manually create a CRM lead from this inquiry"""
        self.ensure_one()

        # Check if CRM module is installed
        if not self.env['ir.module.module'].search([('name', '=', 'crm'), ('state', '=', 'installed')], limit=1):
            raise UserError(_('CRM module is not installed. Please install the CRM module to use this feature.'))

        if self.lead_id:
            return {
                'name': _('CRM Lead'),
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': self.lead_id,
                'view_mode': 'form',
                'target': 'current',
            }

        lead = self._create_crm_lead()
        if lead:
            return {
                'name': _('CRM Lead'),
                'type': 'ir.actions.act_window',
                'res_model': 'crm.lead',
                'res_id': lead.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def _create_crm_lead(self):
        """Create a CRM lead from the inquiry"""
        self.ensure_one()

        # Check if CRM module is installed
        if not self.env['ir.module.module'].search([('name', '=', 'crm'), ('state', '=', 'installed')]):
            return False

        if self.lead_id:
            return self.lead_id

        # Prepare lead values
        lead_vals = {
            'name': f'{self.property_id.name} - {self.partner_id.name}',
            'partner_id': self.partner_id.id,
            'email_from': self.email,
            'phone': self.phone,
            'user_id': self.user_id.id or self.property_id.user_id.id,
            'team_id': self.env['crm.team'].search([('use_leads', '=', True)], limit=1).id,
            'type': 'opportunity',
            'description': f"""
Property Inquiry Details:
Property: {self.property_id.name} ({self.property_id.reference})
Transaction Type: {dict(self.property_id._fields['transaction_type'].selection).get(self.property_id.transaction_type)}
Price: {self.property_id.price} {self.property_id.currency_id.name}
Location: {self.property_id.location}

Customer Message:
{self.message}
            """,
            'priority': '1',
            'tag_ids': [(6, 0, [self.env.ref('property_management.crm_tag_property_inquiry', raise_if_not_found=False).id])] if self.env.ref('property_management.crm_tag_property_inquiry', raise_if_not_found=False) else [],
        }

        # Set expected revenue based on property price
        if self.property_id.transaction_type == 'sale':
            lead_vals['expected_revenue'] = self.property_id.price
        elif self.property_id.transaction_type in ['rent', 'lease']:
            # Estimate 12 months rent as expected revenue
            lead_vals['expected_revenue'] = self.property_id.monthly_rent * 12 if self.property_id.monthly_rent else 0

        try:
            lead = self.env['crm.lead'].create(lead_vals)
            self.write({'lead_id': lead.id})

            # Add a note in the inquiry chatter
            self.message_post(
                body=_('CRM Lead/Opportunity created: <a href="#" data-oe-model="crm.lead" data-oe-id="%s">%s</a>') % (lead.id, lead.name),
                message_type='notification',
            )

            return lead
        except Exception as e:
            # If CRM module not installed or any error, just return False
            return False

    @api.model
    def create(self, vals):
        inquiry = super(PropertyInquiry, self).create(vals)

        # Notify property owner
        if inquiry.property_id and inquiry.property_id.owner_id:
            inquiry.message_post(
                body=_('New inquiry received from %s') % inquiry.partner_id.name,
                partner_ids=[inquiry.property_id.owner_id.id],
                message_type='notification',
            )

        # Auto-create CRM lead if enabled and CRM module is installed
        if inquiry.create_lead and not inquiry.lead_id:
            # Only try if CRM is installed
            if self.env['ir.module.module'].search([('name', '=', 'crm'), ('state', '=', 'installed')], limit=1):
                inquiry._create_crm_lead()

        return inquiry
