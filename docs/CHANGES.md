# Django Payment Simulator: essential cleanup record

Date: 20 October 2026. Baseline: the working project inside the supplied
`265842_webapps2026-1 (1).zip`. Work was performed on a separate copy; the archive
and untouched extraction remain available. Nothing was pushed or deployed.

## Scope, including the only version upgrade

The original Django/SQLite/template architecture, schema, currencies, starting
balance, fixed exchange rates and HTTP conversion-service flow are retained.
There is no new framework, payment gateway, database engine, auth model, frontend
redesign or live exchange-rate service.

The explicit dependency change is **`Django>=6.0.4` to `Django>=6.0.9,<6.1`**.
This raises the same-6.0-line patch floor and prevents an implicit 6.1 upgrade.
It was announced before applying the final version floor. Django's
[6.0.9 release notes](https://docs.djangoproject.com/en/6.0/releases/6.0.9/) describe
the security fixes in that release. The archive did not lock installed versions
for its other dependencies, so their resolved test versions are recorded below;
they are not represented as measured upgrades from known original versions.

For scale: existing Python application/configuration files changed by 158 added
and 214 removed lines, excluding tests and documentation. The net reduction mostly
reflects compacting settings/removing the automatic credential migration. The
application was not expanded into a new payment architecture. Exact redacted diffs
and per-file SHA-256 manifests accompany the delivered ZIP in the outputs folder.

## Every application/configuration change

| File | Change and reason |
| --- | --- |
| `webapps2026/settings.py` | Removed the embedded signing key. `DJANGO_SECRET_KEY` is required from the process environment; missing configuration fails with a clear message. `DJANGO_DEBUG` is explicit and off by default. Allowed hosts and internal API base/optional CA bundle are configurable. Explicit debug mode permits loopback HTTP development; non-debug mode retains secure cookies, HTTPS redirect, HSTS and frame denial. SQLite now uses IMMEDIATE transactions with a 20-second wait. The existing app list, middleware, template directory/processors, URLs, database filename, password validators, GBP 1,000 baseline, currencies, complete rate matrix, crispy configuration and locale are retained. The file was compacted while removing the hardcoded secret; this is configuration editing, not a replacement of application logic. |
| `payapp/migrations/0002_create_initial_admin.py` | Kept the migration name/dependencies but changed its operations to an empty list. Fresh migrations no longer create a public default administrator/password. No existing user's account is silently deleted or reset. |
| `payapp/services.py` | Removed global insecure-TLS warning suppression and `verify=False`. Requests now verify normally or use a locally supplied CA bundle. The HTTP conversion call, five-second timeout, URL shape, same-currency shortcut and initial-currency helper remain. Plain HTTP is accepted only to loopback in explicit debug mode. Network/HTTP/JSON/Decimal-response failures become a controlled ValueError; nonfinite, negative and account-range-exceeding amounts are rejected instead of propagating bad values/500s. Added the shared Decimal maximum matching the existing 12-digit/two-decimal account field. |
| `payapp/api.py` | Preserved the GET-only DRF endpoint and rate table/Decimal rounding. Added finite/nonnegative/range checks and catches quantisation failures within the validation block, so NaN, Infinity and enormous exponents return 400 instead of crashing or returning invalid amounts. Converted values must also fit the same range. |
| `payapp/views.py` | Dashboard creates a missing zero-balance Account for a CLI-created superuser, preventing the fresh-admin profile error without awarding new funds. Direct payments and request fulfilment reject recipient-balance overflow. Request responses require POST and run their pending-request/target lookup inside a transaction, using the existing ownership/status filter and a row-lock queryset where supported. Admin registration wraps user/profile/staff promotion together and displays controlled conversion errors. Existing routes, templates, balance arithmetic, Payment creation, notifications/history and staff checks otherwise remain. |
| `register/forms.py` | `RegisterForm.save()` now has its own atomic block, so both ordinary and administrator registration roll back User creation if account/conversion creation fails. Updated its transaction comment. Existing fields, duplicate-email check, password validation and initial-balance calculation are preserved. |
| `register/views.py` | Ordinary registration catches the controlled conversion ValueError and displays a form error; it does not leave an orphaned User or show a server traceback. Logout now requires a CSRF-protected POST. Login/authentication and redirect logic remain. |
| `templates/register/navbar.html` | Replaced the logout hyperlink with a POST form containing the existing Django CSRF token. No other template or styling redesign. |
| `requirements.txt` | Only the Django requirement line changed as specified above; other package entries remain from the submission. |
| `payapp/tests.py` | Replaced an empty file with 16 focused Django regression/integration tests. Uses Django's own test runner, unittest mocks and a real local HTTP conversion test; no new application/test dependency. |

### Why the transaction changes are necessary

The original request object was fetched before `transaction.atomic()`. The code
also used `select_for_update()` on SQLite, where it does not acquire row locks.
The one-to-one fulfilled-request field already helped prevent duplicate ledger rows,
but did not make stale reads/errors a clean request-handling strategy.

The pending lookup now occurs inside the write transaction, and IMMEDIATE mode
reserves the SQLite writer before balances/state are read. The existing debit,
credit, Payment insertion and request-status update remain transactional. No extra
ledger abstraction or payment-processing subsystem was introduced. Reference:
[Django's SQLite transaction notes](https://docs.djangoproject.com/en/6.0/ref/databases/#transactions-behavior).

The tradeoff is serialised writers, and the existing HTTP conversion call still
occurs during the financial transaction. The README explicitly warns against a
single-threaded development server and against treating this design as high-throughput finance.

## Additions for publication

- `.gitignore`: excludes databases/sidecars, private/local certificates, environment
  files, virtual environments, caches, IDE files, logs and OS metadata.
- `.env.example`: variable names and dummy/reference values only. It explicitly
  says that automatic dotenv loading is not implemented.
- `README.md`: overview, stack, exact setup, generated-key instructions, migration/
  administrator creation, settings, API, tests, architecture and limits.
- `docs/PROJECT-REFRESHER.md`: background, model relationships, payment/request
  flows, security boundaries, SQLite issue, interview notes and optional future work.
- `docs/CHANGES.md`: this complete record.
- `docs/dashboard.png`: fresh Chrome screenshot using synthetic `example.test`
  accounts in a disposable fixture. No real user database is shown.

## Excluded from the upload package

- `webapps.db`: the supplied 172 KB database contained one User and one Account,
  including password-hash/account state. No transaction/request/session rows were
  present in the reviewed database. Counts were inspected read-only; private rows
  were not copied into the publication package.
- `webapps.key`: the supplied private TLS key. Do not reuse it if previously exposed.
- `webapps.crt`: the corresponding local certificate. New deployments should use
  their own trusted certificate and never commit the private key.
- The submission PDF located above the application directory in the ZIP: includes
  assessment screenshots/context and is not necessary to run the project.
- Test-generated database/cache files and the isolated dependency virtual environment.

The original files were not destroyed. Fresh `migrate` creates the schema without
copying the supplied users or creating a shared administrator. A generated empty
database/cache created by diagnostic commands was removed from the prepared tree
before packaging; no original user database was deleted.

## What is unchanged

The `Account`, `Payment` and `PaymentRequest` model definitions, initial schema
migrations, URL configuration, app configuration, permission decorator, manage.py,
WSGI/ASGI entry points, empty ancillary admin/tests modules, and every template
except the logout navbar remain byte-for-byte as supplied. This includes the
dashboard, payment/request forms, history, notifications and three staff templates.
No renaming of the internal `webapps2026` prefix or database filename occurred.

## Verification

- `manage.py check`: passes.
- `manage.py makemigrations --check --dry-run`: no changes detected.
- `manage.py test`: **16 tests pass**, covering payment balances/ledger rows,
  insufficient funds, recipient overflow, self/invalid transfers, ownership,
  request replay/rejection, staff/anonymous access, POST/CSRF rules, conversion
  validation, TLS/network failure handling, registration rollback/success, no
  automatic admin and the fresh CLI-superuser profile.
- A LiveServer test calls the actual HTTP conversion endpoint through Requests.
- A separate disposable, file-backed SQLite deployment passed two simultaneous
  accepts of one request (one success/one 404/one payment) and two simultaneous
  spends competing for the same remaining balance (one success, no overdraft).
  Those checks exercised real HTTP currency calls, not only mocked calculations.
- Chrome login, dashboard, transaction history and POST logout passed with no
  JavaScript page errors. The screenshot was visually inspected.
- Non-debug `manage.py check --deploy` passes with the generated test secret. This
  is a configuration check, not evidence that production hosting/TLS was deployed.
- Source/ZIP checks verify that the original signing-secret value, private-key
  contents, database, certificate, caches and environment secrets are not packaged.

Test runtime: Python 3.12.14. Direct dependency versions resolved from the existing
list: Django 6.0.9; django-crispy-forms 2.7; crispy-bootstrap5 2026.9;
django-extensions 4.1; Werkzeug 3.1.9; pyOpenSSL 26.4.0;
djangorestframework 3.18.3; requests 2.34.2; urllib3 2.8.0.
Bootstrap's template CDN remains 5.3.0. Other packages were not pinned by the
original archive, and this cleanup does not claim to know its previous install set.

## Security and upload handoff

Generate a new signing secret locally. If the original secret/private key was used
on an active deployment, replace it there; a clean new ZIP cannot revoke an exposed
key. An already-applied migration is not rerun automatically, so an existing
database may still contain the old default administrator: reset/remove that account
deliberately after checking its data, rather than assuming this source edit removed it.

Deleting a current file does not erase earlier Git commits. If these assets were
already uploaded, review history and rotate any reused credentials before deciding
whether history removal is needed. No history rewrite or remote operation was performed.

SQLite throughput, form-level email uniqueness rather than a new database-level
email constraint, public fixed-rate conversion, CDN availability, no application-
specific rate limiting and the lack of real financial controls remain documented
limitations. New features/upgrades are your decision, not hidden in this pass.
