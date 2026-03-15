# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertySafetyCertificate(models.Model):
    _name = 'property.safety.certificate'
    _description = 'Property Safety Certificate'
    _order = 'issue_date desc'

    name = fields.Char(string='Certificate Name', required=True)
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  ondelete='cascade')

    certificate_type = fields.Selection([
        ('fire_safety', 'Fire Safety Certificate'),
        ('electrical_safety', 'Electrical Safety Certificate'),
        ('gas_safety', 'Gas Safety Certificate'),
        ('structural', 'Structural Safety Certificate'),
        ('occupancy', 'Occupancy Certificate'),
        ('environmental', 'Environmental Certificate'),
        ('energy', 'Energy Performance Certificate'),
        ('other', 'Other')
    ], string='Certificate Type', required=True)

    certificate_number = fields.Char(string='Certificate Number')
    issue_date = fields.Date(string='Issue Date', required=True)
    expiry_date = fields.Date(string='Expiry Date')
    issuing_authority = fields.Char(string='Issuing Authority')

    status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('pending', 'Pending Renewal')
    ], string='Status', compute='_compute_status', store=True)

    certificate_document = fields.Binary(string='Certificate Document', attachment=True)
    certificate_filename = fields.Char(string='Document Filename')

    notes = fields.Text(string='Notes')

    @api.depends('expiry_date')
    def _compute_status(self):
        from datetime import timedelta
        today = fields.Date.today()
        for certificate in self:
            if certificate.expiry_date:
                if certificate.expiry_date < today:
                    certificate.status = 'expired'
                elif certificate.expiry_date <= (today + timedelta(days=30)):
                    certificate.status = 'pending'
                else:
                    certificate.status = 'valid'
            else:
                certificate.status = 'valid'

    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for certificate in self:
            if certificate.issue_date and certificate.expiry_date:
                if certificate.expiry_date <= certificate.issue_date:
                    raise ValidationError(_('Expiry date must be after issue date.'))
