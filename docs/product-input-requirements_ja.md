# product プラグイン インプット要件ガイド

`product` プラグインを動かすときに、**利用者が用意すべき情報**をまとめたリファレンスです。
スキル間で自動生成・自動連携されるファイル（`reports/` 配下の成果物など）は対象外とし、「パイプラインを回すために人間が持ち込む必要がある情報」に絞って記載します。

architect プラグインのインプットは [architect-input-requirements_ja.md](architect-input-requirements_ja.md) を参照してください。

## 共通の原則

- **捏造しない（Never fabricate）**：市場データ・競合名・数値・要件は、入力資料・利用者の回答・引用付きWeb調査のいずれかに根拠が必要です。不明な項目は勝手に埋めず `TBD`（Open Questions）に記録されます。
- **ギャップ駆動の対話（gap-driven elicitation）**：提供資料を先に読み込み、資料で埋まらない項目だけを質問します。資料が充実しているほど対話は短くなります。
- **2つの実行モード**：対話モード（既定）と `--auto`（対話をスキップし入力資料のみから生成。不明点は `TBD`）。`--auto` は入力資料が1つも無いとエラーになります。
- **出力言語**：`work/pipeline-progress.json` の `options.output_language`（`en` 既定 / `ja`）で切替。入力そのものの言語は自由（日本語資料でも可）。

## 目的とエントリーポイント

**目的**：プロダクトビジョンから SLA/NFR までを検証駆動で設計し、最後に `/architect:define-requirements` へ引き渡す。

**エントリーポイント**：`/product:start`（オーケストレータ）または `/product:define-vision`（第1フェーズ単体）。

## 1. 最低限、用意すべきインプット

| インプット | 必須度 | 内容 | 無い場合 |
|-----------|--------|------|---------|
| プロダクトのアイデア / 一言説明（`target`） | 推奨（対話なら実質必須） | プロダクト名や「誰の・どんな課題を・どう解決するか」の一言 | 対話で引き出す（`--auto` では不可） |
| ビジネス概要資料（`--input=<file\|dir>`） | 推奨 | ビジネスブリーフ、RFP、議事録、既存資料。テキスト/Markdown/PDF。複数指定・ディレクトリ指定可 | 対話で補完 |
| 出力言語の指定（`--lang` または初期化時の選択） | 推奨 | `ja` / `en` | 対話で確認 |

> `--auto` で回す場合は、上記の「アイデア」または「`--input` 資料」の**少なくとも一方が必須**です。

## 2. 精度を上げる / 対話を短くする追加インプット

用意しておくと、そのフェーズでの質問が減り、`TBD` が減ります（無くても対話やWeb調査で補完されます）。

| 情報カテゴリ | 主に使うフェーズ | 具体例 |
|-------------|----------------|-------|
| ターゲット顧客・セグメント | define-vision / generate-persona | 誰向けか（「全員」は不可、必ずセグメント化される） |
| 解決したい課題・ジョブ（JTBD） | define-vision / generate-persona | 顧客が片付けたい用事、既存の代替手段 |
| 市場・競合の事実 | research-landscape / define-vision | 市場規模、競合名、代替品（無ければ引用付きWeb調査 or `TBD`） |
| 成功の定義・KPI | define-success-metrics | North Star候補、重視する指標 |
| 収益・ビジネスモデルの前提 | design-revenue | 課金モデル、価格帯、LTV/CAC等の前提値 |
| 制約条件（`--constraints=<file\|text>`） | define-scope | 技術・予算・スケジュール・法規制・既存資産 |
| デザインシステム（`--import=<path>`） | design-system | 既存の Tailwind / DTCG / Figma Tokens / CSS テーマ |
| SLA/可用性への顧客期待 | design-sla / define-nfr | 許容ダウンタイム、レイテンシ期待、RPO/RTO |

## 3. 実行途中で対話的に聞かれる主な項目

対話モードでは、各フェーズが不足情報をその都度確認します。代表的な確認ポイント：

- **ビジョン**：ターゲットグループ（セグメント化必須）、課題/ジョブ、便益、Go/No-Go 基準
- **検証ゲート（validate-assumptions）**：最もリスクの高い前提と、その検証結果（証拠が集まり次第、再実行可）。ここで `no-go` なら前段の見直しに戻る
- **スコープ**：やること/やらないこと（MoSCoW / RICE）
- **収益**：価格・CAC などの前提（事実ではなく「仮説」として検証ゲートへ送られる）

## 4. 最小構成（`--profile=mvp`）で最低限必要なもの

`vision + scope + validate` のみを回す最小プロファイル。**プロダクトのアイデア1行**があれば開始でき、あとは対話で成立します。

## 5. architect への連携（ハンドオフ）

`define-nfr` / `map-domains` / `design-api` などの成果物が揃うと、`/architect:define-requirements` にインプットとして引き渡せます。architect 側は product の成果物を自動検出し、再ヒアリングせず確認・拡張します。詳細は [architect-input-requirements_ja.md](architect-input-requirements_ja.md) の「product → architect の連携」節を参照してください。

## まとめ（最短で始めるには）

| やりたいこと | 起点コマンド | 最低限用意するもの |
|-------------|-------------|-------------------|
| プロダクト方向性を1から設計 | `/product:start` | プロダクトのアイデア1行 |
| 資料からまとめて生成（対話なし） | `/product:start --auto --input=<資料>` | ビジネス資料 最低1つ |
