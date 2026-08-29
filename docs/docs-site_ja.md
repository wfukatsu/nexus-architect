# 出力レポートをローカルのドキュメントサイトとして閲覧する

`tools/docs-site.sh` は、プロジェクトの `reports/` ツリーを [Blume](https://useblume.dev)
（Astro ベースの Markdown ファーストなドキュメントフレームワーク）で、検索・ナビゲーション付きの
サイトとして手元のマシンで配信します。外部へのアップロードはなく、`reports/` も一切変更しません。
サイトは実行のたびにレポートから作り直される **ステージ** です。

```bash
tools/docs-site.sh                 # カレントプロジェクトの reports/ を同期して dev サーバー起動
tools/docs-site.sh dev ~/proj      # 別プロジェクトのディレクトリを指定
tools/docs-site.sh build           # 静的サイトを tools/docs-site/dist/ に出力
tools/docs-site.sh validate        # ステージ内の内部リンクをすべて検証
tools/docs-site.sh clean           # 生成物を削除
```

オプション: `--port=N`、`--host`、`--open`、`--no-watch`（dev 時に `reports/` の変更を再同期しない）、
`--no-install`。`PROJECT_DIR` を省略すると、カレントディレクトリに `reports/` があればそこ、なければ
リポジトリルートが対象になります。初回実行時に Blume を `tools/docs-site/node_modules` へインストール
します（Node 22.12 以上が必要。生成ディレクトリはすべて git-ignore 済み）。

## サイトの内容

| 元 | 変換先 | 備考 |
|----|--------|------|
| `reports/**/*.md` | レポート 1 件 = 1 ページ。`/<dir>/<name>`（数字のフェーズ接頭辞は除去。`01_analysis/system-overview.md` → `/analysis/system-overview`） | Mermaid 図を描画。レポート自身のフロントマターはタイトル直下に表示し、`nexus` キーの下にも保持 |
| `reports/**/*.json`（マニフェスト、レビュー所見） | 同じルートのコードページ | |
| `reports/**/openapi/*.yaml` | Blume の OpenAPI リファレンス `/api/<service>` | オペレーションごとに 1 ページ、検索対象 |
| `reports/**/asyncapi/*.yaml` | Blume の AsyncAPI リファレンス `/events/<name>` | |
| `reports/00_summary/full-report.html` | `/full-report.html` としてそのまま配信 | |
| `work/pipeline-progress.json` | ランディングページ: オプション、全フェーズのステータスと出力へのリンク | |

レポート間リンク（`reports/03_design/context-map.md`、`../01_analysis/x.md#anchor`）はサイトの
ルートに書き換えます。サイトが配信できないプロジェクト内ファイルへのリンク（`samples/…/Order.java`、
`work/context.md`）はプレーンテキストになります。トップレベルディレクトリはパイプライン順の
サイドバーグループになり、その中のページはマニフェストの出力宣言順に並びます。

## 仕組み

`tools/docs-site/sync_reports.py` が各レポートを **MDX** に変換し（Blume が Mermaid を描画するのは
`.mdx` ページのみ）、MDX が誤って解釈する文字（式になる `{…}`、JSX タグになる裸の `<`）をエスケープ
します。コードフェンスとインラインコードはそのままです。`tools/docs-site/blume.config.ts` は
`nexus` フロントマターキーの宣言（Blume は未知のキーを拒否し、組み込みの `id`/`status` は ADR の
形と衝突する）と、同期でコピーされた仕様ファイルのマウントを担います。`blume validate` が報告する
のはレポート側で元から壊れているリンクで、典型的には `scalardb-schema.md#9.5` のような見出し ID に
存在しない節番号アンカーです。直すのはレポート側であってサイト側ではありません。
