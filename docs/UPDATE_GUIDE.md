# 更新ガイド

このリポジトリの正本は`Dockerfile`、`patches/`と検証手順です。上流Krokiの更新を最優先で評価し、独自パッチが不要なら削除する方針です。図形式を削ることを初期方針にはしません。

## 1. 情報収集

1. [Kroki Releases](https://github.com/yuzutech/kroki/releases)、[D2 Releases](https://github.com/terrastruct/d2/releases)、[Goat](https://github.com/blampe/goat)の更新を確認。
2. Java（Eclipse Temurin）、Go、Ubuntuのセキュリティ修正版を確認。
3. 更新候補の公式Krokiイメージを先にTrivyで検査し、修正済みの独自差分を洗い出す。
4. 各候補についてタグ・コミット・イメージDigest・検査日時を記録する。

## 2. 差分の更新

- 上流KrokiでJacksonやGuavaの修正版が使われていれば、`patches/kroki-server-pom.patch`を縮小または削除する。
- D2の修正版がすでに`golang.org/x/net`等を更新していれば、`patches/d2-go-mod.patch`を縮小または削除する。
- D2・Goatのビルドに使用するGoのパッチ版を見直す。`go.mod`の要求版とビルドに使用した版は別に確認する。
- 上流のタグを更新したら、正しいコミットSHAに合わせてDockerfileの照合値を更新する。
- ベースイメージのDigestと、Java・Go・Mavenイメージの固定方法を見直す。現状はすべてをDigest固定していない。
- Mermaidは別コンテナのため別途更新し、検査・描画試験が通ってから構成へ追加する。

パッチが適用できなくなったときに`git apply`の検査を迂回してはいけません。新しい上流ソースに合わせて差分の要否と内容を調べ直します。

## 3. ビルドと検証

```bash
./scripts/build.sh kroki-secure:review
docker run --rm -d --name kroki-review \
  -p 127.0.0.1:8001:8000 \
  -e KROKI_SAFE_MODE=secure kroki-secure:review
./scripts/smoke-test.sh http://127.0.0.1:8001
./scripts/scan.sh kroki-secure:review
docker rm -f kroki-review
```

※ 上のコマンドは空きポートとコンテナ名を確認してから実行します。`docker run --rm -d`は停止時に自動削除されるコンテナです。

- Mavenの`clean verify`とD2の`go test ./...`はDockerfile内で実行する。
- ヘルスチェックだけでは不十分なので、PlantUML、D2、GoatをSVGへ変換して確認する。
- TrivyのLOW/MEDIUMと`--ignore-unfixed`を外した結果も必要に応じて確認する。
- 検査の誤検出と実際の到達可能性は区別して記録する。

## 4. 採用判断・記録

採用前に固定SHA、イメージDigest、実際のビルドログ、テスト結果、Trivyのオプションと検出結果、既知の制約を日付入りの検証記録へ追記してください。既存利用環境の変更手順やロールバックは各運用環境側で管理し、この公開用リポジトリへ固有情報を書き込みません。

このリポジトリはビルド構成を公開するものであり、実行環境の更新やビルド済みコンテナの配布は対象外です。
