# 変更履歴

Nexus Architect の主な変更点を記録します。

書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づき、
バージョニングは [セマンティック バージョニング](https://semver.org/lang/ja/) に従います。
バージョン番号は `.claude-plugin/marketplace.json` のプラグインごとのバージョンを指し、
3 つのプラグイン（`product`・`architect`・`scalardb`）は同一の番号で一括リリースされます。

## [Unreleased]

## [0.17.7] - 2026-07-27

### ドキュメント
- **コード生成と配送の呼び出し方を明文化。** コード生成スキルはカタログには載っていたが、
  使い方が書かれていなかった — `/architect:pipeline` の外にあること、どの順で連鎖するか、
  各スキルが何を前提とするかがどこにも書かれておらず、さらにバックログ配送のスキル群
  （`export-backlog`・`deliver-backlog`・`implement-backlog`・`review-issue`・`merge-issue`）は
  `CLAUDE.md` には記載があるのに `README.md` と `docs/skill-reference*` には**まったく載っていなかった**。
  - `README.md`: Quick Start にコード生成と配送の入口を追加。新セクション **Code Generation &
    Delivery** で4つの経路と、最も重要な違い — 経路 A は `generated/` 配下の使い捨てスキャフォールド、
    経路 B はプロジェクトの実ソースツリーに書くマージ対象コード — を提示。**Backlog Delivery** の
    コマンド表を新設し、Implementation & Codegen の表に *Requires* 列を追加。依存グラフに手動拡張
    ティアの説明を追記し、v0.17.6 のフラグとプロジェクト設定を説明する **Dependency Versions**
    セクションを新設。
  - `docs/getting-started.md` / `_ja.md`: §5「コードの生成」、§6「バックログ経由でのコード配送」、
    §7「依存バージョンの選択」を新設（既存の ScalarDB / 移行セクションは 8・9 に繰り下げ）。
  - `docs/skill-reference.md` / `_ja.md`: 実装の表に *前提* 列と手動拡張ティアの注記を追加し、
    スキルごとのモデルと役割を示す **バックログ配送** セクションを新設。

### 修正
- `CLAUDE.md` に「手動拡張ティアは `/architect:start` 経由でも呼べる」と書かれていたが、これは誤り。
  `start` は `skill-dependencies.yaml` のフェーズしか実行せず、コード生成スキルを一切参照していない。
  記述を実態に合わせ、新しい呼び出し手順への参照を追加した。

## [0.17.6] - 2026-07-27

### 追加
- **依存バージョンは pin する前に必ず調べる。確認するかどうかはユーザーが選べる**
  （`rules/dependency-versions.md` — 新しい共有契約）。従来のコード生成スキルは、モデルの記憶や
  本リポジトリ自身のスキル内サンプルからバージョン番号を書いていた。そしてそれはドリフトする —
  `config`・`local-env`・`migrate`・code-patterns はいずれも ScalarDB `3.16.0` を pin していたが、
  `spring-boot-integration.md` は `3.17.0`、実際の現行安定版は `3.18.0` だった
  （`gh release list -R scalar-labs/scalardb` と
  `repo1.maven.org/.../scalardb/maven-metadata.xml` で確認済み）。記憶から書いたバージョンは
  未検証の主張であり、古いバージョンは実際のビルドにそのまま流れ込む。

  対象はバージョンを pin するすべての生成物 — Gradle / Maven、`package.json`、イメージタグ、
  Helm / Terraform / Kubernetes、CI ランナーイメージ:
  - **記憶からバージョンを書かない。** エコシステムごとに参照先を明記した:
    `repo1.maven.org/.../maven-metadata.xml`（`search.maven.org` の solr は既定の並び順が
    バージョン順では**ない**ため、古いリリースを最新のように返す。使わない）、
    `npm view <pkg> dist-tags --json`（`latest` タグ。`next`/`canary` ではない）、
    `gh release list`（`Pre-release` 表示が明示される）、Docker Hub / Terraform レジストリ API
    （Terraform の versions 配列は**未ソート** — semver で自分で並べる）、
    `helm search repo --versions`、LTS / EOL 日付は `endoflife.date/api/<product>.json`、
    互換性の記述は context7。
  - **「最新」ではなく「安定」を選ぶ。** プレリリースは除外、`:latest`/`stable` のような可変タグは
    使わない、そのエコシステムが LTS を定義しているなら LTS を優先（多くの場合 LTS は最大の番号では
    ない）、EOL のラインは pin しない、出たばかりのメジャーは既定採用せずフラグとして扱う、
    対象プロジェクト既存の lockfile / BOM / 親 POM は "latest" より優先（作業のついでに無関係な
    依存を上げない）、そして最後に相互互換性で全体を判定する — 各々の最新版の組み合わせは
    しばしば動かない。
  - **決定を記録する。** バージョン決定表（採用 / 最新安定版 / リリース日 / 情報源 / 理由 /
    却下したもの）を成果物に書き、`work/version-decisions.json` にミラーして 7 日間再利用する
    （`--refresh-versions` で再解決）。並列サブエージェントや後続スキルが同じライブラリに
    異なるバージョンを pin することを防ぐ。
  - **調べられなかった時に推測で埋めない。** プロジェクト既存の pin にフォールバックし、
    `verified: false` と理由を記録してユーザーに提示する。

- **`--confirm-versions` / `--no-confirm-versions` と `options.confirm_versions`。**
  解決したバージョン群をユーザーに確認するか、黙って採用するかは設定可能: 実行単位はフラグ、
  プロジェクト既定は `work/pipeline-progress.json` のオプション、未設定なら対話実行では確認し
  `--auto` では確認せず採用。`/architect:start` と `/product:start` が出力言語と一緒にこの設定を
  尋ね、`init-output` が初期値を書き込む。設定に関わらず必ず確認するケース: 参照に失敗した場合、
  現行の選択肢が出たばかりのメジャーのみの場合、既存 pin が EOL の場合、ダウングレードなしに
  互換な組み合わせが存在しない場合、有償エディションや private レジストリが必要な場合。

### 変更
- バージョンを pin するすべてのスキルに contract を接続: `/architect:generate-scalardb-code`、
  `/architect:generate-infra-code`、`/architect:implement-backlog`（Step 5 — 一度解決した
  バージョンをサブエージェントに渡す。既存 lockfile は拘束的）、
  `/architect:design-infrastructure`（バージョンとサポート期限を併記）、
  `/product:generate-frontend`（React / Vite / Storybook の互換性を明示）、
  `/scalardb:scaffold`（Step 4 を新設）、`/scalardb:config`、`/scalardb:local-env`、
  `/scalardb:build-app`、`/scalardb:migrate`。
- 本文中の古い pin が「現在の正解」として読まれないようにした: `config`・`migrate`・`local-env` の
  schema-loader コマンド・migrate ルーターの `SCALARDB_TARGET_VERSION` はバージョン非依存の
  プレースホルダに変更し、code-patterns・`spring-boot-integration.md`・移行テンプレートには
  参照ルールを指す「これは日付付きサンプル」バナーを追加した。
- `/scalardb:local-env` から可変タグ `:latest` を排除した — compose ファイルは再現性のために
  具体的なタグを pin する必要がある。
- エントリードキュメントを同期: `CLAUDE.md`（ルール表・規約・フラグ）、`AGENTS.md`（Codex が使う
  シェル参照コマンド）、`OMNIGENT.md`、`skills/common/progress-registry.md`
  （`options` ブロック全体を表として明文化。`confirm_versions` を含む）。

## [0.17.5] - 2026-07-27

### 追加
- **Epic / Sub-Epic / Issue のチェックリストを進行に応じて更新するようになった**
  （`skills/common/backlog-checklists.md` — 新しい共有契約）。従来のバックログ系スキルは
  ステータスラベル・進捗コメント・manifest は更新していたが、トラッカー上のチェックボックスは
  誰も更新していなかった。GitLab / GitHub はタスクリストを進捗カウンタとして表示するため、
  実装・マージが完了した Issue でも受入基準と親のタスクリストのボックスが未チェックのまま残り、
  Epic を見る全員に対して実際の進捗を過少報告していた。チェックリストは 2 種類で、
  それぞれ更新責任を持つスキルは 1 つだけ:
  - **子アイテムのタスクリスト**（Epic の `## Sub-Epics`、Sub-Epic の `## Issues`）→
    `/architect:merge-issue`。しかもその子が実際に `done` になった時のみ（`done` を確定させるのは
    マージだから）。
  - **受入基準**（Issue の `## Acceptance Criteria`）→ `/architect:implement-backlog`（実装済み）→
    `/architect:review-issue`（検証済み）。

  全スキル共通のルール: 根拠がある時だけチェックし、意図ではチェックしない / 本文はその場で
  `[ ]` → `[x]` のマーカーのみを書き換える（`backlog-manifest.json` から本文を再生成しない —
  人間の編集を破棄してしまうため）/ 再実行は冪等 / レビューや revert で基準が満たされていないと
  判明した場合は理由を明記してチェックを外してよい / GitLab ネイティブ Epic・GitHub sub-issue
  経路では親がリンクを持ちタスクリストが存在しないためスキップ / `--dry-run` は本文を書き換えない。

### 変更
- **`/architect:export-backlog`** が両方のチェックリストを未チェックの `- [ ]` ボックスとして
  生成する（受入基準は 1 件 1 ボックス、子アイテムも 1 件 1 ボックス）。自身は何もチェックしない。
  Given/When/Then は 1 ボックスの *中* に収める — 散文として書かれた基準は下流のスキルが
  チェックできないため。
- **`/architect:implement-backlog`**（Step 7）がコミット済みコードで満たした受入基準を
  チェックし（根拠はコミット / テスト / ドキュメント）、未チェックのまま残したボックスを
  同じ進捗コメントに列挙する。親のタスクリストは触らない — Issue は PR/MR がマージされるまで
  done ではない。
- **`/architect:review-issue`**（Step 5）が PR/MR を上げる前にチェックリストとレビュー判定を
  突き合わせる: 確認できた基準はチェック、覆った基準は理由を Issue に書いてチェックを外し、
  未達のまま残るものは PR/MR 本文に明示する。
- **`/architect:merge-issue`** が未チェックの受入基準を **Step 2 の確認ゲート** で提示する
  （プリフライトには意図的に入れていない — 「プリフライトは全項目必須」という不変条件を
  弱めないため）。Step 4 では当該 Issue の Sub-Epic 内のボックスを、さらにその Sub-Epic が完了した
  場合は Epic 内の当該 Sub-Epic のボックスをチェックする。ユーザーが waive した基準はマージ
  コメントに記録し、完了に見せるためにチェックすることはしない。
- **`/architect:deliver-backlog`** に、チェックボックスは進捗の *出力* であり再開の入力では
  ないことを明記した。ステージ判定は従来どおり `impl.status` とトラッカーのラベルから読み、
  ずれているボックスは担当スキルが直すべき不具合として扱う。

## [0.17.4] - 2026-07-26

### 修正
- **`/architect:generate-docs` — v0.16.2〜v0.17.3 の全作業レビューで見つかった曖昧さ3件を解消。**
  いずれも検証済みの挙動を変えるものではなく、従来は導出可能だが暗黙だった点の明文化。
  - **単独起動時のモード判定を明記。** `--issue` なしで、かつ他スキルの一工程としてでもなく起動された
    場合は、解決された root がモードを決める — `generated/` 配下なら Scaffold、それ以外は Delivery。
    Delivery ではトラッカーへの書き込み前に `--issue` が必須で、参照する Issue が無い実行では
    コミットは作業ブランチに載せつつ、ドリフト所見はユーザーへの報告のみとなる。
  - **`findings` セクションの書き手とタイミングを明記。** 内容を生むのは Step 5 の検証だが、記載は
    Step 4 のセクション表のみで、初回実行の書き手が不在だった。Scaffold モードでは Step 5 が検証後に
    書くことを明記し、Step 4 側の記載は「前回の所見が既に存在する再実行」を扱うものと位置づけた。
  - **安定キー一覧の情報源を一本化。** SKILL.md の散文と契約テストの `STABLE` 集合に二重管理されて
    おり、同期はコメント頼みだった。テストが SKILL.md の「Section keys are stable (…)」の一文から
    一覧を parse するようになり、当該文が消えた場合はハードフェイル、ファイルが単体でコピーされた
    場合はフォールバック一覧で検査を継続する。検証済み: 8キー全て parse され、両フィクスチャと
    フォールバック経路がすべて PASS。

## [0.17.3] - 2026-07-26

本リリースの内容はすべて、バックログ配送経路を実地で動かした結果として得られたものです — マーカー契約を
実在の `/product:generate-frontend` スキャフォールドに対して、Output Location インターロックをスクラッチ
リポジトリで、Step 1 のサブエージェント委譲を実プロジェクトで、そしてトラッカーへの全書き込み経路
（ステータス遷移・進捗コメント・PR 連携・マージ・クローズ・ロールアップ）を実作業項目ではなく使い捨て
リポジトリに対して実行しました。

### 修正
- **`/architect:merge-issue` — 親ノードの完了が manifest に届くようになった。** Step 4 の記述が
  "update the node"（単数）で、しかも Issue にしか存在しない `pr.merged` や merge SHA と併記されて
  いた。そのため Sub-Epic/Epic をトラッカー上で `status::done` にしても manifest には何も書き戻され
  なかった。実在の35ノードのバックログでまさにこの状態を観測 — Issue 27件は全て `impl` を持つ一方、
  Epic と完了済み Sub-Epic 4件には `impl` キー自体が無かった。`deliver-backlog` は `impl.status` を
  読んで resume するため、完了済みの Sub-Epic を未着手と誤認する経路になる。Step 4 はロールアップが
  動かした全ノードを更新するようになり、`pr` 系フィールドは Issue のみに限定された。
- **`/architect:export-backlog`・`/architect:deliver-backlog` — manifest の `labels` 配列は作成時の
  シード値であり現在値ではない。** 作成時に付与された内容（`status::todo` と type/domain ラベル）を
  記録するだけで以後更新されず、ステータスはトラッカーと `impl.status` にある。実バックログでは全
  ノードが `status:todo` のままなのに、トラッカー側は done 7 / doing 9 だった。現状は誰も読んで
  いないため実害は無いが resume ロジックの罠になるため、`export-backlog` にフィールドの正体
  （`--update` 時のみ書き換わることも含む）を明記し、`deliver-backlog` には状態を `impl.status` と
  トラッカーから読むこと、`labels` からは読まないこと、食い違い時はトラッカーが正であることを明示した。
- **`/architect:generate-docs` — インベントリダイジェストが観測値と推論値を区別するようになった。**
  Step 1 の委譲を実行して設計自体は検証できた（haiku の Explore が6項目すべてを埋めたダイジェストを
  返し、独立に検証済みの数値・コマンドと全件一致、ソースの貼り付けも捏造もゼロ）が、穴が判明した —
  `package.json` に `engines` の宣言が無いにもかかわらず「Node.js 18+」をインベントリとして断定して
  いた（Vite 5 の要件からの推論）。結論は正しいが、オーケストレーターはダイジェストしか持たないため
  観測と推論を区別できず、推論が事実として README に流れ込み、本スキルの中核規律を無効化する。導出値は
  `inferred: <値> (<根拠>)` と明示することが必須となり、根拠付きで書くかヘッジする扱いになった。
- **`/product:generate-frontend` — 再生成が上書きする旨を事前に告げるようになった。** 出力先自体は
  正しい（再実行での置換が前提だからこそ `adapt-change` がこのスキルを再実行する）が、再実行が出力先
  配下の手編集を破棄することへの警告が皆無だった。`adapt-change` が可逆性を担保している一方で、実際に
  書き込む当人が沈黙していた。上書きする旨を明示して確認を取り（`--auto` 時を除く）、`--out=<path>`
  による併存の選択肢を提示し、手で保守されるフロントエンドに育った時点で `generated/` の外へ移すべき
  ことを明記した。

### 追加
- **`skills/implement-backlog/output-location.test.sh`** — Output Location インターロックを挙動として
  検証。`reports/`・`generated/`・`work/` を含む通常の `.gitignore` を持つスクラッチリポジトリを構築し、
  `check-ignore` が `generated/` 配下の source root を拒否して該当ルールを提示すること、ワークツリー内の
  実在する `services/` root を受理すること、ドキュメントのコミットが `feature/<issue-id>-<slug>` に
  Issue 参照付きで着地し意図したファイルを stage すること、git が無視するパスでは何も stage されず
  コミットが空コミットではなく拒否されることを確認する。11項目、失敗時 exit 1。

### 変更
- 両 CHANGELOG のリンク参照ブロックが陳腐化していた — `CHANGELOG.md` は `0.8.2` で止まり、タグ付き13
  バージョンが未リンクな上、作成されたことのないタグを指す壊れた `[0.7.0]` リンクが存在し、
  `CHANGELOG_ja.md` には参照が1件も無かった。両方に既存タグと1対1対応する参照を揃えた。
- `docs/codex-gap-analysis_ja.md` の「80 skills」を **87**（architect 50 / product 26 / scalardb 11）に修正。

## [0.17.2] - 2026-07-26

### 修正
- **`/architect:generate-docs` — 領域の挿入と撤去が正確な逆操作になった。** 再実行テストにより、
  マーク付き領域の周辺空白が未定義であることが判明。撤去 → 再挿入で元のファイルが再現せず、
  サイクルを繰り返すたびに空白だけの差分ノイズが残っていた（レビュー可能であることが存在理由の
  ファイルにおいて実害がある）。規則を明文化 — 領域と前後は空行ちょうど1行で区切る（ファイル
  先頭/末尾に接する場合を除く）、撤去は領域＋後続の空行1つ（EOF 隣接なら直前の1つ）を取る、
  ファイル末尾は改行1つで空行2連続は作らない。規則を書く前に検証済み: この規則の下で、中間位置と
  EOF 隣接の両方について撤去 → 再挿入がバイト一致し、撤去/追加を5サイクル繰り返してもドリフト
  しない。

### 追加
- **`skills/generate-docs/marker-mechanics.test.py` — オーナーシップマーカー契約を挙動として
  検証。** SKILL.md はマーカー規則を散文で記述しているため、後の編集が再実行安全性を静かに壊し
  得た。5つの性質にわたる17項目を検査 — その場更新でマーカー外の散文がバイト単位で不変かつ領域が
  重複しないこと、再適用が no-op であること、撤去が他のコンテンツに触れないこと、安定キー一覧外の
  キーが更新・撤去の両方で拒否されること、挿入と撤去の往復がバイト一致し繰り返してもドリフト
  しないこと。埋め込みフィクスチャで自己完結して動作し、パスを渡せば実 README も検査可能。
  失敗時は exit 1（`hooks/*.sh` の CLI 規約に準拠）。

### 変更
- CLAUDE.md の検証に関する記述に本テストを追加し、陳腐化していたプラグインバージョンの記載
  （`0.15.0`）を削除。3プラグインが同一バージョンを共有し一括で bump される旨に改め、リリース
  フローにタグ作成と GitHub Release の手順を追記。

## [0.17.1] - 2026-07-26

### 修正
- **`/architect:generate-docs` — ドリフト所見の置き場と、生成セクションの撤去規則を追加。**
  実在の `/product:generate-frontend` スキャフォールドに対して本スキルを実行したところ、3つの
  欠落が判明した。
  - **Scaffold モードにドリフト所見の置き場が無かった。** Step 5 は「ユーザーに報告し Issue に
    追記」と規定していたが、Scaffold モードにはトラッカーが存在せず、実行時にセクションキーを
    その場で発明せざるを得なかった。安定キー一覧に `findings` を追加し、モード別の記録先を表で
    明示 — Delivery モードでは **Issue** にコメントとして追記（トラッカーが記録媒体であり、
    ドキュメントには書かない）、Scaffold モードでは **`findings` セクション**に記載。いずれの
    場合もドリフトを散文で解消してはならない（コードが行っていない整合をドキュメントが主張して
    しまうため）。
  - **撤去規則が無かった。** 後続の実行で正当性を失ったマーク付きセクション（解消済みのドリフト、
    削除されたサービス、消滅した対象面）は、マーカーごと削除して実行レポートに列挙する。古い
    生成セクションが残るのは、無いことより悪い。削除可能なのは安定キー一覧にあるキーのみで、
    手書きコンテンツには触れない。一覧外のキーの発明も禁止（次回実行時に領域を発見できなくなる）。
  - **git 管理外の対象で生の git エラーが出ていた。** Delivery モードは git ワークツリー外では
    コミットできない旨を明示し、リポジトリを必要としない Scaffold モードを提案するようにした。

  検証結果（マーカー無しの手書き README を対象）: 元の散文は 24/24 行が温存され、生成領域はすべて
  安定キーのマーカー内に収まり、検証工程は実プロジェクトに対してコマンド 6/6・パス 18/18 の実在を
  確認したうえで、当該 README の実在する記述不備を3件検出した。

## [0.17.0] - 2026-07-25

### 追加
- **`/architect:generate-docs` — 生成・実装されたコードのドキュメント（`architect` プラグイン、新規
  スキル）。architect プラグインは 50 スキルに。** コード生成スキルと `implement-backlog` が
  コードを出力する一方で、それを説明する README や `docs/` を作る工程が存在しなかった。本スキルが
  その工程を担い、両方の経路に定位置を持つ。
  - **2つのモード。** *Scaffold* は `generate-scalardb-code` / `generate-infra-code` /
    `/product:generate-frontend` の後に `generated/` を対象とし、コミットしない（再生成可能な
    領域のため）。*Delivery* は作業ブランチ上の解決済み `source_root` を対象とし、Issue 参照付きで
    コミットするため、コードと同じ PR/MR にドキュメントが載る — git に無視されるドキュメントは
    PR に到達できないため、`git check-ignore` とワークツリー内チェックを踏襲。
  - **その場での更新。** オーナーシップマーカー（`<!-- nexus:begin:<section> -->` …
    `<!-- nexus:end:<section> -->`）により再生成対象を本スキルが書いた領域のみに限定。人間が
    書いた散文は保持し、マーカーの無い手書き README は確認なしにその場で書き換えない。
    セクションキー（`overview`・`build-and-run`・`configuration`・`layout`・`api`・`operations`・
    `traceability`）は安定しており、再実行時は同じ領域を更新する。
  - **存在するものを書く。** 内容は実際のコード・ビルドファイル・設定から導出し、設計レポートは
    *why* のみを供給する。検証工程で、記載した各ビルド/実行/テストコマンドが実在するビルド
    ターゲットに裏付けられているか、リンクとパスが解決するかを確認し、コードのインベントリに
    無い設定キーやルートを排除し、設計とコードの乖離は散文で埋めず所見として報告する
    （Delivery モードでは Issue に追記）。
  - **コストティアリング実行。** ソースではなくダイジェストを保持する薄い sonnet オーケストレーター。
    コードのインベントリ化・設計意図の抽出・検証は haiku、ページ執筆はページ単位の並列 sonnet、
    opus は判断が重い設計解説（2PC 境界、整合性モデル、障害・復旧セマンティクス）のみ。

### 変更
- **`/architect:implement-backlog` — 実装コードを記録する Step 5b を新設。** 実装（Step 5）と
  レビュー（Step 6）の間で `/architect:generate-docs --scope=changed --source-root=<resolved>
  --issue=<iid>` を実行し、ドキュメント変更を同じ作業ブランチにコミットする。これによりコードと
  ドキュメントが1つの PR/MR でレビュー・マージされる。スキップはドキュメント対象の変更が無い
  場合に限り許容され、その理由を進捗コメントに記録する必要がある。サブエージェント割当表・
  Desired Outcome・Acceptance Criteria も併せて更新。
- **`/architect:deliver-backlog`** — ステージ (a) に、implement 工程が README/`docs/` の更新を
  同じ PR/MR へ運ぶことを明記。
- `generate-scalardb-code`・`generate-infra-code`・`/product:generate-frontend` から
  `generate-docs` への downstream 参照を追加。CLAUDE.md の manual extension tier に
  **コード生成 → `generate-docs`** の固定順序を記載。AGENTS.md のモデルティア・README.md・
  `docs/skill-reference{,_ja}.md` も同期。

## [0.16.2] - 2026-07-25

### 修正
- **`/architect:implement-backlog` — マージ対象のコードを `generated/` ではなくソースツリーへ出力。**
  本スキルが生成するのは成果物であり、コードは `feature/<issue-id>-<slug>` にコミットされ、
  `/architect:review-issue` が PR/MR でレビューし、`/architect:merge-issue` がマージする。にもかかわらず
  デフォルト出力が `generated/` だったため契約が矛盾していた — `generated/` は再生成可能な
  パイプライン出力であり、対象プロジェクトでは `reports/`・`work/` と併せて git-ignore される
  ことが多く、`git add` が黙って何も stage せず、空コミットによって実装 → レビュー → マージの
  連鎖が破綻し得た。新設の **Output Location** セクションで source root の解決順を定義
  （`--out` → `shared-context/decisions.md` に記録された `source_root` → 既存のリポジトリ
  レイアウト → グリーンフィールドではユーザー確認のうえ `services/{service}/`）し、解決結果を
  `decisions.md` に記録することで Epic 配下の全アイテムが同一の出力先を使うようにした。
  Step 4 では、コード書き込み前に 2 つの事前チェックを必須化 — `git check-ignore -q <source_root>`
  が exit 1（無視ルール不一致）であること（それ以外の exit は git エラーとして提示し、安全と
  みなさない）、および root が対象ワークツリー内に解決されること。Step 5 では実装サブエージェントを
  解決済み root 内に限定し（外部への書き込みが必要な場合はスコープを広げず停止して報告）、
  各コミットが意図したファイルを実際に stage したかを `git show --stat` で検証し、空コミットは
  レビューへ進めず Output Location へ差し戻す。`generated/` はワンショットのコード生成スキル
  （`generate-scalardb-code`・`generate-infra-code`・`generate-frontend`）用の意味を維持し、
  使い捨てスキャフォールドが目的の場合は `--out=generated/<service>/` で従来どおり選択できる。
  `templates/output-structure.md` と CLAUDE.md のコマンドリファレンスも新しい契約に同期。

## [0.16.1] - 2026-07-25

### 変更
- **`/architect:implement-backlog` — サブエージェントによるトークン最適化実行。** スキル本体を薄い
  **sonnet** オーケストレーター（従来は opus）とし、重い工程をモデルティア別サブエージェントへ委譲。
  新設の「Sub-Agent Execution & Model Assignment」セクションに割当を明文化: 共有コンテキストパックの
  導出は並列 sonnet（Step 1）、Epic・兄弟 Issue・設計レポートのダイジェスト化は haiku の Explore
  （Step 3）、Epic 横断契約に対するミニプラン起案は opus（Step 4）、実装はまとまり単位の sonnet
  （判断が重い設計のみ opus へ昇格、Step 5）、Epic 整合性判定とロールアップレビューは opus
  （Step 6）、進捗コメントと impl-log ミラーの下書きは haiku（Step 7）。コスト規則も明示化 —
  オーケストレーターはレポート本体ではなくダイジェストのみ保持し、各工程は足りる最安ティアを使用
  （opus は計画と整合性判断のみに限定）。AGENTS.md のモデルティア表と CLAUDE.md のコマンド
  リファレンスも同期（モデル切替のないランタイム向けにセッションモデルのまま委譲構造を維持する
  指針を追記）。

## [0.16.0] - 2026-07-24

### 追加
- **Backlog Delivery スキルファミリ（`architect` プラグイン、新規5スキル）** — 生成済みレポートを
  GitLab/GitHub 上のマージ済みコードまで届ける一連のワークフロー。**architect プラグインは 49 スキルに。**
  - `/architect:export-backlog` — product/architect のレポートから Epic（What/Why）→ Sub-Epic
    （What/Key Results）→ Issue（How）の3階層バックログを起票。レビューファースト
    （`reports/backlog/backlog-plan.md` + `backlog-manifest.json` を承認後にリモート書込）、冪等な
    再実行、GitLab ネイティブ Epic＋スコープドラベルのフォールバック、GitHub ラベル＋タスクリスト
    方式、全階層へのトレーサビリティ ID 引き継ぎ、全ノードへの `status::todo` 付与。
  - `/architect:implement-backlog` — Epic 全体の整合性を保ちながら選択アイテムを実装。親 Epic と
    同一 Epic 配下の兄弟を参照し、共有エンジニアリングコンテキストパック
    （`reports/backlog/shared-context/`: アーキテクチャガードレール・コーディング規約・ユビキタス
    言語・データ契約・NFR 予算・ADR-lite 決定ログ）と照合し、共有ブランチ契約
    `feature/<issue-id>-<slug>` 上で `generated/{service}/` にコードを出力。Epic/Sub-Epic/Issue へ
    進捗を追記し、軽量＋オンデマンド（`--review-epic`）の整合性レビューを実行。指定がなければ
    `status::doing` のアイテムをユーザー確認のうえ選択。
  - `/architect:review-issue` — 実装済み Issue を Epic 全体の観点（親 Sub-Epic/Epic＋関連 Issue）で
    レビューし、`[B]` ブロッカーは修正サブエージェントによる有界ループで自動修正
    （`--max-fix-rounds`＋無進捗検知。非収束時は Issue に「判断が必要」コメントを書き
    `status::blocked` にしてユーザーに確認）。ブロッカー解消後は Issue 紐付きの PR/MR を起票して
    承認待ちで停止。各ラウンドの指摘は重複排除されたプロジェクトナレッジベース
    （`shared-context/review-knowledge.md`、`KN-` エントリ）に蒸留され、以降の計画・実装が参照する。
  - `/architect:merge-issue` — 承認済み PR/MR を厳格なプレフライト（open・Mergeable 判定・承認・
    CI green・コンフリクトなし）と明示確認ゲート（スキップは `--yes-merge` のみ、プレフライトは
    スキップ不可）の背後でマージし、Issue をクローズ（`status::done` の単一権限）、Sub-Epic/Epic の
    進捗をロールアップ、Sub-Epic 完了時に Epic 統合レビューを起動。
  - `/architect:deliver-backlog` — Epic 配下の各 Issue を implement → review →（人間の承認）→
    merge の順に駆動する半自律オーケストレーター。`backlog-manifest.json` から再開し、人間ゲートで
    ハード停止。`--yes-merge` なしでは自動マージしない。
- **共通ステータス語彙** — `status::todo/doing/review/done/blocked`（GitHub は `status:` 形式）を
  ファミリ全体で共有。export-backlog が seed し、下流スキルが遷移させる。

## [0.15.0] - 2026-07-15

### 追加
- **`architect` プラグイン: `/architect:estimate-token-cost` スキル** — architect パイプラインを
  コードベースに対して実行した場合のトークン使用量と USD コストを見積もる。事前見積もりモデル
  （コード行数 → 取り込みトークン → キャッシュ調整後の課金入力、typical/low/high の3バンド）と、
  `work/token-usage.json` の実測値による較正（部分実行時は残フェーズを外挿）を組み合わせる。
  インフラ・ライセンス・運用コストを扱う `/architect:estimate-cost` とは別物。
  **architect プラグインは 44 スキルに。**
- **フェーズ別トークン使用量の自動記録（`hooks/record_token_usage.py`）** — フェイルセーフな
  フック（`Write|Edit|MultiEdit|Task|Agent` の `PostToolUse` と `Stop`/`SubagentStop`）が
  セッショントランスクリプトを差分解析し、課金トークン（入力/出力、キャッシュ読み、5分/1時間
  キャッシュ書き込み、Web検索リクエスト）をパイプラインフェーズに帰属させる：`in_progress`
  フェーズ優先、次に新たに `completed` へ遷移したフェーズ（保留バケットを回収）、いずれも
  なければターン終了時に `_unassigned`。`work/token-usage.json`（フェーズ×モデル台帳 + USD）と
  `work/token-usage.jsonl`（追記専用監査ログ）を出力。初期化済みパイプラインプロジェクト外では
  不活性。並列サブエージェントの発火は flock で直列化し、message id はチャンク境界をまたいで
  重複排除。
- **`skills/common/references/model-pricing.json`** — モデル価格（期間限定の導入価格を含む）、
  キャッシュ倍率、サーバーツール価格、事前見積もりヒューリスティクスの単一ソース。記録フックと
  見積もりスキルが共有する。
- **`rules/token-pricing.md`** — 台帳スキーマ（`token-usage-v2`）、帰属の意味論と注意点、
  見積もり手法、サブスクリプション課金と API 課金の違いを記載。`CLAUDE.md` の Rules & References
  表から参照。

## [0.14.0] - 2026-07-13

### 追加
- **インプット要件ガイド（`docs/product-input-requirements.md`・
  `docs/architect-input-requirements.md`、EN/JA）** — 各プラグインのパイプラインを実行する際に
  利用者が用意すべき情報をまとめたドキュメント（エントリーポイント、必須／推奨インプット、
  対話モードと `--auto` モード、フェーズごとのヒアリング項目、product→architect のハンドオフ）。
  README・`getting-started`・`skill-reference`・`AGENTS.md`・`CLAUDE.md` からリンク。

## [0.13.0] - 2026-07-07

### 追加
- **`product` プラグイン: `/product:name-product` スキル** — プロダクトを**アルファベット・アクロニム**として
  命名する：各文字が英単語の頭文字になる短く発音可能なラテン文字名で、名前自体が価値フレーズに展開される。
  ビジョン/ポジショニングに根ざして候補を絞り込み、1 案を推奨する。任意実行（`full` プロファイルに含む）。
  新ルール `rules/product/naming-frameworks.md` を追加。**product プラグインは 26 スキルに。**
- **Omnigent 互換レイヤー** — `OMNIGENT.md` とローダー（`tools/omnigent/load-skill.sh`）により、
  汎用マルチエージェント・オーケストレーターが約 90 個の `SKILL.md` を無改変で実行できる。ローダーは
  `plugin:skill` 名をファイルパスに解決し、翻訳プリアンブルを出力し、`${CLAUDE_PLUGIN_ROOT}` を展開する。
  非侵襲（スキルファイルの変更なし）でテスト付き。

### 変更
- **`AGENTS.md` のモデル階層推奨を現行の product 26 スキルに同期**（16 opus / 10 sonnet）。各スキルの
  `model:` frontmatter と両依存マニフェストに一致。

### 修正
- **入れ子 migrate サブスキルの陳腐化フラットパス（12 ファイル 30 箇所）** — 実行可能な `cd` ブロック、
  Related Skills、出力ツリー、抽出スクリプトのコメントが入れ子化前のパス
  （例: `skills/analyze-mysql-schema/...`。正しくは `skills/migrate-mysql/analyze-mysql-schema/...`）を
  参照していた。
- **ドキュメントのドリフト**: README のスキル数を修正（77 → 80）。CLAUDE.md のモデル階層表を修正
  （`analyze` = opus、`report` = haiku）し、product の階層リストを全 26 スキルに補完。CLAUDE.md に
  `/product:design-architecture` を追加。スキルリファレンス（EN/JA）に `/product:create-domain-story` と
  `/product:design-system` を追加。`generate-ui-mock` の説明を実際の駆動源（ドメインストーリー +
  デザインシステム）に更新。
- **パイプラインの範囲を明確化**: `skill-dependencies.yaml` 外の architect 12 スキル（インフラ、
  セキュリティ、オブザーバビリティ、DR、実装、コード生成、コスト見積、セキュリティ調査）を
  `/architect:pipeline` が実行しない**手動拡張ティア**として明記し、pipeline スキルの「全スキル」の
  記述を実態に合わせて修正。
- **product→architect ブリッジ成果物を受け手側で宣言**: `design-microservices` が `architecture.md` /
  `tech-stack-fitness.md` を、`design-api` が `api-design.md` を任意入力として明記（再導出でなく
  リファインするセマンティクス）。
- レビューフェーズの `parallel_with` 宣言を対称化。見出しを `Desired Outcome` / `Decision Criteria` に
  正規化（5 スキル）。scalardb ユーティリティ 5 スキルの説明に「Use when」トリガーを追加。`workflow/` と
  `research/` に位置づけ README を追加。README にドキュメント言語ポリシーを追加。Codex 監査ドキュメントに
  時点スナップショット注記を追加。getting-started（EN/JA）に `samples/ec-monolith` の導線を追加。
  define-requirements の brainstorm ドキュメントの陳腐化した `research/` ファイル名を修正。

### ドキュメント
- getting-started ガイド（EN/JA）に `/product:generate-frontend` を掲載。

## [0.12.0] - 2026-06-29

### 追加
- **`product` プラグイン: `/product:generate-frontend` スキル** — ナビゲート可能な UI モックとアクティブな
  デザインシステムから、**実行可能な React + TypeScript フロントエンド**を `generated/frontend/` に生成する。
  画面を **Atomic Design** で分解し（デザイントークン → atoms → molecules → organisms → templates → pages）、
  デザインシステムの各 `CMP-` を対応する原子レベルのコンポーネントに、各 UI モック画面をページにする。
  コンポーネントは **CSS Modules + CSS 変数**でスタイリングし、デザイントークンのみを参照する（生値は使わない）。
  ストーリーフロー（`next`/`prev`）は **react-router** で配線し、各コンポーネントを **Storybook** に variant/state
  ごとの story として登録する。自己完結でインストール可能な scaffold（React 18 + Vite + Storybook 8 + TS）を出力する。
  新ルール `rules/product/atomic-react-storybook.md` を追加。トレーサビリティに `COMP-`/`PAGE-` ノードを
  `CMP-`/`TOK-`/`STORY-` への Upstream 参照付きで記録する。spec フェーズの `generate-ui-mock` の後に実行する。
  **product プラグインは 25 スキルに。**

### 変更
- **`product` プラグイン: `/product:start` が `generate-frontend` を選択式ステップとして提示**するようになりました。
  UI モックの後に、実行可能な React + Storybook フロントエンドを生成するか対話的に尋ね（インタラクティブ）、
  `--auto` ではプロファイルに従う（`ux-to-spec` / `full` に含まれる）。新フラグ `--frontend` / `--no-frontend` で
  選択を強制でき、決定は `work/pipeline-progress.json` → `options.frontend` に記録する。このステップは非ブロッキングで、
  後続フェーズは生成コードではなくモックを参照する。

## [0.11.0] - 2026-06-26

### 変更
- **`product` プラグイン: `/product:generate-ui-mock` がクリックで遷移できるナビゲート可能なプロトタイプを生成**
  するようになりました。これまでの画面が独立した単一 HTML ファイル群だった状態から、ドメインストーリーの
  番号付きアクティビティ順に画面を並べ、各画面の「フローを前進させるアクション」を次のアクティビティの画面への
  実際の `<a href>` リンクにします。これにより、ストーリー全体をクリックで端から端まで辿れます。各画面には
  戻る/次へのナビゲーションと `step N of M` 表示、分岐は対象画面へのリンク、ストーリーごとのフローインデックス
  （`{STORY}-index.html`）を入口として追加します。ファイル名は決定論的（`{STORY}-NN-{slug}.html`）で、ソースに
  欠けているステップは無効化した `TBD` リンクとして表示します（デッドエンドは作りません）。トレーサビリティに
  画面間の `next`/`prev` エッジを記録します。

## [0.10.0] - 2026-06-24

### 追加
- **`product` プラグイン: `/product:create-domain-story` スキル** — ペルソナ起点のドメインストーリーテリング。
  アクターはペルソナ（`PER-`）、アクティビティはジョブストーリー（`JOB-`）をジャーニー（`JNY-`）順に並べたもの、
  ワークアイテムは扱う対象から導出する。各ストーリーは「あるペルソナが主要ジョブを遂行する」ハッピーパスの
  シナリオで、ペルソナ×ジョブ単位でスコープする（境界づけられたコンテキストは `--domain` による任意の拡張）。
  UX フェーズの、ジャーニー／ポジショニングの後・UI モックの**前**に実行し、`reports/01_ux/domain-stories/` を
  `STORY-` トレーサビリティ付きで出力する。`/architect:create-domain-story` の product パイプライン版。
- **`product` プラグイン: `/product:design-system` スキル** — **分離管理**のデザインシステムを構築または
  `--import` で取り込む。構築はポジショニング／ペルソナ／ビジョンから **W3C DTCG** トークン
  （color/type/spacing/radius/elevation/motion）を WCAG コントラストゲート付きで導出。`--import` は既存システム
  （Tailwind config / DTCG JSON / Figma Tokens / CSS テーマ）を同一スキーマへ正規化する。出力は `reports/` 配下では
  なく専用の `design-system/<name>/` ツリーに置き、semver の `manifest.json` を持ち、複数の名前付きシステムを
  併存でき、**standalone**（いつでも単独実行可能）。アクティブなシステムは
  `work/pipeline-progress.json` → `options.design_system` に記録する。新ルール
  `rules/product/design-system.md` を追加。**product プラグインは 24 スキルに。**

### 変更
- **`/product:generate-ui-mock` がストーリー駆動＋デザインシステム適用に** — 画面は各ペルソナ×ジョブの
  ドメインストーリーから導出し（1 アクティビティ ≒ 1 画面操作）、アクティブなデザインシステムでスタイリングする。
  各 self-contained 画面に `tokens.css` をインライン注入し、`--fidelity=lo`（トークンのみ）または
  `mid`（トークン＋`CMP-` コンポーネントスタイル）で描画する。システム未設定時はアドホックな lo-fi へフォールバック。
  画面は `STORY-`/`CMP-` もトレースする。
- **UX フェーズの順序** — `full` プロファイルで `create-domain-story` と `design-system` をポジショニングの後・
  `generate-ui-mock` の前に実行し、モックが「選択された流れ」を「共有の視覚言語」で描けるようにした。

## [0.9.0] - 2026-06-24

### 追加
- **`product` プラグイン: `/product:design-architecture` スキル** — 境界づけられたコンテキスト・
  API レイヤー・データモデル・非機能要件を統合してランタイムの全体アーキテクチャを生成し（Mermaid の
  構成図 / クリティカルパス / デプロイ・スケーリングの 3 ビュー）、定型チェックリスト
  **Kong（API Gateway）・ScalarDB・ScalarDB Analytics・ScalarDL** に対する**技術適合度評価**を
  成果物の根拠に基づいて実施。各技術に **採用 / 条件付き採用 / 不採用** の判定と採用理由・配置を出力する。
  ScalarDB / ScalarDL の「採用」は architect プラグインの ScalarDB パイプラインへの橋渡しとなる。
  出力は `reports/03_domain/architecture.md` と `reports/03_domain/tech-stack-fitness.md`。
  `full` プロファイル（`define-nfr` の後の総合ステップ）と依存グラフに追加。新ルール
  `rules/product/architecture-and-tech-fitness.md` を追加。product プラグインは 22 スキルに。
- **product → architect ハンドオフ契約（`docs/design.md`）** — `product` の成果物が `architect`
  プラグインのインプットとしてどう橋渡しされるかの単一の真実。4 つの SKILL/ルールファイルで宙吊りに
  なっていた `design.md` 参照を解消。成果物マッピング（成果物ごとの ID 接頭辞 → `define-requirements`
  の成果物、§1.3）、`product` が供給しない設計上のギャップ（§1.4）、クロスプラグインの
  **トレーサビリティ書き戻し**契約（`FEAT-→FR-` リンク、`NFR-` の verbatim 再利用、§1.5）、
  正典の**適応エンジン**仕様（§7）を定義。

### 変更
- **`/architect:define-requirements` が product 成果物を取り込む** — `reports/0*_*/` の product
  レポートを自動検出し、product の ID を引き継ぎ、`tech-stack-fitness.md` を ScalarDB 適用判定の
  prior として利用し、`FR-`/`NFR-` ノードを `work/traceability.json` へ書き戻す。
- **`/architect:start`・`/architect:pipeline` の product 認識** — 前段でハンドオフ検出を行い、
  product レポートを渡してグリーンフィールドパスへ誘導する。
- **`/product:map-domains`** が `CTX-` ごとに粗い整合性ヒント（`Strong`/`Eventual`/`TBD`）を出力し、
  architect のトランザクション整合性分類の起点とする。
- **`/architect:review-consistency`** がクロスプラグインのトレーサビリティ継続性を検査する。

## [0.8.2] - 2026-06-20

### 変更
- 3 プラグインのバージョンを 0.8.2 に更新。

### ドキュメント
- これまで architect の 43 スキルのうち 41 件しか記載していなかった
  `create-domain-story`（設計）と `review-report`（レポート）を `README.md` および
  スキルリファレンス（en/ja）に追加。
- `/architect:pipeline` のフラグ記載を実態に合わせて修正
  （`--resume-from`・`--rerun-from`・`--skip-{phase}`・`--no-scalardb`・`--lang`）。
- Getting Started / Codex 利用ガイド（en/ja）に `product` プラグインの導線を追加：
  「プロダクトの方向性（グリーンフィールド）」の起点、`/product:*` のスキルマッピング
  （`skills/product/<name>/SKILL.md`）、product のインストールコマンドを追記。

## [0.8.1] - 2026-06-20

### 修正
- `product:` / `scalardb:` 名前空間のスキルが読み込まれないプラグイン名前空間の衝突を修正。
  マーケットプレイス マニフェストで各プラグインに明示的な `skills[]` 配列を持たせ、
  各プラグインが自身のコマンドのみを登録するようにした。

## [0.8.0] - 2026-06-20

### 追加
- **`product` プラグイン**（21 スキル、14 ルール）— プロダクトビジョンから SLA/NFR までを
  対話的・検証駆動で進めるプロダクト方向性パイプライン。深い設計の前に最もリスクの高い前提を
  抽出・検証し、トレーサビリティグラフで変更を再伝播し、システム実装設計のために
  `/architect:define-requirements` へ引き継ぐ。

これにより Nexus Architect は 3 プラグイン構成（`product`・`architect`・`scalardb`）、
合計 75 スキルのツールキットになりました。

## [0.7.0] - 2026-06-11

### 追加
- グリーンフィールドの起点となる `/architect:define-requirements` スキル：機能/非機能要件の
  分類、データ・トランザクション要件分析、ScalarDB 適用判断。`--input`・`--auto`・
  `--no-scalardb` をサポート。

## [0.6.2] - 2026-06-11

### 追加
- ドメインストーリーテリング用の `/architect:create-domain-story` スキル
  （ドメインごとの業務プロセスを可視化）。
- 生成された HTML レポートの品質をレビューする `/architect:review-report` スキル。
- ツールキット検証用の `ec-monolith` サンプルプロジェクト。

### 修正
- フック・スキル・マニフェスト全体のエージェント構成監査の指摘を解消。
- Mermaid バリデータのブロック解析を修復し、ユビキタス言語の用語整合ルールを追加。
- `investigate` スキルに計算手順と自己検証を追加。

## [0.6.1] - 2026-05-12

### 追加
- レビュー・評価スキルでの並列サブエージェント実行。
- スキーマレポート後の `migrate-oracle` SA3/SA4/SA5 ステージの並列化。

### 修正
- 28 ファイルにわたる多視点レビューの修正。
- 移行パイプライン全体のスキル呼び出しとネストされたサブスキルパスを修正。

## [0.6.0] - 2026-05-07

### 追加
- Codex 互換レイヤー（`AGENTS.md`）：Claude Code プラグインをインストールせずに
  同じスキルファイルを Codex から利用可能に。

### 修正
- `/architect:` プレフィックス登録を有効にするため、全 SKILL.md から `name` フィールドを削除。
- スキル監査の指摘（マニフェスト命名、フロントマター、JDBC パターン）を解消。

## [0.5.0] - 2026-03-24

### 変更
- ScalarDB 開発スキルを独立した `scalardb` プラグインに分離。

## [0.4.0] - 2026-03-23

### 追加
- データベース移行（Oracle / MySQL / PostgreSQL → ScalarDB）：スキーマ抽出、移行分析、
  ストアドプロシージャ/トリガーの Java 変換。

## [0.3.0] - 2026-03-23

### 追加
- ScalarDB アプリケーション開発スキル（スキーマモデリング、設定、CRUD/JDBC パターン、
  スキャフォールド、コードレビュー、移行アドバイザリ）。

## [0.2.0]

### 変更
- リポジトリを Claude Code プラグイン互換の構成に再編。

[0.17.4]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.4
[0.17.3]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.3
[0.17.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.2
[0.17.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.1
[0.17.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.17.0
[0.16.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.2
[0.16.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.1
[0.16.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.16.0
[0.15.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.15.0
[0.14.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.14.0
[0.13.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.13.0
[0.12.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.12.0
[0.11.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.11.0
[0.10.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.10.0
[0.9.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.9.0
[0.8.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.2
[0.8.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.1
[0.8.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.8.0
[0.6.2]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.2
[0.6.1]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.1
[0.6.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.6.0
[0.5.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.5.0
[0.4.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.4.0
[0.3.0]: https://github.com/wfukatsu/nexus-architect/releases/tag/v0.3.0
