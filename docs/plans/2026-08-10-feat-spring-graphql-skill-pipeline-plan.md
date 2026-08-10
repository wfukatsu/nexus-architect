---
title: "feat: Add Spring for GraphQL design and implementation skills"
type: feat
status: completed
date: 2026-08-10
---

# Spring for GraphQL 設計・実装スキル追加計画

## 概要

GraphQL を採用すべきかを API 特性、クライアント要求、運用要件、バックエンド DB、ScalarDB の版・Edition・トランザクション方式から判断し、採用時は Spring for GraphQL を公開境界として設計・実装・検証できる一連のスキルとルールを追加する。

対象は「SDL を出力するだけ」ではなく、次の判断と成果物を一つの契約チェーンにすることである。

1. REST、GraphQL、併用のどれを採用するか
2. Spring MVC、WebFlux、WebSocket、RSocket のどれを使うか
3. PostgreSQL 等の通常 DB、ScalarDB Core/Cluster、ScalarDB SQL/GraphQL interface のどれをどの境界で使うか
4. SDL、resolver、application service、repository、transaction の対応
5. 認証・フィールド／オブジェクト／テナント認可、クエリ負荷制御、N+1 防止
6. 契約テスト、API セキュリティレビュー、設計↕コード検証、8段階品質ゲート

## 背景と現状のギャップ

既存の `/architect:design-api` は REST、GraphQL、gRPC、AsyncAPI を対象にし、`reports/03_design/api-specifications/graphql/` を出力先として宣言している。しかし、後続は次の点で REST/OpenAPI に偏っている。

- `/architect:generate-api-code` は OpenAPI から `@RestController`、DTO、Problem Details handler を生成する。
- `rules/api-contract-fidelity.md` の join key と contract map は HTTP method/path/status code を中心に定義されている。
- `/architect:generate-contract-tests` の既定スタックは OpenAPI request validator と MockMvc である。
- `/architect:verify-implementation` の inventory と drift 判定は HTTP route を中心にしている。
- `rules/api-security-checks.md` は汎用 API セキュリティを扱うが、GraphQL 固有の field authorization、alias/batch/depth/complexity、introspection、subscription、DataLoader cache partitioning を明示的な検査項目にしていない。
- ScalarDB の GraphQL interface は Enterprise Premium の機能である一方、「ScalarDB が提供する GraphQL surface」と「Spring for GraphQL で構築する application API」が区別されていない。

このため、新しい実装スキルだけを追加すると、採用判断、契約、レビュー、検証のどこかが REST 前提のまま残る。

## 基本方針

### 1. GraphQL は要件から選択し、DB 製品から自動選択しない

GraphQL の採用を推奨するのは、次の条件が複数当てはまる場合とする。

- 画面／BFF ごとに必要なレスポンス形状が大きく異なる。
- 複数リソースを一度に取得することで under-fetching を減らせる。
- スキーマ進化を additive に管理できる組織・クライアント関係がある。
- field-level authorization、query cost、N+1、schema governance を運用できる。
- HTTP キャッシュよりクライアント主導の選択性が重要である。

次の場合は REST、gRPC、AsyncAPI、または併用を優先する。

- 単純な command API、ファイル転送、Webhook、厳格な HTTP semantics が中心。
- CDN／HTTP cache、URL 単位の認可・レート制限が主要要件。
- 公開 API で固定された業務操作と明示的な retry semantics が重要。
- field-level authorization や query complexity の運用能力がない。
- Saga/TCC の orchestration endpoint を自由な query surface と混同する恐れがある。

判定は二択ではなく `REST`、`GraphQL`、`hybrid`、`gRPC/AsyncAPI` の decision record とし、surface 単位で選択する。

### 2. ScalarDB 採用と GraphQL 採用を直結させない

次の2つを別の選択肢として扱う。

- **Spring for GraphQL application API**: Spring Security、Application Service、ScalarDB repository を経由する公開／BFF surface。
- **ScalarDB の GraphQL interface**: pinned release と contracted Edition で利用可否を確認する製品機能。

デフォルト方針は、外部または業務 API では Spring for GraphQL を公開境界とし、ScalarDB の GraphQL interface を直接公開しないこととする。直接利用は、Edition、機能、認可、監査、負荷制御、ネットワーク境界を pinned OKF bundle で確認し、内部／管理用途として明示的に承認された場合だけ許容する。

