# Despensa development roadmap

## Implemented baseline

| Stage | Delivered |
| --- | --- |
| V0.1 | Recipe manager and Despensa branding |
| V0.2 | Pantry inventory, batches, expiration, and stock filters |
| V0.3 | Deterministic availability, aliases, and compatible conversions |
| V0.4 | Multi-recipe shopping lists, actual purchases, and atomic inventory transfers |
| V0.5 | Live dashboard, Spanish interface, responsive navigation, and shared visual system |
| V0.6 preparation | Technical audit, publication documentation, demonstration screenshots, and submission draft |

The tasks below are future development opportunities. Their order is a planning suggestion rather than a delivery commitment.

## Future contribution areas

| Opportunity | Expected technical work | Verification criteria |
| --- | --- | --- |
| Weekly meal planning | Add meal-plan and scheduled-recipe models, date/serving endpoints, and a weekly view. Reuse shopping aggregation for selected meals. | Multiple scheduled meals share stock once and retain correct dates and servings after reload. |
| Inventory consumption tracking | Add a batch allocation and stock-movement ledger, explicit cooking confirmation, reversal rules, and transactional idempotency. Define FEFO allocation. | Repeated confirmations do not deduct twice, stock never becomes negative, and history explains each movement. |
| Nutrition information | Define per-ingredient nutrition records, units, source provenance, provider adapters or reviewed import, and per-serving aggregation. Review dataset terms. | Quantities normalize consistently and missing nutrition remains visibly unknown. |
| Multi-user household management | Add household memberships and ownership keys to domain tables, migrate existing data, scope every query, and provide invitation/member views. | Tests prove isolation between households and preserve existing single-user data during migration. |
| Authentication and authorization | Choose an identity/session approach, protect backend operations, define household roles, and add session/CSRF/security configuration as appropriate. | Unauthenticated requests and unauthorized cross-household operations are rejected in API tests. |
| Recipe import | Create bounded JSON/import schemas, format adapters, a preview-and-confirm flow, provenance fields, and duplicate handling. | Malformed imports fail without partial writes and existing recipes remain unchanged. |
| Advanced ingredient normalization | Introduce a reviewed alias catalog and editing UI, language-specific rules, and migration/versioning of matching keys. | Similar-but-distinct products remain separate and historical purchase records remain stable. |
| Shopping budget management | Add currencies, unit prices, estimated and actual costs, and Decimal totals. Define compatible-unit pricing and rounding. | Totals reconcile across batches and units without mixing currencies implicitly. |
| Improved inventory analytics | Build date-range queries, expiration/waste/consumption metrics, supporting indexes, and accessible charts based on stored events. | Displayed metrics trace back to actual records and handle empty periods explicitly. |
| Production deployment | Define frontend hosting and API reverse-proxy configuration, HTTPS, secrets management, persistent storage, backup/restore, monitoring, and deployment checks. Complete the access-control work before public operation. | A clean environment can start the application, migrate safely, restore a backup, and pass health and security checks. |
| Receipt scanning | Add an OCR/parser boundary, reviewed purchase drafts, error handling, and confirmation before creating purchase records. | Uncertain fields require review and repeated import cannot duplicate purchases. |

## Foundation and starter tasks

- Add frontend interaction tests for list editing, purchase confirmation, transfer conflicts, and mobile navigation.
- Add bounded pagination and indexed search while preserving current API behavior for existing callers.
- Improve error recovery and keyboard/screen-reader navigation with targeted browser checks.
- Extend deterministic alias fixtures and import validation tests.
- Clarify the project license and contribution terms with the confirmed rightsholder.

Keep contributions scoped, documented, and covered by meaningful regression tests. Planned functionality should remain labeled as future work until implemented and validated.
