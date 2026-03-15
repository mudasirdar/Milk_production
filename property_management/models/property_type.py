# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PropertyType(models.Model):
    _name = 'property.type'
    _description = 'Property Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description', translate=True)
    property_count = fields.Integer(
        string='Property Count',
        compute='_compute_property_count',
        store=False
    )

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Property type name must be unique!')
    ]

    @api.depends()
    def _compute_property_count(self):
        for record in self:
            record.property_count = self.env['property.property'].search_count([
                ('property_type_id', '=', record.id)
            ])

    def action_view_properties(self):
        return {
            'name': 'Properties',
            'type': 'ir.actions.act_window',
            'res_model': 'property.property',
            'view_mode': 'list,form',
            'domain': [('property_type_id', '=', self.id)],
            'context': {'default_property_type_id': self.id}
        }
