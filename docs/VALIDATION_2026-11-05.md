# 初回検証記録（2026-11-05）

## 対象と根拠

特定のLinux AMD64 / WSL2 / Docker Engine環境で、元の公式イメージを段階的に更新して検証した記録。環境固有のホスト名、ユーザー名、ネットワーク構成、コンテナIDは記載しない。

**注意：** 以下のPASSは段階的に構築したローカルイメージの結果。公開リポジトリにまとめた`Dockerfile`のクリーンビルドと完全に同一条件で再試験した結果ではない。

## 固定した上流ソース

| 対象 | タグ | Commit |
| --- | --- | --- |
| Kroki | v0.34.0 | `2408475da7877125364abcd4c1c9fabf02a8756c` |
| D2 | v0.9.0 | `d5a51743b6d5c00f1ec6f8340003f5d5a6ba4eda` |
| Goat | v0.5.1 | `6d4db359c601eae6efa1fcd94601fa1793e114d5` |

Kroki公式イメージ`yuzutech/kroki:0.34.0`の取得Digest：`sha256:1314e60e6dd813cd00c90cb22007a05fdb92edf43259dfae71abbe89429ea36a`。

## 適用した更新

| 分類 | 更新 |
| --- | --- |
| Kroki | 0.27.0 → 0.34.0 |
| Java | Temurin 17.0.14 → 21.0.13+9 |
| Ubuntu | 24.04のAPT更新 |
| Jackson Databind | 2.22.2 → 2.22.3 |
| Guava | 33.6.0-jre → 33.7.2-jre |
| D2 | 0.7.1 → 0.9.0のソースで再ビルド |
| D2の`golang.org/x/net` | 0.57.0 → 0.60.0 |
| Goat | v0.5.1をGo 1.27.3で再ビルド |
| ビルド用Go | 1.27.3 |

D2の`go get`および`go mod tidy`で`x/sync`、`x/sys`、`x/term`、`x/text`、`x/tools`も更新。Mavenは`clean verify`成功。D2の`go test ./...`はリリース用試験に`jq`が必要で、追加後の全テストPASSを確認した。

## 脆弱性検査（当時の結果）

Trivy`--severity HIGH,CRITICAL --ignore-unfixed`を使用。初期レポートの検出総数は58件（Ubuntu 6、Kroki JAR 3、D2 37、Goat 12）。段階的に更新した最終イメージでは、それぞれ0件になった。

これは検査日時とオプションに依存した結果。全CVEが存在しないこと、未修正CVEがないこと、実際に脆弱なコード経路がないこと、下位レイヤーに古いファイルがないことを意味しない。

## 実行時検証

- `/health` がHTTP 200
- PlantUML → SVG成功
- D2 → SVG成功
- Goat → SVG成功
- Windows側のエディタからのPlantUML表示を確認
- Java `21.0.13+9`で起動
- `KROKI_SAFE_MODE=secure`とループバックへのポート公開を使用

D2のコマンド`d2 --version`は`v0.8.1-HEAD`と表示された。ソースGit SHAはv0.9.0タグと一致しており、バージョン文字列の埋め込みは今後の確認事項。Mermaidの動作試験は実施していない。

## 公開用構成の未検証箇所

- 統合Dockerfileのクリーンビルド（独立環境での再現）
- ARM64、Mermaid、LOW/MEDIUMおよび修正版なしの検査
- ベースイメージ下位レイヤーを含む完全なクリーン再ビルド
