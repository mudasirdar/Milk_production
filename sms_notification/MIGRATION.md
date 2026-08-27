# SMS Notification Module - Odoo 19 Migration Guide

## Module Overview

The SMS Notification module provides SMS messaging capabilities within Odoo. It allows users to send SMS messages to individuals, multiple contacts, or groups through various SMS gateway providers.

### Key Features

- **Send SMS**: Send SMS to individual contacts, multiple partners, or groups
- **SMS Groups**: Create and manage groups of contacts for bulk messaging
- **SMS Templates**: Use predefined templates for quick messaging
- **Multiple Gateway Support**: Integration with various SMS gateway providers:
  - Twilio
  - Plivo
  - ClickSend
  - MSG91
  - Mobily
  - Skebby
  - Netelip
  - Nexmo
  - MessageBird
  - TextLocal
  - SMSHub
  - iSmart
  - Msegat
- **Delivery Reports**: Track SMS delivery status (sent, delivered, undelivered)
- **SMS History**: View history of all sent messages
- **Draft SMS**: Save messages as drafts for later sending
- **Auto-delete**: Option to automatically delete SMS after sending to save space
- **Country Code Support**: Automatic country calling code detection

---

## Migration Changes (Odoo 16/17 to Odoo 19)

### 1. security/ir_rule.xml

**Issue**: `res.groups` fields `users` and `category_id` are no longer writable in Odoo 19.

**Original Code**:
```xml
<record id="sms_notification" model="res.groups">
    <field name="name">Enable SMS Feature</field>
    <field name="category_id" ref="base.module_category_extra"/>
    <field name="users" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
</record>
```

**Fixed Code**:
```xml
<record id="sms_notification" model="res.groups">
    <field name="name">Enable SMS Feature</field>
</record>
```

**Reason**: In Odoo 19, group membership must be assigned differently, and `category_id` handling has changed.

---

### 2. views/sms_sms_view.xml

**Issue 1**: Search view deprecated attributes (`icon`, `expand`, `string` on group, `help` on filters).

**Original Code**:
```xml
<group expand="0" string="Group by...">
    <filter name="group_by_type" string="Group Type" context="{'group_by':'group_type'}" icon="terp-accessories-archiver"/>
    <filter name="group_by_state" string="State" context="{'group_by':'state'}"/>
</group>
```

**Fixed Code**:
```xml
<group>
    <filter name="group_by_type" string="Group Type" context="{'group_by':'group_type'}"/>
    <filter name="group_by_state" string="State" context="{'group_by':'state'}"/>
</group>
```

**Issue 2**: `target="inline"` is no longer valid for `ir.actions.act_window`.

**Original Code**:
```xml
<field name="target">inline</field>
```

**Fixed Code**:
```xml
<field name="target">current</field>
```

---

### 3. views/sms_group_view.xml

**Issue 1**: `mobile` field does not exist in `res.partner` in Odoo 19.

**Original Code**:
```xml
<field name="member_ids">
    <list>
        <field name="name"/>
        <field name="mobile"/>
        <field name="email"/>
    </list>
</field>
```

**Fixed Code**:
```xml
<field name="member_ids">
    <list>
        <field name="name"/>
        <field name="phone"/>
        <field name="email"/>
    </list>
</field>
```

**Issue 2**: Search view deprecated attributes.

**Original Code**:
```xml
<filter name="customer" string="Customer" domain="[('member_type','=','customer')]" help="Customer" />
<filter name="supplier" string="Supplier" domain="[('member_type','=','supplier')]" help="Supplier" />
<filter name="any" string="Any" domain="[('member_type','=','any')]" help="Any" />
<group expand="0" string="Group by...">
    <filter name="group_by_type" string="Type" domain="[]" context="{'group_by':'member_type'}" icon="terp-accessories-archiver"/>
</group>
```

