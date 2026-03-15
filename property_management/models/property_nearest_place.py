# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyNearestPlace(models.Model):
    _name = 'property.nearest.place'
    _description = 'Property Nearest Place'
    _order = 'distance, name'

    name = fields.Char(string='Place Name', required=True)
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  ondelete='cascade')

    place_type = fields.Selection([
        ('school', 'School'),
        ('hospital', 'Hospital/Clinic'),
        ('shopping', 'Shopping Center/Mall'),
        ('restaurant', 'Restaurant'),
        ('park', 'Park/Garden'),
        ('transport', 'Public Transport'),
        ('bank', 'Bank/ATM'),
        ('pharmacy', 'Pharmacy'),
        ('gym', 'Gym/Fitness Center'),
        ('airport', 'Airport'),
        ('railway', 'Railway Station'),
        ('bus_stop', 'Bus Stop'),
        ('metro', 'Metro Station'),
        ('market', 'Market'),
        ('police', 'Police Station'),
        ('fire', 'Fire Station'),
        ('religious', 'Religious Place'),
        ('other', 'Other')
    ], string='Place Type', required=True)

    distance = fields.Float(string='Distance (km)', digits=(10, 2), required=True)
    distance_unit = fields.Selection([
        ('km', 'Kilometers'),
        ('m', 'Meters'),
        ('mi', 'Miles')
    ], string='Distance Unit', default='km')

    travel_time = fields.Integer(string='Travel Time (minutes)',
                                 help='Approximate travel time by car/transport')

    address = fields.Char(string='Address')
    description = fields.Text(string='Description')

    # Optional coordinates for the place
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