通常 DB と ScalarDB のいずれでも Controller は Application Service にのみ依存させる。ScalarDB の同期 API を使う場合は Spring MVC を既定とし、WebFlux は subscription や既存 reactive stack 等の根拠があり、blocking call を bounded executor または virtual thread へ隔離する設計がある場合だけ選択する。

### 3. GraphQL にも検証可能な contract と join key を持たせる

GraphQL の contract は SDL と operation contract table の組である。REST の `operationId` に相当する安定 join key を次の形で定義する。

```text
<parentType>.<fieldName>
例: Query.customer, Mutation.createCustomer, Customer.orders
```

各 field coordinate を exactly one resolver method に対応させ、SDL → resolver → application service → transaction → test → finding を contract map で追跡する。client document の `operationName` は実行時観測用であり、schema field の実装 join key とは区別する。

### 4. GraphQL のエラー表現を既存 Problem Type registry に統合する

GraphQL execution error は `errors[].extensions.type` に既存 problem type URI を載せ、GraphQL over HTTP の transport status と field execution error を区別する。新しい ad-hoc error envelope は作らない。

`UnknownTransactionStatusException` は GraphQL でも専用分岐を持ち、idempotency-key protection の有無に応じて retry/reconcile guidance を変える。複数 top-level Mutation が一つの HTTP request に含まれても、request 全体を暗黙の単一 ScalarDB transaction とみなさない。

## 提案するスキル構成

### A. `/architect:design-api` を API surface 選択の入口として拡張

新しい独立選択スキルを増やすより、既存の API 設計入口で surface ごとに方式を決め、その後の conditional phase を起動する方が既存利用者との互換性が高い。

変更内容:

- REST／GraphQL／hybrid の decision matrix を追加する。
- DB／data access、transaction、client variability、cache、security、operations を評価軸にする。
- `reports/03_design/api-style-decisions.md` を新規出力する。
- GraphQL 選択時は、対象 bounded context、consumer、Query/Mutation/Subscription、transport、MVC/WebFlux、DB access path、採用しない surface と理由を記録する。
- GraphQL SDL の詳細生成を後続 `/architect:design-graphql` に移し、`design-api` は共通 operation inventory、problem type registry、gateway policy を保持する。
- `api_style_graphql`、`api_style_rest`、`api_style_hybrid` の pipeline condition を設定する。

### B. `/architect:design-graphql` を追加

GraphQL が選択された surface に対して、Spring for GraphQL で実装可能な詳細設計を作る。

主な入力:

- `reports/03_design/api-style-decisions.md`
- `reports/03_design/target-architecture.md`
- `reports/03_design/scalardb-transaction.md` または `data-layer-design.md`
- `reports/01_analysis/actors-roles-permissions.md`
- product の logical API、NFR、SLA（存在する場合）
- ScalarDB 利用時の product/version/edition と pinned OKF concepts

主な出力:

- `reports/03_design/api-specifications/graphql/<service>.graphqls`
- `reports/03_design/api-specifications/graphql/resolver-contracts.md`
- `reports/03_design/api-specifications/graphql/authorization-matrix.md`
- `reports/03_design/api-specifications/graphql/batch-loading-plan.md`
- `reports/03_design/api-specifications/graphql/query-governance.md`
- `reports/03_design/api-specifications/graphql/transport-design.md`

設計項目:

- schema-first SDL、nullability、input/output type 分離、custom scalar、deprecation policy。
- Query／Mutation／Subscription と field coordinate ごとの resolver、application service、transaction placement。
- tenant、principal、scope/role、ownership predicate、field-level PII policy。
- `@BatchMapping`／DataLoader の key、batch query、cache scope、tenant/principal partitioning、maximum batch size。
- cursor pagination、stable sort、signed cursor、maximum page size。
- depth、complexity、alias、batch operation、document size、timeout、rate limit、persisted/allowlisted query の budgets。
- GraphiQL、introspection、schema printer、CORS、CSWSH、WebSocket authentication、subscription connection limits。
- operationName、normalized query hash、executionId、tenant/principal を使う observability と secret/PII masking。
- MVC/WebFlux の選択と blocking ScalarDB call の扱い。

### C. `/architect:generate-graphql-code` を追加

`design-graphql` と `design-implementation` の成果物から Spring Boot application API layer を生成する。

生成対象:

