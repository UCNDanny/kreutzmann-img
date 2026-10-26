<#ftl output_format="HTML" auto_esc=true>
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Complete your Kreutzmann account setup</title>
<style>
a[target="_blank"]:not(:empty):not(:has(*))::after {
  content: "↗";
  display: inline-block;
  margin-inline-start: 0.2em;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 0.75em;
  font-weight: normal;
  line-height: 1;
  vertical-align: 0.08em;
}
/* Inline styles remain usable in clients that discard media queries. */
@media screen and (max-width:480px) {
  .email-outer { padding:20px 12px !important; }
  .email-brand { padding-bottom:18px !important; }
  .email-card { padding:28px 20px !important; }
  .email-heading { font-size:28px !important; line-height:34px !important; letter-spacing:-0.5px !important; }
  .email-cta { width:100% !important; }
  .email-cta a { display:block !important; text-align:center !important; padding:15px 12px !important; }
}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f4f2ee;color:#1f2926;-webkit-text-size-adjust:100%;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">Your Kreutzmann account needs a few final steps.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f4f2ee" style="width:100%;background-color:#f4f2ee;">
<tr><td align="center" class="email-outer" style="padding:36px 16px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;table-layout:fixed;">
<tr><td class="email-brand" style="padding:0 8px 25px;font-family:Arial,Helvetica,sans-serif;font-size:23px;font-weight:bold;letter-spacing:-0.7px;color:#165b4b;">Kreutzmann</td></tr>
<tr><td class="email-card" bgcolor="#fdfcfa" style="background-color:#fdfcfa;border:1px solid #d9ded6;border-radius:6px;padding:36px 28px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;table-layout:fixed;">
<tr><td style="padding:0 0 22px;font-family:Arial,Helvetica,sans-serif;font-size:11px;line-height:18px;letter-spacing:2px;color:#606b65;">YOUR ACCOUNT SETUP</td></tr>
<tr><td><h1 class="email-heading" style="overflow-wrap:anywhere;word-wrap:break-word;margin:0 0 22px;font-family:Georgia,'Times New Roman',serif;font-size:38px;line-height:44px;font-weight:normal;letter-spacing:-1px;color:#1f2926;">You’re invited to<br><span style="color:#165b4b;font-style:italic;">Kreutzmann’s in-house services.</span></h1></td></tr>
<tr><td style="padding:0 0 16px;font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:26px;color:#1f2926;overflow-wrap:anywhere;word-break:break-word;">We’re glad to welcome you to Kreutzmann’s in-house services.</td></tr>
<tr><td style="padding:0 0 28px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:25px;color:#606b65;">Follow the link below to complete the actions required for your account.<#if requiredActions?? && requiredActions?has_content><br><br>Required steps: <#list requiredActions as action>${msg("requiredAction." + action)}<#sep>, </#list>.</#if></td></tr>
<tr><td style="padding:0 0 20px;">
<table class="email-cta" role="presentation" cellpadding="0" cellspacing="0" border="0"><tr><td bgcolor="#165b4b" style="background-color:#165b4b;border-radius:4px;mso-padding-alt:15px 24px;"><a href="${link}" target="_blank" rel="noopener noreferrer" style="display:inline-block;border:1px solid #165b4b;border-radius:4px;padding:14px 23px;font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:22px;font-weight:bold;text-decoration:none;color:#ffffff;">Continue account setup</a></td></tr></table>
</td></tr>
<tr><td style="padding:0 0 27px;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:21px;color:#606b65;">This account-action link expires in ${linkExpirationFormatter(linkExpiration)}.</td></tr>
<tr><td style="border-top:1px solid #d9ded6;padding:23px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:13px;line-height:21px;color:#606b65;">If the button doesn't work, copy and paste this link into your browser:</td></tr>
<tr><td style="padding:9px 0 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:20px;word-break:break-all;overflow-wrap:anywhere;"><a href="${link}" target="_blank" rel="noopener noreferrer" style="color:#165b4b;text-decoration:underline;word-break:break-all;overflow-wrap:anywhere;">${link}</a></td></tr>
</table>
</td></tr>
<tr><td style="padding:23px 8px 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:20px;color:#606b65;">If you weren’t expecting this account email, contact your administrator before continuing.</td></tr>
<tr><td style="padding:18px 8px 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:20px;color:#606b65;">Need a hand? <a href="mailto:info@kreutzmann.gl" style="color:#165b4b;text-decoration:underline;">info@kreutzmann.gl</a><br>Practical tools for everyday operations.</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table>
</body>
</html>
