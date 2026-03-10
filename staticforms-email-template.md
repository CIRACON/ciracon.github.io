# StaticForms – Email Response Template

Paste the HTML below into the StaticForms custom email template field.

---

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Ciracon</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 0; color: #1a1a2e; background-color: #f8f9fa;">

  <!-- Header -->
  <div style="background-color: #0B0F14; padding: 32px 24px; text-align: center;">
    <h1 style="margin: 0; font-size: 18px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #E5E7EB;">
      <span style="color: #3B82F6;">C</span>ira<span style="color: #3B82F6;">c</span>on
    </h1>
    <p style="margin: 8px 0 0; font-size: 12px; color: #9CA3AF; letter-spacing: 0.04em;">
      Engineering-First Consulting
    </p>
  </div>

  <!-- Body -->
  <div style="background-color: #ffffff; padding: 32px 24px;">
    <h2 style="margin: 0 0 8px; font-size: 20px; font-weight: 600; color: #0F172A;">
      Thank you for reaching out, {{name}}
    </h2>
    <p style="margin: 0 0 24px; font-size: 14px; color: #6B7280;">
      We've received your message and a member of our team will personally follow up within one business day.
    </p>

    <!-- AI Reply / Message -->
    <div style="background-color: #F1F5F9; border-left: 3px solid #3B82F6; padding: 16px 20px; border-radius: 4px; margin-bottom: 24px; font-size: 14px; line-height: 1.7; color: #334155;">
      {{message}}
    </div>

    <!-- What's Next -->
    <h3 style="margin: 0 0 12px; font-size: 14px; font-weight: 600; color: #0F172A; text-transform: uppercase; letter-spacing: 0.04em;">
      What happens next
    </h3>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
      <tr>
        <td style="padding: 8px 12px 8px 0; vertical-align: top; color: #3B82F6; font-weight: 600; font-size: 14px; width: 24px;">1.</td>
        <td style="padding: 8px 0; font-size: 14px; color: #334155;">We review your inquiry and match it to the right expertise.</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px 8px 0; vertical-align: top; color: #3B82F6; font-weight: 600; font-size: 14px;">2.</td>
        <td style="padding: 8px 0; font-size: 14px; color: #334155;">A team member follows up to schedule an initial conversation.</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px 8px 0; vertical-align: top; color: #3B82F6; font-weight: 600; font-size: 14px;">3.</td>
        <td style="padding: 8px 0; font-size: 14px; color: #334155;">We scope your challenge together — no commitment required.</td>
      </tr>
    </table>

    <!-- CTA -->
    <div style="text-align: center; margin: 32px 0 8px;">
      <a href="https://www.ciracon.com/services.html" style="display: inline-block; background-color: #3B82F6; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 6px; font-size: 14px; font-weight: 600;">
        Explore Our Services
      </a>
    </div>
  </div>

  <!-- Footer -->
  <div style="background-color: #0B0F14; padding: 24px; text-align: center;">
    <p style="margin: 0 0 4px; font-size: 12px; color: #9CA3AF;">
      AI Engineering · Platform Engineering · DevOps · Cloud
    </p>
    <p style="margin: 0 0 12px; font-size: 12px; color: #6B7280;">
      <a href="mailto:info@ciracon.com" style="color: #3B82F6; text-decoration: none;">info@ciracon.com</a>
      &nbsp;·&nbsp;
      <a href="https://www.ciracon.com" style="color: #3B82F6; text-decoration: none;">www.ciracon.com</a>
    </p>
    <p style="margin: 0; font-size: 11px; color: #4B5563;">
      © 2026 Ciracon. All rights reserved.
    </p>
  </div>

</body>
</html>
```
