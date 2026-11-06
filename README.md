# Kroki security-maintained build recipe

Krokiの公式コンテナイメージを基点に、確認時点で必要だった依存関係の更新を追加する非公式ビルド構成です。Dockerfile、パッチ、検証手順のみを管理し、ビルド済みのコンテナイメージ・JAR・実行ファイルは配布しません。

**Unofficial build recipe for Kroki.** It provides source-pinned build instructions and verification scripts, not prebuilt images or a guarantee of security.

## 対象と方針

- Kroki 0.34.0をベースに、既存の図形式を削除せず更新する
- Temurin 21.0.13+9へJava実行環境を差し替える
- Ubuntu 24.04のAPTパッケージをビルド時に更新する
- Kroki JARのJackson Databind / Guavaを修正版に更新し、Mavenで再ビルドする
- D2 v0.9.0とGoat v0.5.1をGo 1.27.3でビルドし、D2の依存モジュールも更新する
- D2の`golang.org/x/net v0.62.0`を維持する
- 開発用パッケージを除去した後、`docker export/import`で最終イメージをフラット化する
- HTTP公開を`127.0.0.1`に限定し、`KROKI_SAFE_MODE=secure`を維持する

ソースのコミットSHAと依存バージョンは`Dockerfile`と`patches/`に記録しています。リリース時点の固定構成なので、後日そのまま安全であることを保証するものではありません。

## 前提

- Linux/WSL2上のDocker EngineとDocker Build
- Linux AMD64（初版で確認した構成。ARM64は未検証）
- イメージ・Maven・Goモジュールを取得できるネットワーク
- ホスト上の`bash`とPython 3、検証用の`curl`

ホストOSへJava・Go・Mavenを直接インストールする必要はありません。

## ビルドと確認

```bash
git clone https://github.com/skysht3/kroki-secure-build.git
cd kroki-secure-build

./scripts/build.sh
docker run -d --name kroki-example --restart no \
  -p 127.0.0.1:8001:8000 \
  -e KROKI_SAFE_MODE=secure \
  kroki-secure:0.34.0-flat

# 起動後、/healthに応答する状態で実行する
./scripts/smoke-test.sh http://127.0.0.1:8001
mkdir -p reports
# 全重大度。未修正の検出も含める
./scripts/scan.sh kroki-secure:0.34.0-flat --format json > reports/trivy-full.json
# 修正版ありHIGH/CRITICALがあれば非0で終了する
./scripts/scan.sh kroki-secure:0.34.0-flat \
  --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1

# 検証用コンテナを不要になったときだけ削除
docker rm -f kroki-example
```

ビルドでは上流リポジトリをタグで取得した後、コミットSHAが指定値に一致することを検査します。
依存更新パッチを適用し、Mavenの`clean verify`とD2の`go mod verify`、`go test ./...`を含むステージからイメージを生成します。
BuildKitキャッシュが有効なら、これらのステージを再利用します。

`build.sh [最終タグ [フラット化前タグ]]`は、既定で`kroki-secure:0.34.0-flat-layered`を構築し、その後`kroki-secure:0.34.0-flat`を生成します。
両タグをローカルに残し、サイズと設定を比較できるようにします。
既存タグの上書きを拒否するため、再ビルド時は新しいタグ（例：`./scripts/build.sh kroki-secure:review-2`）を指定してください。
同じ出力タグを使うビルドを並行実行しないでください。
Dockerfileのみのビルドでは、フラット化前のイメージが生成されます。

`build-essential`、`gcc`、`g++`、`libc6-dev`、`linux-libc-dev`をAPTの依存関係に従って除去します。
削除予定に想定外の実行時パッケージが含まれていればビルドを中止し、`autoremove`は実行しません。
全開発用パッケージの網羅的な除去は行わず、その他の自動削除候補は残します。

