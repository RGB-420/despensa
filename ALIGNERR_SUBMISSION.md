# Alignerr submission preparation

This is a factual draft for the Software Developer — Build Your Own Project submission form. The applicant must review the confirmation items before using it. Application acceptance or eligibility has not been established by this document.

## Project name

Despensa

## Repository URL

https://github.com/RGB-420/despensa

## Short project description

Despensa is a full-stack kitchen management application connecting recipes, pantry inventory, ingredient availability, and shopping. Users can compare recipes with usable stock, combine multiple recipes into a shopping list, record actual purchases, and explicitly transfer purchases into inventory. The interface is in Spanish and supports desktop and mobile layouts.

## Technology stack

- React, TypeScript, Vite, and plain CSS.
- Python, FastAPI, Pydantic, and SQLAlchemy.
- SQLite persistence with additive migrations.
- Pytest and FastAPI TestClient.

## Current implementation status

The implemented application is V0.5. V0.6 preparation covers the technical audit, documentation, screenshots, and publication workflow.

Implemented areas include recipe CRUD/search, pantry batches and expiration, deterministic availability, multi-recipe shopping calculations, manual shopping items, purchase states, atomic inventory transfer, a live dashboard, and responsive navigation.

The audit passed 101 backend tests, TypeScript checking, and the production build. Local browser checks used isolated demonstration data. The application runs locally. A hosted production application is future work.

## Architecture

The React client calls a FastAPI API through Vite's local proxy. SQLAlchemy stores recipes, inventory batches, shopping lists, and shopping items in SQLite.

Dedicated services reuse ingredient normalization and Decimal-based compatible-unit conversion. Multi-recipe shopping demand is aggregated before stock is deducted once. Purchase transfers acquire a SQLite write transaction, persist inventory and transfer status together, and prevent duplicate stock on retries.

The internal package remains backend/pantrylab. Architecture and endpoint contracts are documented in [ARCHITECTURE.md](ARCHITECTURE.md) and [API.md](API.md).

## Development roadmap

Potential contributions include weekly meal planning, consumption ledgers, nutrition, household support, authentication/authorization, recipe import, reviewed aliases, shopping budgets, inventory analytics, receipt review, and production deployment.

[ROADMAP.md](ROADMAP.md) describes the technical work and verification criteria for each area.

## Ownership information requiring applicant confirmation

- [ ] Confirm the applicant identity and the name to use in the form.
- [ ] Confirm the rights or permissions needed to publish and submit the code and documentation.
- [ ] Confirm any employer, client, collaborator, or third-party restrictions.
- [ ] Confirm contributor identities and required attribution, if any.
- [ ] Review the program's current rules and any required disclosure of development assistance.

Implementation and documentation used AI coding assistance through Codex. The applicant should confirm the required disclosure and eligibility wording under the program's current terms.

Git repository creation, commit history, and an account's ability to publish do not by themselves establish legal ownership. No personal identity, sole-ownership claim, or prior contributor details are supplied here.

## License information requiring applicant confirmation

No project LICENSE file is present. Project licensing remains undecided. Third-party dependencies retain their own license terms.

- [ ] Confirm the authorized rightsholder and project license decision.
- [ ] Confirm the copyright attribution before adding any license text.
- [ ] Confirm any licensing requirement in the program's submission terms.

MIT is a suggested permissive option, pending authorization. It permits broad reuse subject to notice retention and includes a warranty disclaimer. [MIT reference](https://choosealicense.com/licenses/mit/)

## Collaboration possibilities

Contributors could work on targeted frontend tests, pagination, import validation, meal-planning APIs, stock movement history, household isolation, or deployment tooling. Changes should preserve existing data, deterministic matching, and transactional inventory behavior.

Contribution licensing terms should be agreed with the confirmed rightsholder. The applicant must supply any requested availability or time commitment.

## Known limitations

- Local single-user operation without authentication or household isolation.
- In-memory navigation state and lists without pagination.
- Aliases maintained in code, with explicit measurement dimensions.
- Independent shopping plans rather than global stock reservation.
- Inventory corrections after transfer require explicit adjustments.
- No production deployment is claimed.

## Evidence and submission status

- [README.md](README.md) provides setup, features, and screenshots.
- [docs/AUDIT.md](docs/AUDIT.md) records the publication audit.
- Screenshots contain only synthetic demonstration records.
- The Alignerr form has not been submitted.
