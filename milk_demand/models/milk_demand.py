from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MilkDemand(models.Model):
    _name = 'milk.demand'
    _description = 'Milk Product Demand'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'demand_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        domain="[('customer_rank', '>', 0)]",
        help='Customer who is placing the demand'
    )
    demand_date = fields.Date(
        string='Demand Date',
        required=True,
        default=lambda self: fields.Date.add(fields.Date.today(), days=1),
        tracking=True,
        help='Date for which the demand is placed (usually next day)'
    )
    creation_date = fields.Date(
        string='Creation Date',
        default=fields.Date.today,
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('converted', 'Converted to SO'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many(
        'milk.demand.line',
        'demand_id',
        string='Demand Lines'
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        readonly=True,
        copy=False
    )
    sale_order_count = fields.Integer(
        compute='_compute_sale_order_count',
        string='Sales Orders'
    )

    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # Totals
    total_qty = fields.Float(
        string='Total Quantity',
        compute='_compute_totals',
        store=True
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_totals',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency'
    )

    @api.depends('sale_order_id')
    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = 1 if rec.sale_order_id else 0

    @api.depends('line_ids.quantity', 'line_ids.subtotal')
    def _compute_totals(self):
        for rec in self:
            rec.total_qty = sum(rec.line_ids.mapped('quantity'))
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('milk.demand') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm the demand."""
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('Please add at least one product line before confirming.'))
            rec.state = 'confirmed'

    def action_cancel(self):
        """Cancel the demand."""
        for rec in self:
            if rec.state == 'converted':
                raise UserError(_('Cannot cancel a demand that has been converted to Sales Order.'))
            rec.state = 'cancelled'

    def action_reset_draft(self):
        """Reset to draft."""
        for rec in self:
            if rec.state == 'converted':
                raise UserError(_('Cannot reset a demand that has been converted to Sales Order.'))
            rec.state = 'draft'

    def action_convert_to_sale_order(self):
        """Convert demand to Sales Order."""
        self.ensure_one()

        if self.state != 'confirmed':
            raise UserError(_('Only confirmed demands can be converted to Sales Order.'))

        if self.sale_order_id:
            raise UserError(_('This demand has already been converted to Sales Order.'))

        if not self.line_ids:
            raise UserError(_('Cannot create Sales Order without any product lines.'))

        # Create Sales Order
        so_vals = {
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.name,
            'company_id': self.company_id.id,
            'client_order_ref': f'Demand: {self.name}',
        }

        sale_order = self.env['sale.order'].create(so_vals)

        # Create Sales Order Lines
        for line in self.line_ids:
            sol_vals = {
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'price_unit': line.price_unit,
                'rfaf_crates': line.crates,
            }
            self.env['sale.order.line'].create(sol_vals)

        self.write({
            'sale_order_id': sale_order.id,
            'state': 'converted',
        })

        self.message_post(
            body=_('Demand converted to Sales Order: %s') % sale_order.name
        )

        # Return action to open the created Sales Order
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_sale_order(self):
        """View the linked Sales Order."""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No Sales Order linked to this demand.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class MilkDemandLine(models.Model):
    _name = 'milk.demand.line'
    _description = 'Milk Demand Line'
    _order = 'sequence, id'

    demand_id = fields.Many2one(
        'milk.demand',
        string='Demand',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('sale_ok', '=', True)]"
    )
    crates = fields.Integer(
        string='Crates',
        default=0,
        help='Number of crates. Quantity is calculated based on product units per crate.',
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure'
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price'
    )
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True
    )

    state = fields.Selection(
        related='demand_id.state',
        string='Status',
        store=True
    )

    notes = fields.Char(string='Notes')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.crates = 0
            # Get price from pricelist or product
            if self.demand_id.partner_id:
                pricelist = self.demand_id.partner_id.property_product_pricelist
                if pricelist:
                    price = pricelist._get_product_price(
                        self.product_id, self.quantity or 1.0
                    )
                    self.price_unit = price
                else:
                    self.price_unit = self.product_id.lst_price
            else:
                self.price_unit = self.product_id.lst_price

    @api.onchange('crates')
    def _onchange_crates(self):
        """Compute quantity from crates for products with crates enabled.
        Uses the product's configured units per crate.
        """
        for line in self:
            if line.product_id and line.product_id.rfaf_use_crates and line.crates:
                units_per_crate = line.product_id.rfaf_units_per_crate or 12.0
                line.quantity = line.crates * units_per_crate

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