フラット化は元イメージの`Config`からEnv、Entrypoint、Cmd、User、WorkingDir、ExposedPorts、Labels、StopSignalを復元し、生成後に照合します。
コンテナ作成時の設定を転記せず、元にないWorkingDirなどを追加しません。
Volumes、Healthcheck、OnBuild、Shell、legacyのArgsEscapedなど、保持を保証できない設定があれば明示的に失敗します。
中間コンテナは正常終了、エラー、SIGINT/SIGTERMの際に削除します。
ホスト停止やSIGKILLなど、プロセスが後片付けを実行できない終了は対象外です。

2026-11-05の実機検証では、既存の4,610,324,304 bytesから3,791,946,711 bytesへ削減しました（約818MB、17.75%）。
設定の一致と4件のスモークテストを確認しています。
検証条件、Trivyの残存検出、再実行コマンドは[検証記録](docs/VALIDATION_2026-11-05.md#正式な軽量化手順の実機検証)を参照してください。

`scripts/scan.sh`はTrivyをコンテナで実行し、既定では全重大度を検査します。
追加のTrivyオプションはイメージ名の後に指定できます。
Dockerソケットの読み取り専用マウントでも強い権限が残るため、使用するTrivyイメージを信頼できるものに限定してください。
`reports/`、イメージアーカイブ、ビルドログはGit管理から除外します。

## 構成

| パス | 内容 |
| --- | --- |
| `Dockerfile` | Kroki・D2・Goatのソース取得、依存修正、ビルド、最終イメージ生成 |
| `patches/kroki-server-pom.patch` | Jackson・Guavaの推移的依存を明示的に上書き |
| `patches/d2-go-mod.patch` | D2の`golang.org/x/net`と関連モジュールを更新 |
| `scripts/build.sh` | パッケージ除去を含むLinux AMD64ビルドとフラット化 |
| `scripts/flatten-image.py` | 設定を照合し、ローカルの新規タグへexport/import |
| `scripts/test_flatten_image.py` | 設定保持と失敗時処理の回帰テスト |
| `scripts/smoke-test.sh` | Health・PlantUML・D2・GoatのSVG変換 |
| `scripts/scan.sh` | Trivyによる全重大度検査と指定条件での評価 |
| `docs/VALIDATION_2026-11-05.md` | 初回の実機検証記録 |
| `docs/UPDATE_GUIDE.md` | 公式更新と独自差分の見直し手順 |
| `docs/SECURITY_NOTES.md` | 検査範囲、制約、既知の残課題 |
| `THIRD_PARTY.md` | 上流OSS・再配布の留意点 |

## ライセンス

このリポジトリの独自部分は、明示した例外を除きMIT Licenseで提供します。詳細は[LICENSE](LICENSE)と[THIRD_PARTY.md](THIRD_PARTY.md)を参照してください。

`patches/d2-go-mod.patch`はD2 v0.9.0のMPL-2.0対象ファイルへの修正を含むため、Mozilla Public License 2.0 (MPL-2.0)で提供します。MPL-2.0本文は[LICENSES/MPL-2.0.txt](LICENSES/MPL-2.0.txt)に含めています。

上流Kroki、D2、Goat、Eclipse Temurin、Goおよびビルド時に取得される依存コンポーネントには、それぞれの上流ライセンスが適用されます。

## 未対応・制約

- Mermaidは上流の別コンテナを使用する構成が必要で、初回検証には含まれていません。既存のKrokiコンテナ単体で利用可能とは扱いません。
- フラット化前のイメージには旧ファイルの下位レイヤーが残ります。最終版では現在のファイルシステムを1レイヤーへまとめますが、上流イメージの全ソフトウェアを再ビルドする構成ではありません。
- フラット化により元のレイヤー履歴、ビルド由来のattestation、署名は引き継ぎません。イメージIDも変わります。
- APTの`upgrade`は実行時点のリポジトリ状態に依存します。すべてのベースイメージはDigest固定済みではありません。
- Linux AMD64で統合手順を検証済みです。キャッシュを使わない新規環境でのビルドと、全描画形式の動作は未検証です。

公式への不具合報告・修正の代わりになるものではありません。更新時は`docs/UPDATE_GUIDE.md`を参照してください。