- `src/main/resources/graphql/**/*.graphqls`
- `@Controller` と `@QueryMapping`、`@MutationMapping`、`@SubscriptionMapping`、`@SchemaMapping`、`@BatchMapping`
- input records/classes、output projection DTO、explicit mapper
- `WebGraphQlInterceptor` による認証済み tenant context 伝播
- method security と object/row/field authorization の enforcement point
- `DataFetcherExceptionResolver` または `@GraphQlExceptionHandler`
- GraphQL Java Instrumentation／Spring properties による query budgets
- Micrometer Observation customization
- GraphQL contract map

package ownership は既存 generator と衝突させず、`…/api/graphql/` を本スキル、`…/application/` の interface を API generator、実装と `…/domain/`／`…/infrastructure/` を ScalarDB/data-layer generator の所有とする。

`generate-api-code` と `generate-graphql-code` は `api-style-decisions.md` に従って条件実行し、hybrid では共有 application service を利用するが、REST DTO と GraphQL type を同一クラスへ安易に統合しない。

### D. 既存のテスト・レビュー・検証スキルを GraphQL 対応

新しいテスト／レビュー skill を乱立させず、既存の横断品質 skill を拡張する。

- `generate-contract-tests`: `GraphQlTester` を既定にし、schema inspection、field coordinate ↔ resolver coverage、input validation、errors extensions、authorization、N+1 query count、complexity/depth rejection、tenant isolation を生成する。HTTP/WebSocket/RSocket は transport design に応じて tester を選ぶ。
- `review-api-security`: GraphQL 固有チェックを追加し、design/code の両モードで field authorization、BOLA、introspection、GraphiQL、CSWSH、subscription、alias/batching、DataLoader cache leakage、query cost、error leakage を評価する。
- `verify-implementation`: Spring GraphQL runtime wiring/controller annotations から resolver inventory を導出し、SDL と contract map の自己申告を独立検証する。
- `generate-test-specs`: REST と GraphQL で contract test stack を分岐する。
- `implement-backlog`: GraphQL item では `generate-graphql-code` の制約と contract-first change protocol を適用する。
- `generate-docs`: SDL location、query examples、security policy、limits、deprecation を文書化する。

## 提案するルール構成

### 1. `rules/api-style-selection.md`

REST／GraphQL／hybrid／gRPC／AsyncAPI の選択基準、DB と API style を独立して決める原則、Spring MVC／WebFlux の選択、ScalarDB GraphQL interface 直接公開の禁止既定を定義する。

### 2. `rules/graphql-contract-fidelity.md`

SDL を contract とする規則、field coordinate join key、resolver 1:1、nullability、input/output 分離、schema evolution、contract map schema、drift protocol、GraphQL error mapping を定義する。共通事項は `api-contract-fidelity.md` を参照し、重複させない。

### 3. `rules/graphql-security-checks.md`

GraphQL 固有の設計・コード検査を定義する。最低限、以下を blocker/critical/major に分類する。

- URL 認証だけで field/operation/object authorization がない。
- tenant ID を未検証 header から採用する。
- DataLoader key/cache が tenant/principal を跨ぐ。
- page size、depth、complexity、alias、batch operation、timeout の上限がない。
- Mutation の idempotency と `UnknownTransactionStatusException` の分岐がない。
- introspection／GraphiQL／schema printer が本番で意図せず有効。
- WebSocket origin/authentication/reauthentication と connection limit がない。
- raw query／variables／PII をログへ記録する。
- `@PreAuthorize` があるが method security が無効、または repository query に tenant predicate がない。

既存 `rules/api-error-standard.md`、`api-security-checks.md`、`ai-code-quality-gate.md`、`dependency-versions.md` は共通のまま相互参照を追加する。

## Pipeline とメタデータの変更

### Dependency graph

`skills/common/skill-dependencies.yaml` に次を追加する。

```yaml
design-graphql:
  category: design
  depends_on: [design-api]
  conditions: [api_style_graphql]
  outputs:
    - reports/03_design/api-specifications/graphql/

generate-graphql-code:
  category: implementation
  depends_on: [design-implementation, design-graphql]
  conditions: [api_style_graphql]
  outputs:
    - reports/06_implementation/api-contract-map.json
```

hybrid は condition evaluator が `api_style_graphql` と `api_style_rest` の双方を true として扱う。既存 phase map を再登録せず、shared progress file へ additive に stamp する。

