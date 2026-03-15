# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.website.controllers.main import QueryURL


class PropertyController(http.Controller):

    def _get_search_domain(self, search=None, property_type=None, transaction_type=None,
                          city=None, country=None, min_price=None, max_price=None,
                          bedrooms=None, bathrooms=None, min_area=None, max_area=None,
                          amenities=None, parking=None):
        """Build search domain based on filters"""
        domain = [('website_published', '=', True), ('state', '=', 'published')]

        if search:
            domain += ['|', '|', ('name', 'ilike', search),
                      ('description', 'ilike', search),
                      ('location', 'ilike', search)]

        if property_type:
            try:
                property_type = int(property_type)
                domain += [('property_type_id', '=', property_type)]
            except ValueError:
                pass

        if transaction_type:
            domain += [('transaction_type', '=', transaction_type)]

        if city:
            domain += [('city', 'ilike', city)]

        if country:
            try:
                country = int(country)
                domain += [('country_id', '=', country)]
            except ValueError:
                pass

        if min_price:
            try:
                min_price = float(min_price)
                domain += [('price', '>=', min_price)]
            except ValueError:
                pass

        if max_price:
            try:
                max_price = float(max_price)
                domain += [('price', '<=', max_price)]
            except ValueError:
                pass

        if bedrooms:
            try:
                bedrooms = int(bedrooms)
                domain += [('bedrooms', '>=', bedrooms)]
            except ValueError:
                pass

        if bathrooms:
            try:
                bathrooms = int(bathrooms)
                domain += [('bathrooms', '>=', bathrooms)]
            except ValueError:
                pass

        if min_area:
            try:
                min_area = float(min_area)
                domain += [('building_area', '>=', min_area)]
            except ValueError:
                pass

        if max_area:
            try:
                max_area = float(max_area)
                domain += [('building_area', '<=', max_area)]
            except ValueError:
                pass

        if amenities:
            try:
                amenity_ids = [int(a) for a in amenities.split(',') if a]
                for amenity_id in amenity_ids:
                    domain += [('amenity_ids', 'in', amenity_id)]
            except ValueError:
                pass

        if parking:
            try:
                parking = int(parking)
                domain += [('parking_spaces', '>=', parking)]
            except ValueError:
                pass

        return domain

    @http.route(['/properties', '/properties/page/<int:page>'], type='http', auth='public', website=True)
    def property_list(self, page=1, search='', property_type=None, transaction_type=None,
                     city=None, country=None, min_price=None, max_price=None,
                     bedrooms=None, bathrooms=None, min_area=None, max_area=None,
                     amenities=None, parking=None, sortby=None, **kwargs):
        """Display property listing page with filters"""
        Property = request.env['property.property']
        PropertyType = request.env['property.type']
        Country = request.env['res.country']
        Amenity = request.env['property.amenity']

        # Get filter options
        property_types = PropertyType.search([('active', '=', True)])
        countries = Country.search([])
        available_amenities = Amenity.search([('active', '=', True)])

        # Build search domain
        domain = self._get_search_domain(
            search=search,
            property_type=property_type,
            transaction_type=transaction_type,
            city=city,
            country=country,
            min_price=min_price,
            max_price=max_price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            min_area=min_area,
            max_area=max_area,
            amenities=amenities,
            parking=parking
        )

        # Sorting options
        sort_order = {
            'newest': 'create_date desc, id desc',
            'price_low': 'price asc',
            'price_high': 'price desc',
            'name': 'name asc',
        }
        order = sort_order.get(sortby, 'create_date desc, id desc')

        # Pagination
        properties_per_page = 12
        total_properties = Property.search_count(domain)
        pager = request.website.pager(
            url='/properties',
            total=total_properties,
            page=page,
            step=properties_per_page,
            url_args={
                'search': search,
                'property_type': property_type,
                'transaction_type': transaction_type,
                'city': city,
                'country': country,
                'min_price': min_price,
                'max_price': max_price,
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'min_area': min_area,
                'max_area': max_area,
                'amenities': amenities,
                'parking': parking,
                'sortby': sortby,
            }
        )

        # Get properties
        properties = Property.search(
            domain,
            limit=properties_per_page,
            offset=pager['offset'],
            order=order
        )

        # Build query URL for filters
        keep_query = QueryURL('/properties',
                             search=search,
                             property_type=property_type,
                             transaction_type=transaction_type,
                             city=city,
                             country=country,
                             min_price=min_price,
                             max_price=max_price,
                             bedrooms=bedrooms,
                             bathrooms=bathrooms,
                             min_area=min_area,
                             max_area=max_area,
                             amenities=amenities,
                             parking=parking)

        values = {
            'properties': properties,
            'pager': pager,
            'search': search,
            'property_types': property_types,
            'countries': countries,
            'amenities': available_amenities,
            'filters': {
                'property_type': int(property_type) if property_type else None,
                'transaction_type': transaction_type,
                'city': city,
                'country': int(country) if country else None,
                'min_price': float(min_price) if min_price else None,
                'max_price': float(max_price) if max_price else None,
                'bedrooms': int(bedrooms) if bedrooms else None,
                'bathrooms': int(bathrooms) if bathrooms else None,
                'min_area': float(min_area) if min_area else None,
                'max_area': float(max_area) if max_area else None,
                'amenities': amenities,
                'parking': int(parking) if parking else None,
            },
            'sortby': sortby or 'newest',
            'keep_query': keep_query,
        }

        return request.render('property_management.property_listing_page', values)

    @http.route(['/property/<int:property_id>'], type='http', auth='public', website=True)
    def property_detail(self, property_id, **kwargs):
        """Display property detail page"""
        Property = request.env['property.property']

        property_obj = Property.sudo().search([
            ('id', '=', property_id),
            ('website_published', '=', True),
            ('state', '=', 'published')
        ], limit=1)

        if not property_obj:
            return request.redirect('/properties')

        # Increment views counter
        property_obj.increment_views()

        # Get similar properties
        similar_domain = [
            ('id', '!=', property_id),
            ('website_published', '=', True),
            ('state', '=', 'published'),
            ('property_type_id', '=', property_obj.property_type_id.id)
        ]
        similar_properties = Property.search(similar_domain, limit=4, order='create_date desc')

        values = {
            'property': property_obj,
            'similar_properties': similar_properties,
            'main_object': property_obj,
        }

        return request.render('property_management.property_detail_page', values)

    @http.route(['/property/<int:property_id>/inquiry'], type='http', auth='public', website=True, methods=['POST'])
    def property_inquiry_submit(self, property_id, **post):
        """Handle property inquiry form submission"""
        Property = request.env['property.property']
        Inquiry = request.env['property.inquiry']
        Partner = request.env['res.partner']

        property_obj = Property.sudo().search([
            ('id', '=', property_id),
            ('website_published', '=', True),
            ('state', '=', 'published')
        ], limit=1)

        if not property_obj:
            return request.redirect('/properties')

        # Get or create partner
        partner = None
        if request.env.user._is_public():
            # Public user - find or create partner
            email = post.get('email', '').strip()
            name = post.get('name', '').strip()
            phone = post.get('phone', '').strip()

            if email:
                partner = Partner.sudo().search([('email', '=', email)], limit=1)
                if not partner:
                    partner = Partner.sudo().create({
                        'name': name or email,
                        'email': email,
                        'phone': phone,
                    })
        else:
            # Logged in user
            partner = request.env.user.partner_id

        if not partner:
            return request.redirect(f'/property/{property_id}?inquiry_error=1')

        # Create inquiry
        inquiry_vals = {
            'name': post.get('subject', _('Property Inquiry')),
            'property_id': property_id,
            'partner_id': partner.id,
            'email': post.get('email', partner.email),
            'phone': post.get('phone', partner.phone),
            'message': post.get('message', ''),
            'state': 'new',
        }

        Inquiry.sudo().create(inquiry_vals)

        return request.redirect(f'/property/{property_id}?inquiry_success=1')
