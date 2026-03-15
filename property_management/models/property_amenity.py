# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PropertyAmenity(models.Model):
    _name = 'property.amenity'
    _description = 'Property Amenity'
    _order = 'sequence, name'

    name = fields.Char(string='Amenity Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description', translate=True)
    icon = fields.Char(string='Icon Class', help='FontAwesome icon class (e.g., fa-swimming-pool)')

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Amenity name must be unique!')
    ]
