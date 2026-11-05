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

## 個人環境での再現確認（2026-11-05）

- 公開用統合Dockerfileでクリーンビルド成功（Go 1.27.3）。
- Health、PlantUML、D2、Goatのスモーク試験は全件PASSと報告。
- TrivyのHIGH/CRITICALかつ修正版ありの検出はUbuntu、Kroki JAR、D2、Goatの4対象で0件。
- 全重大度検査では未修正扱いの検出が多数あり、D2のx/net v0.60.0に対するUNKNOWNの修正可能な検出2件が判明。
- D2 v0.9.0ソースでx/net v0.62.0と関連モジュールを更新し、Go 1.27.3でgo test ./...全件PASS。
- **この時点では、更新パッチを組み込んだ最終イメージの再ビルドと全重大度再検査は未実施。**

## 初回記録時点の未検証箇所

- 更新したD2パッチを含む統合Dockerfileの再ビルドとスモーク試験
- ARM64、Mermaidの動作試験、全重大度の検出結果に対する影響評価
- ベースイメージ下位レイヤーを含む完全なクリーン再ビルド

以下に正式な軽量化手順の検証を記録します。
上記の未検証状態のうち、更新したD2パッチを含む統合ビルドと最終イメージのスモーク試験、全重大度検査は実施済みです。

## 正式な軽量化手順の実機検証

Linux AMD64、Docker Engine 29.9.3で`./scripts/build.sh`を実行し、正常終了を確認しました。
既存のBuildKitキャッシュを利用しており、Mavenの`clean verify`とD2の`go mod verify`、`go test ./...`を含むステージはキャッシュから再利用しました。
この検証でそれらのテストをキャッシュなしで再実行したという意味ではありません。
Kroki、D2、GoatのタグとコミットSHA照合、パッチ適用検査はDockerfileに維持しています。
生成イメージのアップロードは行っていません。

### サイズと設定

値は`docker image inspect`の`Size`であり、レジストリ上の圧縮転送サイズではありません。

| 対象 | ローカルタグ | bytes |
| --- | --- | ---: |
| 既存の動作確認済み版 | `kroki-secure:0.34.0-local` | 4,610,324,304 |
| 正式ビルド、開発用パッケージ除去後 | `kroki-secure:0.34.0-flat-layered` | 4,607,247,884 |
| 正式なフラット化版 | `kroki-secure:0.34.0-flat` | 3,791,946,711 |

既存版から818,377,593 bytes（約818MB、17.75%）削減しました。
フラット化前後のレイヤー数は37から1へ減少しました。
既存の`local`、`slim-test`、`flat-test`タグは上書きしていません。
同じ出力タグでの`build.sh`再実行は、ビルド開始前に非0で終了することを確認しました。

フラット化前後の`Config`はJSONとして完全一致しました。
Env 26件、Labels 7件、Entrypoint、`User=kroki`、`8000/tcp`を保持しています。
元のイメージにないCmd、WorkingDir、Healthcheck、Volumes、StopSignalなどは追加していません。
OSとArchitectureも`linux/amd64`で一致しました。

### パッケージと描画機能

指定した`build-essential`、`gcc`、`g++`、`libc6-dev`、`linux-libc-dev`と、APTが依存削除すると判断したパッケージの計35件を除去しました。
インストール済みパッケージ数は418から383となり、追加パッケージはありませんでした。
削除予定をシミュレーションし、開発パッケージ、G++、GObject introspection以外の削除が予定された場合はビルドを止めます。
実行時共有ライブラリの削除はありませんでした。
`autoremove`は実行しておらず、その他の自動削除候補は残しています。
指定5パッケージの不在と、`dpkg --audit`の出力が空であることを最終イメージで確認しました。

| 試験 | 結果 |
| --- | --- |
| `/health` | PASS |
| PlantUML → SVG | PASS |
| D2 → SVG | PASS |
| Goat → SVG | PASS |

元のイメージにある`KROKI_*_BIN_PATH`の全17パスについて、最終版でも実行可能であることを確認しました。
これらの描画プログラム、Kroki JAR、Goat、`/etc/kroki`内の設定ファイルの計20エントリでSHA-256が一致しました。
同じ比較はフラット化前後でも一致しています。
Dockerfileやパッチに描画形式を削除する変更は加えていません。
これは静的な保持確認であり、全描画形式の動作試験ではありません。

