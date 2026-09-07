# Deploy on Railway

This uses Railway's HTTPS edge and private networking. No additional ingress proxy
or database container is included. Read `SECURITY-CONTROLS.md` first: Railway host
FIPS qualification and CIS/STIG host controls remain unverified.

## 1. Prerequisites

- Control of the public DNS names for the gateway and for Keycloak.
- All applications and the gateway in the same Railway project environment.
- A dedicated external PostgreSQL database/user, verified TLS configuration, and
  a tested backup/restore process. Confirm the PostgreSQL version is supported by Keycloak.
- The external database certificate matches the JDBC hostname. Its trust anchor
  is known. `sslmode=require` alone does not verify server identity.
- Published image digests from your repository's successful release workflow.

Public CA certificates and tooling need no purchase. Hosting can incur charges.
Railway handles public certificate issuance/renewal. Verify the actual issuer if
Let's Encrypt specifically is a requirement; an image cannot select Railway's CA.

## 2. Keycloak service

Create an image service using your published Keycloak digest. Associate
`railway/keycloak.json` where Railway supports repository config for that service;
for an image-only service, enter its equivalent settings in the UI. These JSON files
configure deployment behavior, not image source credentials or custom domains.

Leave the start command empty. The image starts Keycloak through its own
entrypoint (a shell-free Java launcher that also prepares `/tmp/database-ca.pem`);
there is no `kc.sh` or `keycloak-entrypoint.sh` in it. A custom start command,
including one copied from an official-image service, breaks the deployment.

Attach the Keycloak public domain, targeting **8080**, and configure:

```dotenv
KC_HOSTNAME=https://<keycloak-domain>
KC_HTTP_ENABLED=true
KC_PROXY_HEADERS=xforwarded
KC_DB_USERNAME=keycloak
KC_DB_PASSWORD=<database password>
KC_DB_URL=jdbc:postgresql://<certificate-matching-host>:5432/keycloak?sslmode=verify-full&sslrootcert=/tmp/database-ca.pem
KC_BOOTSTRAP_ADMIN_USERNAME=bootstrap-admin
KC_BOOTSTRAP_ADMIN_PASSWORD=<random password of at least 14 characters>
```

The image automatically deploys its bundled public CA certificates to
`/tmp/database-ca.pem`. No certificate file needs to be downloaded or mounted.
For a database signed by a private CA, supply its trusted PEM through `DATABASE_CA_PEM`
in the deployment environment; the entrypoint uses it in place of the public bundle.
The JDBC URL explicitly selects that trust source. This does not modify Java's general
HTTPS trust store. Do not set a custom start command; the entrypoint prepares this file.

Set an appropriate memory limit (start with 2 GiB) and one replica. Verify the service's
writable paths and platform security controls. `KC_FEATURES=fips` and
`KC_FIPS_MODE=strict` are baked into the image; do not override them to bypass errors.
Approved-mode initialization is not evidence that the underlying JVM/host is qualified.

Do not expose or route port **9000** publicly. The supplied Keycloak Railway JSON
intentionally does not invent a management-port healthcheck setting. Configure a
supported private readiness probe to `/health/ready` on port 9000, or establish an
appropriate platform-supported deployment gate before production rollout. Gateway
healthchecks do not substitute for Keycloak readiness monitoring.

Restrict administrative routes through available platform/network access controls.
A separate admin hostname alone does not block the Admin API on other routes.

## 3. Provision the realm

This repository does not ship or import realm configuration. Create the realm and its
client through the Keycloak admin console or your own provisioning process, against the
running Keycloak service. Do not bake secrets into an image.

Sign in at `https://<keycloak-domain>/admin/` with the bootstrap administrator, then:

- Create the realm. Keep self-registration and password reset disabled until SMTP and
  an approval process are in place.
- Create an OIDC confidential client for the gateway with the callback URL shown in
  `docker-compose.yml`. Record its client ID and secret for the gateway variables.
- Create the `gateway-users` group and add approved users. Give each user a verified
  email address matching `OAUTH2_PROXY_EMAIL_DOMAINS`.
- Create a permanent administrator with the intended access policy, then delete the
  bootstrap administrator and remove `KC_BOOTSTRAP_ADMIN_*` from Railway.