**Fixed Code**:
```xml
<filter name="customer" string="Customer" domain="[('member_type','=','customer')]"/>
<filter name="supplier" string="Supplier" domain="[('member_type','=','supplier')]"/>
<filter name="any" string="Any" domain="[('member_type','=','any')]"/>
<group>
    <filter name="group_by_type" string="Type" domain="[]" context="{'group_by':'member_type'}"/>
</group>
```

---

### 4. views/res_config_view.xml

**Issue**: `target="inline"` is not valid in Odoo 19.

**Original Code**:
```xml
<record id="action_sms_notification_config_settings" model="ir.actions.act_window">
    <field name="target">inline</field>
</record>
```

**Fixed Code**:
```xml
<record id="action_sms_notification_config_settings" model="ir.actions.act_window">
    <field name="target">current</field>
</record>
```

---

### 5. views/sms_report_view.xml

**Issue 1**: `help` attribute on buttons in list view is deprecated.

**Original Code**:
```xml
<button name="send_now" string="Send Now" type="object" icon="fa-paper-plane text-success" invisible="state not in 'new'" help="Send Now"/>
<button name="retry" string="Retry" type="object" icon="fa-repeat text-success" invisible="state not in 'undelivered'" help="Retry"/>
```

**Fixed Code**:
```xml
<button name="send_now" string="Send Now" type="object" icon="fa-paper-plane text-success" invisible="state not in 'new'"/>
<button name="retry" string="Retry" type="object" icon="fa-repeat text-success" invisible="state not in 'undelivered'"/>
```

**Issue 2**: Search view deprecated attributes.

**Original Code**:
```xml
<filter name="outgoing_sms_filter" string="Outgoing" domain="[('state','=','new')]" help="Outgoing SMS"/>
<filter name="delivered_sms_filter" string="Delivered" domain="[('state','=','delivered')]" help="Delivered SMS"/>
<filter name="sent_sms" string="Sent" domain="[('state','=','sent')]" help="Sent SMS"/>
<filter name="undelivered" string="Undelivered" domain="[('state','=','undelivered')]" help="Undelivered SMS"/>
<group expand="0" string="Group By">
    <filter name="group_by_state" string="Status" context="{'group_by':'state'}"/>
</group>
```

**Fixed Code**:
```xml
<filter name="outgoing_sms_filter" string="Outgoing" domain="[('state','=','new')]"/>
<filter name="delivered_sms_filter" string="Delivered" domain="[('state','=','delivered')]"/>
<filter name="sent_sms" string="Sent" domain="[('state','=','sent')]"/>
<filter name="undelivered" string="Undelivered" domain="[('state','=','undelivered')]"/>
<group>
    <filter name="group_by_state" string="Status" context="{'group_by':'state'}"/>
</group>
```

---

## Summary of Deprecated Features in Odoo 19

| Feature | Status | Replacement |
|---------|--------|-------------|
| `target="inline"` on act_window | Removed | Use `target="current"` |
| `help` attribute on filters | Removed | Remove attribute |
| `help` attribute on buttons (list view) | Removed | Remove attribute |
| `icon` attribute on filters | Removed | Remove attribute |
| `expand` attribute on search group | Removed | Remove attribute |
| `string` attribute on search group | Removed | Remove attribute |
| `mobile` field on res.partner | Renamed | Use `phone` field |
| `users` field on res.groups (writable) | Read-only | Assign via user's groups_id |
| `category_id` on res.groups (in XML) | Changed | Handle differently |

---

## Files Modified

1. `security/ir_rule.xml`
2. `views/sms_sms_view.xml`
3. `views/sms_group_view.xml`
4. `views/res_config_view.xml`
5. `views/sms_report_view.xml`

---

## Testing

After applying these changes, test the following:

1. Module installation completes without errors
2. SMS menu appears correctly
3. Send SMS form works properly
4. SMS Groups can be created and managed
5. Delivery reports display correctly
6. Configuration settings are accessible
7. Search and filter functionality works in all views