レビュー依存は GraphQL 選択時に `design-graphql` 完了後となるよう解決する。generator 群が現在 manifest 外で手動実行される設計なら、その状態を先に確認し、design phase のみ manifest へ追加して implementation command chain は README／skill relationships で管理する。既存 orchestration semantics を一度に変更しない。

### Claude/Codex compatibility

- `skills/design-graphql/SKILL.md` と `skills/generate-graphql-code/SKILL.md` を正規配置する。
- architect plugin の command discovery／metadata を既存方式に従って更新する。
- `CLAUDE.md`、`README.md`、`docs/skill-reference.md`、`docs/skill-reference_ja.md`、`AGENTS.md` の model recommendation と command list を更新する。
- Claude 固有 frontmatter と Codex mapping を保持する。
- skill-creator の一般的な `agents/openai.yaml` は、この repository の plugin skill discovery が利用している場合だけ追加し、既存 skill と異なる独自形式を持ち込まない。

## Contract map の拡張案

既存 JSON schema を壊さず、operation entry に `protocol` と protocol-specific binding を追加する。

```json
{
  "protocol": "graphql",
  "operation_id": "Mutation.createCustomer",
  "spec_file": "reports/03_design/api-specifications/graphql/customer.graphqls",
  "parent_type": "Mutation",
  "field": "createCustomer",
  "handler": "com.example.api.graphql.CustomerController#createCustomer",
  "input_type": "CreateCustomerInput",
  "output_type": "Customer",
  "problem_types": ["validation-failed", "transaction-status-unknown"],
  "authorization": "scope:customer.write + tenant + ownership",
  "transaction": "TX-004",
  "traces_to": ["FR-012"]
}
```

REST entry は既存 fields を維持する。consumer は `protocol` で分岐し、未指定の旧 map は `rest` と解釈する migration rule を設ける。

## バージョンと知識ソースの扱い

- Spring Boot BOM を第一の version authority とし、通常は `spring-graphql` を直接 pin しない。
- 新規生成時は対象 Spring Boot release、Java baseline、Spring GraphQL managed version、GraphQL Java transitive version の互換性を公式 BOM／release metadata から解決する。
- Maven pin、Boot plugin、container tag を書く前に `rules/dependency-versions.md` に従い registry lookup と `work/version-decisions.json` を更新する。
- Spring for GraphQL 2.0.4、1.4.6、1.3.7、1.2.9 という安定版一覧は 2026-08-10 時点の公式 reference で確認できるが、SKILL.md に current version を固定値として埋め込まない。
- ScalarDB の設計・実装判断は必ず OKF bundle で product/version/edition を先に pin し、ScalarDB GraphQL interface の可用性、security、configuration をその release の docs だけで判断する。
- 重要な Spring GraphQL security release note は実装時に公式 GitHub Releases／advisory を再確認し、skill 本文には脆弱性番号の固定一覧ではなく「生成前に対象 line の security note を検査する手順」を置く。

## 実装フェーズ

### Phase 1: Decision model と共通 contract の整備

- `api-style-selection.md` を追加する。
- `design-api` に decision matrix と `api-style-decisions.md` を追加する。
- GraphQL field coordinate と contract map extension を `graphql-contract-fidelity.md` に定義する。
- `api-contract-fidelity.md` と `api-error-standard.md` に protocol routing を追加する。
- pipeline condition と progress handling の unit test を先に追加する。

完了条件:

- 同じ要件例に対して REST／GraphQL／hybrid の判定根拠が再現可能である。
- DB が ScalarDB であることだけを理由に GraphQL が選ばれない。
- ScalarDB native GraphQL と Spring application GraphQL が明確に区別される。

### Phase 2: GraphQL design skill

- skill-creator の手順に従い `design-graphql` を作成する。
- SDL、resolver contract、authorization matrix、batch plan、query governance、transport design の templates/references を必要最小限で追加する。
- `design-api`、`design-implementation`、review skills との入出力を接続する。
- sample requirements から成果物を生成する forward test を行う。

完了条件:

- 全 SDL field coordinate に resolver、authorization、transaction、N+1 strategy、limits が結び付く。
- unknown は permissive default や `TBD` で黙らせず `OQ-` workflow に入る。
- ScalarDB decisions は pinned OKF sources を記録する。

### Phase 3: Spring code generation skill

- `generate-graphql-code` を追加する。
- Spring MVC を既定とし、WebFlux／subscription は design input で条件生成する。
- controller、DTO、mapper、context interceptor、exception resolver、instrumentation、observation、contract map を生成する。
- existing package ownership と generator handoff をテストする。
- version lookup と confirmation flow を接続する。

