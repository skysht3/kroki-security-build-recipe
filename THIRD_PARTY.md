# 上流OSSと配布について

このリポジトリに含めるのは、独自に記述したビルド構成・差分パッチ・検証手順のみです。Kroki、D2、Goat、Java、Goのソース全文、実行ファイル、コンテナイメージは格納・再配布しません。

## このリポジトリのライセンス

- このリポジトリの独自部分は、明示した例外を除き[MIT License](LICENSE)で提供します。
- `patches/d2-go-mod.patch`は、MPL-2.0で提供されるD2 v0.9.0の`go.mod`に対する修正を含むため、**Mozilla Public License 2.0 (MPL-2.0)**で提供します。ライセンス本文は[LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt)を参照してください。
- `patches/kroki-server-pom.patch`はMIT Licenseで提供されるKrokiへの差分であり、このリポジトリではMIT Licenseの範囲として扱います。

## 主な上流OSS

- [Kroki v0.34.0](https://github.com/yuzutech/kroki) — MIT License。
- [D2 v0.9.0](https://github.com/d2lang/d2) — Mozilla Public License 2.0 (MPL-2.0)。
- [Goat v0.5.1](https://github.com/blampe/goat) — MIT License。
- [Eclipse Temurin](https://adoptium.net/) — Java配布物にはEclipse Adoptium / OpenJDK等の各ライセンス条件が適用されます。
- [Go](https://go.dev/) — Go配布物にはGoプロジェクトのライセンス条件が適用されます。

Dockerfileが指定するイメージや依存ライブラリは、利用者のビルド時に取得されます。利用・組織内配布・成果物の再配布には、それぞれの上流ライセンス、NOTICE、依存コンポーネントの条件が引き続き適用されます。

特にMPL-2.0対象の`patches/d2-go-mod.patch`を再配布・変更する場合は、MPL-2.0のSource Code Formに関する条件を維持してください。このリポジトリはビルド済みD2バイナリを配布せず、D2の上流ソースと当該パッチから利用者がビルドする構成です。
