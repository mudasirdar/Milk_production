# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyCategory(models.Model):
    _name = 'property.category'
    _description = 'Property Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description', translate=True)
    parent_id = fields.Many2one('property.category', string='Parent Category')
    child_ids = fields.One2many('property.category', 'parent_id', string='Child Categories')
    property_count = fields.Integer(string='Property Count', compute='_compute_property_count')

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Category name must be unique!')
    ]

    @api.depends('name')
    def _compute_property_count(self):
        for category in self:
            category.property_count = self.env['property.property'].search_count([
                ('property_category', '=', category.id)
            ])