完了条件:

- controller が ScalarDB type／repository を直接参照しない。
- every field coordinate が exactly one handler を持ち、extra resolver がない。
- tenant、authorization、transaction、error policy が design と一致する。
- hybrid generation で REST／GraphQL DTO と handlers が衝突しない。

### Phase 4: Contract tests、security review、verification

- `generate-contract-tests` に GraphQlTester stack を追加する。
- `graphql-security-checks.md` と `review-api-security` の checks/findings を接続する。
- `verify-implementation` に resolver inventory、SDL drift、runtime enforcement の検証を追加する。
- `ai-code-quality-gate` の contract/API security/design-code conformance stages が GraphQL artifacts を evidence として扱えるようにする。

完了条件:

- schema、resolver、authorization、tenant isolation、N+1、query budgets、errors、subscription の各テストに実行証拠が残る。
- REST-only project では既存 gate result が変わらない。
- GraphQL の FAIL は human review handoff を block する。

### Phase 5: Documentation、compatibility、end-to-end validation

- command list、model table、skill references、examples を更新する。
- Claude plugin と Codex の双方で新 skill が発見・実行できることを確認する。
- REST-only、GraphQL + PostgreSQL、GraphQL + ScalarDB、hybrid の4 fixture で pipeline を検証する。
- sample generated Markdown／Mermaid は hook validation を実行する。
- skill folders は quick validation または repository equivalent、YAML manifest は existing pipeline tests で検証する。

## テストシナリオ

### Selection tests

1. 多画面 BFF、read-heavy、複雑な projection、PostgreSQL → GraphQL + Spring MVC。
2. 明示的 command、HTTP cache、public API → REST。
3. flexible reads + strict commands → Query は GraphQL、Mutation command は REST の hybrid。
4. ScalarDB 採用のみで client variability がない → GraphQL を自動採用しない。
5. ScalarDB Enterprise Premium だが外部 API → native GraphQL 直接公開ではなく Spring facade を既定にする。

### Design tests

1. `Customer.orders` に batch plan がなく、N+1 risk finding になる。
2. tenant header と JWT claim の照合が未定なら OQ を発行する。
3. field-level PII authorization が authorization matrix に現れる。
4. multiple top-level mutations が request-wide transaction と誤記されない。
5. blocking ScalarDB API + WebFlux が executor plan なしなら blocker になる。

### Generated code tests

1. SDL input constraint が Java validation へ写像される。
2. `Query.customer`／`Mutation.createCustomer`／`Customer.orders` が1:1で handler に bind される。
3. DataLoader cache key が tenant を含み、cross-tenant batch を拒否する。
4. `UnknownTransactionStatusException` の GraphQL error extensions と retry guidance が idempotency policy に一致する。
5. GraphiQL/introspection/schema printer の production profile が policy に一致する。

### Security tests

未認証、scope 不足、他 tenant、owner、admin、nested sensitive field、alias explosion、deep query、high-cost query、oversized page、batch flood、invalid WebSocket origin、subscription reconnect を最低限含める。

## System-wide impact

### Interaction graph

```text
requirements / product API design
  -> design-api (surface decision)
  -> design-graphql (SDL + resolver/security/performance contract)
  -> design-implementation
  -> generate-graphql-code + domain/data generator
  -> generate-contract-tests
  -> review-api-security
  -> verify-implementation --gate
  -> implement-backlog / review handoff
```

### Error propagation

ScalarDB／repository exception → domain exception → application service retry/rollback policy → GraphQL exception resolver → `errors[].extensions.type`。transport-level authentication、parse、validation、execution error を区別し、内部 exception message は露出させない。

### State lifecycle risks

- 複数 top-level Mutation は直列でも同一 transaction ではない。
- idempotency record と business write が別 transaction になると重複を防げない。
- unknown commit status の blanket retry は二重更新を起こす。
- DataLoader cache の tenant leakage は request 内外の情報漏えいになる。
- subscription は長寿命 connection の auth expiry と resource leak を生む。

### API surface parity

hybrid では同じ business operation の REST と GraphQL が authorization、transaction、error type、idempotency で一致する必要がある。contract map の `traces_to` と `transaction` を parity check の join key にする。

## リスクと緩和策

