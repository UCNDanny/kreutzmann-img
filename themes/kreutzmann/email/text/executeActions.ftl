<#ftl output_format="plainText">
Kreutzmann — Your account setup

We’re glad to welcome you to Kreutzmann’s in-house services.
Follow the link below to complete the actions required for your account.
<#if requiredActions?? && requiredActions?has_content>
Required steps:
<#list requiredActions as action>
- ${msg("requiredAction." + action)}
</#list>
</#if>

Continue account setup:
${link}

This account-action link expires in ${linkExpirationFormatter(linkExpiration)}.

If you weren’t expecting this account email, contact your administrator before continuing.
Need a hand? info@kreutzmann.gl
