# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError


class PropertyPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """Add property counts to portal home"""
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'property_count' in counters:
            property_count = request.env['property.property'].search_count([
                ('owner_id', '=', partner.id)
            ]) if request.env['property.property'].check_access_rights('read', raise_exception=False) else 0
            values['property_count'] = property_count

        if 'inquiry_count' in counters:
            inquiry_count = request.env['property.inquiry'].search_count([
                '|',
                ('property_owner_id', '=', partner.id),
                ('partner_id', '=', partner.id)
            ]) if request.env['property.inquiry'].check_access_rights('read', raise_exception=False) else 0
            values['inquiry_count'] = inquiry_count

        return values

    def _property_get_page_view_values(self, property_obj, access_token, **kwargs):
        """Prepare values for property portal page"""
        values = {
            'property': property_obj,
            'page_name': 'property',
        }
        return self._get_page_view_values(property_obj, access_token, values, 'my_properties_history', False, **kwargs)

    @http.route(['/my/properties', '/my/properties/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_properties(self, page=1, sortby=None, filterby=None, search=None, **kwargs):
        """Display user's properties in portal"""
        Property = request.env['property.property']
        partner = request.env.user.partner_id

        # Sorting options
        sort_order = {
            'date': 'create_date desc, id desc',
            'name': 'name asc',
            'price': 'price desc',
            'state': 'state asc',
        }
        order = sort_order.get(sortby, 'create_date desc, id desc')

        # Filter options
        filter_domain = {
            'all': [],
            'draft': [('state', '=', 'draft')],
            'pending': [('state', '=', 'pending')],
            'approved': [('state', '=', 'approved')],
            'published': [('state', '=', 'published')],
        }
        domain = [('owner_id', '=', partner.id)]
        if filterby and filterby in filter_domain:
            domain += filter_domain[filterby]

        if search:
            domain += ['|', '|', ('name', 'ilike', search), ('reference', 'ilike', search), ('location', 'ilike', search)]

        # Count properties
        property_count = Property.search_count(domain)

        # Pagination
        pager = portal_pager(
            url='/my/properties',
            total=property_count,
            page=page,
            step=self._items_per_page,
            url_args={'sortby': sortby, 'filterby': filterby, 'search': search}
        )

        # Get properties
        properties = Property.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        values = {
            'properties': properties,
            'page_name': 'property',
            'pager': pager,
            'default_url': '/my/properties',
            'sortby': sortby or 'date',
            'filterby': filterby or 'all',
            'search': search or '',
            'searchbar_sortings': {
                'date': {'label': _('Newest'), 'order': 'create_date desc'},
                'name': {'label': _('Name'), 'order': 'name'},
                'price': {'label': _('Price'), 'order': 'price desc'},
                'state': {'label': _('Status'), 'order': 'state'},
            },
            'searchbar_filters': {
                'all': {'label': _('All'), 'domain': []},
                'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
                'pending': {'label': _('Pending'), 'domain': [('state', '=', 'pending')]},
                'approved': {'label': _('Approved'), 'domain': [('state', '=', 'approved')]},
                'published': {'label': _('Published'), 'domain': [('state', '=', 'published')]},
            },
        }

        return request.render('property_management.portal_my_properties', values)

    @http.route(['/my/property/<int:property_id>'], type='http', auth='user', website=True)
    def portal_property_detail(self, property_id, access_token=None, **kwargs):
        """Display property detail in portal"""
        try:
            property_sudo = self._document_check_access('property.property', property_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._property_get_page_view_values(property_sudo, access_token, **kwargs)
        return request.render('property_management.portal_property_detail', values)

    @http.route(['/my/property/<int:property_id>/edit'], type='http', auth='user', website=True)
    def portal_property_edit(self, property_id, access_token=None, **kwargs):
        """Edit property in portal"""
        try:
            property_sudo = self._document_check_access('property.property', property_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Check if user is the owner
        if property_sudo.owner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my')

        # Get necessary data for form
        PropertyType = request.env['property.type']
        Country = request.env['res.country']
        State = request.env['res.country.state']
        Amenity = request.env['property.amenity']

        property_types = PropertyType.search([('active', '=', True)])
        countries = Country.search([])
        states = State.search([]) if property_sudo.country_id else State.search([('country_id', '=', property_sudo.country_id.id)])
        amenities = Amenity.search([('active', '=', True)])

        values = {
            'property': property_sudo,
            'property_types': property_types,
            'countries': countries,
            'states': states,
            'amenities': amenities,
            'page_name': 'property_edit',
        }

        return request.render('property_management.portal_property_edit', values)

    @http.route(['/my/property/<int:property_id>/update'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_property_update(self, property_id, access_token=None, **post):
        """Update property from portal"""
        try:
            property_sudo = self._document_check_access('property.property', property_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Check if user is the owner
        if property_sudo.owner_id.id != request.env.user.partner_id.id:
            return request.redirect('/my')

        # Prepare values
        vals = {}

        # Basic fields
        if 'name' in post:
            vals['name'] = post.get('name')
        if 'description' in post:
            vals['description'] = post.get('description')
        if 'property_type_id' in post:
            vals['property_type_id'] = int(post.get('property_type_id'))
        if 'transaction_type' in post:
            vals['transaction_type'] = post.get('transaction_type')
        if 'price' in post:
            vals['price'] = float(post.get('price', 0))
        if 'monthly_rent' in post:
            vals['monthly_rent'] = float(post.get('monthly_rent', 0))

        # Location
        if 'street' in post:
            vals['street'] = post.get('street')
        if 'city' in post:
            vals['city'] = post.get('city')
        if 'state_id' in post:
            vals['state_id'] = int(post.get('state_id')) if post.get('state_id') else False
        if 'zip' in post:
            vals['zip'] = post.get('zip')
        if 'country_id' in post:
            vals['country_id'] = int(post.get('country_id'))

        # Characteristics
        if 'bedrooms' in post:
            vals['bedrooms'] = int(post.get('bedrooms', 0))
        if 'bathrooms' in post:
            vals['bathrooms'] = int(post.get('bathrooms', 0))
        if 'parking_spaces' in post:
            vals['parking_spaces'] = int(post.get('parking_spaces', 0))
        if 'building_area' in post:
            vals['building_area'] = float(post.get('building_area', 0))
        if 'land_area' in post:
            vals['land_area'] = float(post.get('land_area', 0))
        if 'year_built' in post:
            vals['year_built'] = int(post.get('year_built', 0)) if post.get('year_built') else False
        if 'property_condition' in post:
            vals['property_condition'] = post.get('property_condition')

        # Amenities
        if 'amenity_ids' in post:
            amenity_ids = [int(a) for a in request.httprequest.form.getlist('amenity_ids')]
            vals['amenity_ids'] = [(6, 0, amenity_ids)]

        # Update property
        if vals:
            property_sudo.sudo().write(vals)

        return request.redirect(f'/my/property/{property_id}?update_success=1')

    @http.route(['/my/property/new'], type='http', auth='user', website=True)
    def portal_property_new(self, **kwargs):
        """Create new property in portal"""
        PropertyType = request.env['property.type']
        Country = request.env['res.country']
        Amenity = request.env['property.amenity']

        property_types = PropertyType.search([('active', '=', True)])
        countries = Country.search([])
        amenities = Amenity.search([('active', '=', True)])

        values = {
            'property_types': property_types,
            'countries': countries,
            'amenities': amenities,
            'page_name': 'property_new',
        }

        return request.render('property_management.portal_property_new', values)

    @http.route(['/my/property/create'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_property_create(self, **post):
        """Create new property from portal"""
        Property = request.env['property.property']
        partner = request.env.user.partner_id

        # Prepare values
        vals = {
            'owner_id': partner.id,
            'name': post.get('name'),
            'description': post.get('description', ''),
            'property_type_id': int(post.get('property_type_id')),
            'transaction_type': post.get('transaction_type'),
            'price': float(post.get('price', 0)),
            'city': post.get('city'),
            'country_id': int(post.get('country_id')),
        }

        # Optional fields
        if post.get('monthly_rent'):
            vals['monthly_rent'] = float(post.get('monthly_rent'))
        if post.get('street'):
            vals['street'] = post.get('street')
        if post.get('state_id'):
            vals['state_id'] = int(post.get('state_id'))
        if post.get('zip'):
            vals['zip'] = post.get('zip')
        if post.get('bedrooms'):
            vals['bedrooms'] = int(post.get('bedrooms', 0))
        if post.get('bathrooms'):
            vals['bathrooms'] = int(post.get('bathrooms', 0))
        if post.get('parking_spaces'):
            vals['parking_spaces'] = int(post.get('parking_spaces', 0))
        if post.get('building_area'):
            vals['building_area'] = float(post.get('building_area', 0))
        if post.get('land_area'):
            vals['land_area'] = float(post.get('land_area', 0))
        if post.get('year_built'):
            vals['year_built'] = int(post.get('year_built'))
        if post.get('property_condition'):
            vals['property_condition'] = post.get('property_condition')

        # Amenities
        if 'amenity_ids' in post:
            amenity_ids = [int(a) for a in request.httprequest.form.getlist('amenity_ids')]
            vals['amenity_ids'] = [(6, 0, amenity_ids)]

        # Create property
        property_obj = Property.sudo().create(vals)

        return request.redirect(f'/my/property/{property_obj.id}?create_success=1')

    @http.route(['/my/inquiries', '/my/inquiries/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_inquiries(self, page=1, sortby=None, filterby=None, **kwargs):
        """Display user's property inquiries in portal"""
        Inquiry = request.env['property.inquiry']
        partner = request.env.user.partner_id

        # Sorting
        sort_order = {
            'date': 'create_date desc',
            'property': 'property_id',
            'state': 'state',
        }
        order = sort_order.get(sortby, 'create_date desc')

        # Filtering
        filter_domain = {
            'all': [],
            'new': [('state', '=', 'new')],
            'in_progress': [('state', '=', 'in_progress')],
            'replied': [('state', '=', 'replied')],
            'closed': [('state', '=', 'closed')],
        }

        domain = ['|', ('property_owner_id', '=', partner.id), ('partner_id', '=', partner.id)]
        if filterby and filterby in filter_domain:
            domain += filter_domain[filterby]

        # Count
        inquiry_count = Inquiry.search_count(domain)

        # Pagination
        pager = portal_pager(
            url='/my/inquiries',
            total=inquiry_count,
            page=page,
            step=self._items_per_page,
            url_args={'sortby': sortby, 'filterby': filterby}
        )

        # Get inquiries
        inquiries = Inquiry.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values = {
            'inquiries': inquiries,
            'page_name': 'inquiry',
            'pager': pager,
            'default_url': '/my/inquiries',
            'sortby': sortby or 'date',
            'filterby': filterby or 'all',
            'searchbar_sortings': {
                'date': {'label': _('Date'), 'order': 'create_date desc'},
                'property': {'label': _('Property'), 'order': 'property_id'},
                'state': {'label': _('Status'), 'order': 'state'},
            },
            'searchbar_filters': {
                'all': {'label': _('All'), 'domain': []},
                'new': {'label': _('New'), 'domain': [('state', '=', 'new')]},
                'in_progress': {'label': _('In Progress'), 'domain': [('state', '=', 'in_progress')]},
                'replied': {'label': _('Replied'), 'domain': [('state', '=', 'replied')]},
                'closed': {'label': _('Closed'), 'domain': [('state', '=', 'closed')]},
            },
        }

        return request.render('property_management.portal_my_inquiries', values)

    @http.route(['/my/inquiry/<int:inquiry_id>'], type='http', auth='user', website=True)
    def portal_inquiry_detail(self, inquiry_id, access_token=None, **kwargs):
        """Display inquiry detail in portal"""
        try:
            inquiry_sudo = self._document_check_access('property.inquiry', inquiry_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'inquiry': inquiry_sudo,
            'page_name': 'inquiry',
        }

        return request.render('property_management.portal_inquiry_detail', values)