### Trivy

Trivy 0.76.1を使用しました。
実行したスキャナーイメージのDigestは`sha256:790fd66d1697395d8693d1acaa1ea702406a20f109b6fc7bac8db623eca6c06c`です。
脆弱性DBの更新日時は2026-11-05 07:00:54 UTC、Java DBは同日01:08:50 UTCでした。
全重大度検査は`--scanners vuln --format json`を指定し、`--ignore-unfixed`は指定していません。

| 対象 | UNKNOWN | LOW | MEDIUM | HIGH | CRITICAL |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ubuntu 24.04 | 0 | 80 | 98 | 0 | 0 |
| Kroki JAR | 0 | 0 | 0 | 0 | 0 |
| D2 | 0 | 0 | 0 | 0 | 0 |
| Goat | 0 | 0 | 0 | 0 | 0 |

D2のパッケージ情報から`golang.org/x/net v0.62.0`を確認しました。
修正版ありHIGH/CRITICALについては、`--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`でも0件、終了コード0を確認しました。
残る178件の個別の攻撃到達可能性、誤検出、受容可否は未評価です。
HIGH/CRITICALが0件という結果を、全CVEの解消やHumanによるRisk受容と同一視しません。
スキャナーやDBの更新で結果は変化します。

### 設定保持と失敗時処理の回帰テスト

`scripts/test_flatten_image.py`の14テストがPASSしました。
このうち1件はDocker実機を使い、Env内の空文字、`$`、引用符、バックスラッシュ、Cmd、WorkingDir、User、ポート、Labels、StopSignalの保持を確認しています。
VolumesとHealthcheckを持つイメージ、開発用パッケージが残るイメージ、既存タグへの出力は拒否されました。
その他のテストでは、未知の設定、export失敗後の部分的import、import失敗、設定不一致、中断、後片付け失敗を非0の失敗として扱うことを確認しました。
正常終了時と拒否時の一時コンテナ削除も確認しています。

### 再実行コマンド

出力タグが未使用であることを前提に、次を実行します。
生成物はGit除外済みの`reports/`に保存します。

```bash
./scripts/build.sh kroki-secure:review-2

docker image inspect kroki-secure:review-2-layered kroki-secure:review-2 \
  --format '{{.Size}} {{json .Config}}'

# フラット化前後の設定差分。何も出力されなければ一致
diff -u \
  <(docker image inspect kroki-secure:review-2-layered --format '{{json .Config}}' | python3 -m json.tool --sort-keys) \
  <(docker image inspect kroki-secure:review-2 --format '{{json .Config}}' | python3 -m json.tool --sort-keys)

docker run --rm --entrypoint /bin/sh kroki-secure:review-2 -ec '
  for package in build-essential gcc g++ libc6-dev linux-libc-dev; do
    status=$(dpkg-query -W -f="${Status}" "$package" 2>/dev/null || true)
    case "$status" in *"ok installed") echo "FAIL: $package"; exit 1;; esac
  done
  dpkg --audit
'

# 空きポートとコンテナ名を確認し、起動後/healthへ応答する状態で試験する
docker run --rm -d --name kroki-review-2 \
  -p 127.0.0.1:8001:8000 kroki-secure:review-2
./scripts/smoke-test.sh http://127.0.0.1:8001
docker rm -f kroki-review-2

mkdir -p reports
./scripts/scan.sh kroki-secure:review-2 --format json > reports/trivy-full.json
./scripts/scan.sh kroki-secure:review-2 \
  --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1

python3 -m unittest discover -s scripts -p 'test_*.py' -v
KROKI_DOCKER_TESTS=1 python3 -m unittest discover -s scripts -p 'test_*.py' -v
bash -n scripts/build.sh scripts/scan.sh scripts/smoke-test.sh
git diff --check
```

同一の出力タグを使った並行ビルドは対象外です。
`SIGKILL`やホスト停止など、プロセスが後片付けできない終了も対象外です。
フラット化はビルド履歴やattestationを保持せず、export/importの実行日時などにより同じイメージIDの再生成は保証しません。
未検証事項はARM64、全描画形式、キャッシュを無効化した新規環境での一括ビルド、残存CVEの個別評価です。
