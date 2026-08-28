# Textbee SMS Integration - Setup Guide

## 1. Install the Module

1. Copy the `textbee_sms` folder to your Odoo 19 addons path.
2. Restart the Odoo server.
3. Go to **Apps** → **Update Apps List**.
4. Search for **"Textbee SMS Integration"** → Click **Install**.

---

## 2. Configure the API Key (Optional)

The default API key is already set. To change it:

1. Activate **Developer Mode** (Settings → General Settings → scroll down → Developer Tools → Activate).
2. Go to **Settings → Technical → Parameters → System Parameters**.
3. Click **New**.
   - **Key**: `textbee_sms.api_key`
   - **Value**: Your Textbee API key
4. Click **Save**.

> If you skip this step, it uses the default key: `txb_ayhHP7gzDPfybNq83Zqnt1R7BM6dT0Sp`

---

## 3. Ensure Contacts Have Phone Numbers

1. Go to **Contacts** → open a contact.
2. Make sure either the **Phone** or **Mobile** field is filled.
3. The module checks `Phone` first, then falls back to `Mobile`.

---

## 4. Send SMS from a Sale Order

### Option A - Header Button

1. Go to **Sales → Orders → Orders**.
2. Open any Sale Order.
3. Click the **"Send Textbee SMS"** button in the header.

### Option B - Action Menu (single or bulk)

1. From the Sale Order list view, select one or more orders.
2. Click **Action → Send Textbee SMS**.

---

## 5. Send SMS from a Purchase Order

Same two options:

1. Go to **Purchase → Orders**.
2. Open a Purchase Order → click **"Send Textbee SMS"** in the header.
3. Or select orders from list view → **Action → Send Textbee SMS**.

---

## 6. Check SMS Status

After sending, check the **Chatter** (bottom of the order form):

- **Success**: *"Textbee SMS sent successfully to +91XXXXXXXXXX"*
- **No phone**: *"Textbee SMS failed: No phone number found for John"*
- **API error**: *"Textbee SMS failed: [error details]"*

Server logs also capture errors for debugging (`grep "Textbee"` in your Odoo log).

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Button not visible | Update Apps List & reinstall the module |
| "No phone number found" | Add phone/mobile to the contact |
| API errors (401/403) | Check your API key in System Parameters |
| Timeout errors | Check your server's internet connectivity |