| リスク | 緩和策 |
|---|---|
| 既存 REST 契約ルールを GraphQL へ無理に流用する | 共通 rule と protocol-specific rule を分離し、旧 REST map の後方互換をテストする |
| skill が巨大化する | SKILL.md は workflow に限定し、Spring patterns、security checks、contract schema は直接参照可能な rule/reference に分ける |
| Spring／GraphQL Java API が release line で変わる | Boot BOM と公式 docs を実行時に解決し、固定 version／class name を rule に埋め込まない |
| ScalarDB native GraphQL と Spring facade の混同 | `access_surface` と `data_access` を decision artifact の別項目にする |
| GraphQL の自由度が DB 負荷へ直結する | batch plan と query governance を design acceptance criteria にする |
| annotation が存在するだけで安全と判定する | method security enabled、filter coverage、repository tenant predicate を code verification する |
| GraphQL error semantics と RFC 9457 が衝突する | problem type URI を共有し、carrier を protocol-specific にする |

## Acceptance Criteria

### Functional

- [x] `/architect:design-api` が surface ごとの REST／GraphQL／hybrid decision record を生成する。
- [x] GraphQL 選択時だけ `/architect:design-graphql` が実行される。
- [x] `/architect:generate-graphql-code` が SDL 準拠の Spring for GraphQL application layer と contract map を生成する。
- [x] PostgreSQL 等と ScalarDB の双方で application service／repository boundary を設計できる。
- [x] ScalarDB native GraphQL の直接公開は explicit decision なしに生成されない。

### Security and operations

- [x] operation、field、object、row/tenant の認可が design と code の双方で検証される。
- [x] depth、complexity、alias、batch、page、timeout、rate、subscription limits が具体値または OQ を持つ。
- [x] DataLoader の batching と tenant-safe cache policy が全 nested DB field にある。
- [x] GraphiQL、introspection、schema printer、CORS、WebSocket origin/auth policy が environment ごとに定義される。
- [x] raw query/variables を既定で log せず、安全な observation dimensions を使う。

### Contract and quality

- [x] 全 field coordinate が SDL、handler、test、authorization、transaction、requirement に trace される。
- [x] schema drift、extra/missing resolver、nullability/validation mismatch を機械検出する。
- [x] GraphQL errors が problem type registry を再利用し、ad-hoc envelope を作らない。
- [x] 8段階品質ゲートが各 stage の command/exit code または skip reason を記録する。
- [x] REST-only project と既存 Claude/Codex commands の後方互換が保たれる。

## 実装順序と推奨 PR 分割

1. **PR 1 — decision and contracts**: API style rule、design-api decision、GraphQL contract rule、manifest conditions、tests。
2. **PR 2 — design skill**: design-graphql、templates/references、forward-test fixtures。
3. **PR 3 — generator**: generate-graphql-code、contract map extension、version resolution。
4. **PR 4 — quality enforcement**: contract tests、security review、verification、quality gate。
5. **PR 5 — docs and compatibility**: README、CLAUDE、AGENTS、skill references、end-to-end fixtures。

各 PR は独立して既存 REST path を壊さず、PR 3 以降は前段の contract artifact なしに推測生成しない。

## Sources and references

### Internal

- `skills/design-api/SKILL.md`
- `skills/design-implementation/SKILL.md`
- `skills/generate-api-code/SKILL.md`
- `skills/generate-contract-tests/SKILL.md`
- `skills/review-api-security/SKILL.md`
- `skills/verify-implementation/SKILL.md`
- `skills/common/skill-dependencies.yaml`
- `rules/api-contract-fidelity.md`
- `rules/api-error-standard.md`
- `rules/api-security-checks.md`
- `rules/ai-code-quality-gate.md`
- `rules/dependency-versions.md`
- `rules/okf-knowledge-bundle.md`
- `rules/scalardb-edition-profiles.md`
- `rules/spring-boot-integration.md`

### Official external documentation checked on 2026-08-10

- Spring for GraphQL Reference: https://docs.spring.io/spring-graphql/reference/
- Spring Boot Spring for GraphQL: https://docs.spring.io/spring-boot/reference/web/spring-graphql.html
- Annotated Controllers: https://docs.spring.io/spring-graphql/reference/controllers.html
- Security: https://docs.spring.io/spring-graphql/reference/security.html
- Request Execution: https://docs.spring.io/spring-graphql/reference/request-execution.html
- Observability: https://docs.spring.io/spring-graphql/reference/observability.html
- Releases: https://github.com/spring-projects/spring-graphql/releases
