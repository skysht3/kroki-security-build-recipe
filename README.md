# Kroki security-maintained build recipe

Krokiの公式コンテナイメージを基点に、確認時点で必要だった依存関係の更新を追加する非公式ビルド構成です。Dockerfile、パッチ、検証手順のみを管理し、ビルド済みのコンテナイメージ・JAR・実行ファイルは配布しません。

**Unofficial build recipe for Kroki.** It provides source-pinned build instructions and verification scripts, not prebuilt images or a guarantee of security.

## 対象と方針

- Kroki 0.34.0をベースに、既存の図形式を削除せず更新する
- Temurin 21.0.13+9へJava実行環境を差し替える
- Ubuntu 24.04のAPTパッケージをビルド時に更新する
- Kroki JARのJackson Databind / Guavaを修正版に更新し、Mavenで再ビルドする
- D2 v0.9.0とGoat v0.5.1をGo 1.27.3でビルドし、D2の依存モジュールも更新する
- HTTP公開を`127.0.0.1`に限定し、`KROKI_SAFE_MODE=secure`を維持する

ソースのコミットSHAと依存バージョンは`Dockerfile`と`patches/`に記録しています。リリース時点の固定構成なので、後日そのまま安全であることを保証するものではありません。

## 前提

- Linux/WSL2上のDocker EngineとDocker Build
- Linux AMD64（初版で確認した構成。ARM64は未検証）
- イメージ・Maven・Goモジュールを取得できるネットワーク
- 検証用に`curl`、`bash`、脆弱性検査用にDockerを利用可能であること

ホストOSへJava・Go・Mavenを直接インストールする必要はありません。

## ビルドと確認

```bash
git clone https://github.com/skysht3/kroki-secure-build.git
cd kroki-secure-build

./scripts/build.sh
docker run -d --name kroki-example --restart no \
  -p 127.0.0.1:8001:8000 \
  -e KROKI_SAFE_MODE=secure \
  kroki-secure:0.34.0-local

./scripts/smoke-test.sh http://127.0.0.1:8001
./scripts/scan.sh kroki-secure:0.34.0-local

# 検証用コンテナを不要になったときだけ削除
docker rm -f kroki-example
```

ビルドでは上流リポジトリをタグで取得した後、コミットSHAが指定値に一致することを検査します。依存更新パッチを適用し、Mavenの`clean verify`とD2の`go test ./...`を実行してから最終イメージを生成します。新しい環境からの一括ビルドは、この公開用構成ではまだ完走確認していません。

`scripts/scan.sh`はTrivyをコンテナで実行します。Dockerソケットの読み取り専用マウントでも強い権限が残るため、使用するTrivyイメージを信頼できるものに限定してください。検出0件は「HIGH/CRITICALかつ修正可能な既知CVE」に限ります。

## 構成

| パス | 内容 |
| --- | --- |
| `Dockerfile` | Kroki・D2・Goatのソース取得、依存修正、ビルド、最終イメージ生成 |
| `patches/kroki-server-pom.patch` | Jackson・Guavaの推移的依存を明示的に上書き |
| `patches/d2-go-mod.patch` | D2の`golang.org/x/net`と関連モジュールを更新 |
| `scripts/build.sh` | Linux AMD64イメージ生成 |
| `scripts/smoke-test.sh` | Health・PlantUML・D2・GoatのSVG変換 |
| `scripts/scan.sh` | Trivyによる条件付き脆弱性検査 |
| `docs/VALIDATION_2026-11-05.md` | 初回の実機検証記録 |
| `docs/UPDATE_GUIDE.md` | 公式更新と独自差分の見直し手順 |
| `docs/SECURITY_NOTES.md` | 検査範囲、制約、既知の残課題 |
| `THIRD_PARTY.md` | 上流OSS・再配布の留意点 |

## 未対応・制約

- Mermaidは上流の別コンテナを使用する構成が必要で、初回検証には含まれていません。既存のKrokiコンテナ単体で利用可能とは扱いません。
- JavaやGoバイナリの差し替えは上位レイヤーで行うため、公式ベースイメージの旧ファイルは下位レイヤーに残ります。完全なクリーンビルドではありません。
- APTの`upgrade`は実行時点のリポジトリ状態に依存します。すべてのベースイメージはDigest固定済みではありません。
- 初回検証は特定のローカル環境での記録です。このリポジトリの統合Dockerfileを別の環境で再現した結果ではありません。
- 公開前に、このリポジトリ独自部分の配布ライセンスを決定してください。上流のライセンスは別途適用されます。

公式への不具合報告・修正の代わりになるものではありません。更新時は`docs/UPDATE_GUIDE.md`を参照してください。
