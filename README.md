# Kroki security build recipe

Krokiの公式コンテナイメージを基点に、確認時点で必要だった依存関係の更新を追加する非公式ビルド構成です。Dockerfile、パッチ、検証手順のみを管理し、ビルド済みのコンテナイメージ・JAR・実行ファイルは配布しません。

**Unofficial build recipe for Kroki.** It provides source-pinned build instructions and verification scripts, not prebuilt images or a guarantee of security.

## 保守・サポートについて

このリポジトリは、継続的な保守、セキュリティ更新、利用者サポートを約束するものではありません。作者自身の利用環境で必要になった場合に更新することがありますが、更新頻度や将来の対応は保証しません。

IssueやPull Requestへの対応も保証しません。このリポジトリを利用する場合は、上流Krokiや依存コンポーネントの更新、脆弱性情報、各自の利用環境への適合性を利用者自身で確認してください。

## 対象と方針

- 公式 `yuzutech/kroki:0.37.1`（Linux AMD64）をDigestで固定します。コンテナ内はUbuntu 26.04、Temurin 21.0.13.1+2です。WSLのUbuntu 24.04は更新不要です。
- 上流のD2・TikZ・Bytefield修正を維持します。D2を再ビルドするときは、依存更新と一緒にKroki上流のファイルアクセス制限パッチを適用します。
- 独自差分は、Kroki JARのGuava `33.8.0-jre` と、D2の `golang.org/x/net v0.62.0` および関連モジュールの更新です。Java、Jackson、Goatは上流の版を使います。
- APTの一括更新、開発パッケージの削除、フラット化は既定ビルドでは行いません。APTの修正要否は新しいベースをスキャンして判断します。
- ポート公開は `127.0.0.1` に限定し、`KROKI_SAFE_MODE=secure` を使います。

## 前提

- LinuxまたはWSL2のDocker Engine（Linux AMD64）、BuildKit
- ビルド元イメージ、GitHub、Maven、Goモジュールを取得できるネットワーク
- ホストの `bash` と、検証用の `curl`

ホストへのJava・Go・Mavenのインストールは不要です。

## ビルドと確認

既存のコンテナを止めず、新しいタグと空いているローカルポートで試します。

```bash
git clone https://github.com/skysht3/kroki-security-build-recipe.git
cd kroki-security-build-recipe

./scripts/build.sh kroki-secure:0.37.1
docker run -d --name kroki-review --restart no \
  -p 127.0.0.1:8001:8000 \
  -e KROKI_SAFE_MODE=secure \
  kroki-secure:0.37.1

# 起動後、HealthとPlantUML・D2・GoatのSVG変換を確認
./scripts/smoke-test.sh http://127.0.0.1:8001
docker exec kroki-review java -version
docker exec kroki-review d2 --version

mkdir -p reports
./scripts/scan.sh kroki-secure:0.37.1 --format json > reports/trivy-full.json
./scripts/scan.sh kroki-secure:0.37.1 \
  --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1

# 検証用コンテナだけを終了・削除
docker stop kroki-review
docker rm kroki-review
```

`build.sh [イメージタグ]` はパッチの適用可否、タグとソースSHAの一致を確認してから、Mavenの `clean verify`、D2の `go mod verify` と `go test ./...` を含むビルドを実行します。出力は1タグで、既存タグの上書きは拒否します。やり直す場合は新しいタグを指定してください。

`scan.sh` はTrivyをコンテナで実行します。Dockerソケットの読み取り専用マウントにも強い権限があるため、信頼できるTrivyイメージだけを使ってください。

組織の環境へ持ち込む前に、利用する図形式・フォント・出力形式を上記に追加して確認してください。判定・切り戻し手順は[更新ガイド](docs/UPDATE_GUIDE.md)、検証の実施状況は[0.37.1の検証記録](docs/VALIDATION_2026-11-26.md)を参照してください。

## 構成

| パス | 内容 |
| --- | --- |
| `Dockerfile` | 公式0.37.1ベースにGuava更新済みJARとD2を組み込む |
| `patches/kroki-server-pom.patch` | Kroki JARのGuavaを更新 |
| `patches/d2-go-mod.patch` | D2の `golang.org/x/net` と関連モジュールを更新 |
| `scripts/build.sh` | Linux AMD64向けのビルド |
| `scripts/smoke-test.sh` | Health・PlantUML・D2・GoatのSVG変換 |
| `scripts/scan.sh` | Trivyによる脆弱性検査 |
| `scripts/flatten-image.py` | 旧レシピのフラット化ツール。現在のビルドでは呼び出さない |
| `docs/UPDATE_GUIDE.md` | 上流確認・再ビルド・採用判断 |
| `docs/VALIDATION_2026-11-26.md` | 0.37.1ベースの検証記録 |
| `docs/VALIDATION_2026-11-05.md` | 0.34.0ベースの過去の検証記録 |
| `docs/SECURITY_NOTES.md` / `docs/READINESS.md` | 前提と既知の制約 |
| `THIRD_PARTY.md` | 上流OSS・再配布の留意点 |

## ライセンス

このリポジトリの独自部分は、明示した例外を除きMIT Licenseで提供します。詳細は[LICENSE](LICENSE)と[THIRD_PARTY.md](THIRD_PARTY.md)を参照してください。

`patches/d2-go-mod.patch`はD2 v0.9.0のMPL-2.0対象ファイルへの修正を含むため、Mozilla Public License 2.0 (MPL-2.0)で提供します。MPL-2.0本文は[LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt)に含めています。

上流Kroki、D2、Goat、Eclipse Temurin、Goおよびビルド時に取得される依存コンポーネントには、それぞれの上流ライセンスが適用されます。

## 対応範囲

Linux AMD64向けのビルドレシピのみを提供します。ARM64、全描画形式、Mermaidなどの別コンテナは対象外です。検証時点や未実施の項目は[既知の制約](docs/READINESS.md)に記載しています。
