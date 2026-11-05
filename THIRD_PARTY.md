# 上流OSSと配布について

このリポジトリに含めるのは、独自に記述したビルド構成・最小限の差分パッチ・検証手順のみです。Kroki、D2、Goat、Java、Goのソース全文、実行ファイル、コンテナイメージは格納・再配布しません。

- [Kroki](https://github.com/yuzutech/kroki) — 上流のライセンス、NOTICE、依存コンポーネントの条件を確認してください。
- [D2](https://github.com/terrastruct/d2) — 上流のライセンスと付随する依存の条件を確認してください。
- [Goat](https://github.com/blampe/goat) — 上流のライセンスを確認してください。
- [Eclipse Temurin](https://adoptium.net/) — Java配布物には固有のライセンス条件があります。
- [Go](https://go.dev/) — Goのライセンス条件を確認してください。

Dockerfileが指定するイメージや依存ライブラリは、利用者のビルド時に取得されます。利用・組織内配布・成果物の再配布には、上流のライセンスと通知要件が引き続き適用されます。

このリポジトリ独自部分のライセンスは公開前に決定する必要があります。GitHubでPublicにすること自体は、第三者への再利用許諾とは同義ではありません。
