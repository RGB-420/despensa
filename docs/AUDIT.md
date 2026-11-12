# V0.6 publication audit

Audit date is 2026-11-12. The application baseline is V0.5 at commit d60934bc761ad111587015dd4188308904c28178. This preparation adds documentation and demonstration screenshots.

## Git and code review

The working tree was clean at audit start. The configured origin is https://github.com/RGB-420/despensa.git. Its public visibility and main branch were checked. Fetch confirmed that the remote main was an ancestor of the local branch, permitting a normal fast-forward push.

The V0.4 shopping and V0.5 dashboard/UI commits were reviewed. Existing history is preserved. No application feature or schema change was needed during this audit.

## Validation results

| Check | Result |
| --- | --- |
| Full backend suite | 101 passed |
| Availability tests | 40 passed |
| Dashboard tests | 4 passed |
| Inventory tests | 18 passed |
| Recipe tests | 15 passed |
| Shopping tests | 24 passed |
| TypeScript validation | Passed |
| Frontend production build | Passed |
| Repeatable schema migration | Passed twice on a read-only backup of the local database |
| Existing migration and persistence regressions | Passed in the backend suite |
| Live demonstration API workflow | Passed with isolated synthetic records |
| Browser checks | Dashboard, pantry, availability, shopping/purchase states, and mobile layout |

The environment used Python 3.12.10, Node.js 22.23.2, and npm 10.9.8. Tests used fresh temporary SQLite files. The production build used the existing locked frontend dependencies.

The suite emitted one non-blocking Starlette warning about the deprecated httpx TestClient integration. Dependency changes were outside this documentation-focused audit.

## Data and migration safety

The local database was opened read-only and backed up into an ignored test directory. Migration was applied twice to that copy. Inventory, recipes, shopping items, and shopping lists retained identical rows, with schema version 4.

The suite also verifies migration from previous schemas, persistence across application restarts, concurrent transfer idempotency, and atomic rollback after an injected failure.

## Repository and history inspection

The baseline had six reachable commits, 47 tracked paths, and 113 reachable blob objects. Reachable history and commit data were scanned for known credential formats, private keys, credential-bearing URLs, and credential-like literal assignments. No matches were found.

Historical paths were checked for environment files, databases, private keys, virtual environments, dependencies, logs, caches, temporary files, and generated builds. No prohibited historical paths were found. Nine representative .gitignore cases passed.

The preparation commit is separately checked before publication, including its staged documentation and image paths. Pattern scans are evidence within this review's scope and are not a guarantee that every possible secret format can be identified.

## Demonstration screenshots

The five JPEGs under screenshots/ were captured from a freshly created isolated database populated with synthetic kitchen records through the API.

| File | Content |
| --- | --- |
| screenshots/dashboard.jpg | Dashboard with actual counts from the demonstration dataset |
| screenshots/pantry.jpg | Batches, expiration, zero stock, and minimum-stock indicators |
| screenshots/availability.jpg | Ready, almost-ready, and missing-ingredient states |
| screenshots/shopping.jpg | Purchase progress and purchased/transferred distinction |
| screenshots/mobile.jpg | Compact mobile dashboard |

Desktop capture used a 1440 CSS-pixel viewport. Mobile behavior was checked at 390 CSS pixels without horizontal overflow. Image files contain application content without browser address bars or personal/local development records. JPEG signatures and dimensions were verified.

## License review

No project license file was found. MIT is documented as a recommendation requiring authorization, and no license file was added. Dependency license metadata remains distinct from project licensing.

## Publication verification

Publication uses the configured origin and a normal push of main. The verification procedure checks the remote commit, anonymous public access, published paths and blob hashes, README image availability, and rendered documentation. The final published revision is available in the repository's main-branch history.

## Remaining applicant actions

Confirm ownership/attribution information, choose and authorize a project license if desired, and review the Alignerr draft and current program requirements. Submission of the form remains an applicant action.