Confirm issuer discovery at
`https://<keycloak-domain>/realms/<realm>/.well-known/openid-configuration`. The
`OAUTH2_PROXY_OIDC_ISSUER_URL` value must match this issuer exactly. Later realm and
credential changes are explicit administrative operations. Realms already present in the
external database are picked up automatically; Keycloak's local container data is temporary.

## 4. Application services

Disable every public domain and public TCP proxy for protected applications. Confirm
there are no alternate public endpoints left behind. Verify each private hostname,
port, and IPv4/IPv6 binding. Other services in the same Railway environment may still
reach these upstreams; private networking is not per-service authorization.

Applications must serve their public base paths:

| Prefix | Private upstream |
| --- | --- |
| `/<app>/` | `http://<app-service>.railway.internal:8080/<app>/` |
| `/<app>-api/` | `http://<api-service>.railway.internal:8080/<app>-api/` |
| `/` | `http://<root-service>.railway.internal:8080/` |

No prefix stripping occurs. oauth2-proxy chooses the longest matching upstream path.
Reserve `/oauth2/*`, `/ping`, `/ready`, and other built-in gateway endpoints. Confirm
bare paths such as `/<app>` redirect to their slash form; do not assume catch-all
routing produces the intended redirect. If needed implement these redirects in the
root application. Test that a sibling path such as `/<app>-other` does not enter the
`/<app>` upstream.

All apps share an origin and gateway access policy. App-specific permissions and CSRF
protection remain each app's responsibility. Set application cookie names and paths
so they do not collide, and scope service workers to their app prefixes.

## 5. Gateway service

Deploy your oauth2-proxy digest and attach the gateway public domain, target port **4180**.
Set `PORT=4180` so Railway's healthcheck knows the listening port. Use
`railway/oauth2-proxy.json` or the equivalent `/ready` healthcheck and restart settings.
Railway's deployment healthcheck is not continuous monitoring.

Copy the gateway environment mapping from `docker-compose.yml` into Railway variables.
Replace Compose `${...}` expressions with actual values or Railway reference variables;
Railway does not interpret Compose syntax. In particular:

- Set the exact realm issuer and callback shown in Compose.
- Set the client secret from the gateway client created in Keycloak.
- Generate the cookie secret with `openssl rand -base64 32 | tr -- '+/' '-_'`.
- Set allowed email domains and `/gateway-users` explicitly.
- Use comma-separated upstream URLs from the table, verified against real services.
- Preserve secure, HttpOnly, host-only root-path cookies and the API-route rule.
- Leave cookie domains unset. Do not add skip-auth routes for `/ping`.
- Preserve header stripping and keep token/Basic Authorization forwarding disabled.

The sample cookie lifetime is eight hours, refreshed after four minutes; Keycloak
access tokens last five minutes with a 30-minute SSO idle limit and eight-hour maximum.
Verify actual refresh and group-removal behavior. Revocation is not necessarily immediate.

## 6. Production acceptance

Run with isolated test accounts and an external test database first:

- Login with PKCE, valid audience/groups, and return to the original URL for every app.
- Missing group/unverified email rejected; API calls without a session return 401.
- Assets, forms, redirects, query strings, uploads, and required WebSockets work.
- Bare-prefix and prefix-boundary routing is correct.
- Spoofed identity headers, bad state/nonce, and external return URLs are rejected.
- Sessions refresh and expire as intended; group removal takes effect within the documented window.
- Test gateway logout separately from Keycloak logout. Configure and test coordinated
  logout if required; gateway sign-out alone can allow immediate Keycloak SSO login.
- No direct public app access, database port exposure, or public management port.
- Verify edge forwarded-header handling. Enabling reverse-proxy mode assumes a trusted edge.
- Wrong DB certificate/hostname rejected; successful DB connection uses verified TLS.
- Keycloak restarts without losing realm state; database restore succeeds in isolation.
- Record actual Railway runtime restrictions and host compliance evidence.

Do not mark these checks passed solely because the CI build, smoke test, and scan succeed.

## 7. Operations

Monitor public availability and private readiness separately. Limit log retention and
avoid logging tokens, cookies, secrets, or full authentication callback queries.
Back up the database before Keycloak upgrades. Database schema changes may prevent a
simple image rollback; use the supported upgrade path and a tested restore plan.

Rotate client secrets in Keycloak and the gateway together. Rotating the gateway cookie
secret invalidates existing gateway sessions. Update deployment image digests explicitly
only after review; an upstream update PR does not deploy itself.
