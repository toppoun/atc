# Development

開発者向けメモです。

## 構成

```text
.
├── atc/
│   ├── cli.py
│   └── templates/
│       ├── template.py
│       └── template.cpp
├── vscode/
│   └── atc-helper/
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           └── extension.ts
├── docs/
├── install.sh
├── update.sh
├── uninstall.sh
├── pyproject.toml
└── README.md
```

- Python CLI: `atc/cli.py`
- VS Code 拡張機能: `vscode/atc-helper/`
- 標準テンプレート: `atc/templates/`
- 実行時作業ディレクトリ: `.atc/`

## Python CLI

ローカルインストール:

```bash
python3 -m pip install -e .
```

構文チェック:

```bash
python -m compileall atc
```

wheel 作成確認:

```bash
python -m pip wheel . --no-deps --no-build-isolation -w dist
```

## VS Code 拡張機能

```bash
cd vscode/atc-helper
npm install
npm run compile
npx @vscode/vsce package --allow-missing-repository
```

ローカルインストール:

```bash
code --install-extension ./atc-helper-0.0.1.vsix --force
```

インストール後は `Developer: Reload Window` を実行してください。

## VSIX

Marketplace 公開はまだしません。ローカル VSIX インストールで利用します。

## package-data / templates

`pyproject.toml` で `atc/templates/template.py` と `atc/templates/template.cpp` を package-data に含めています。

これにより `pip install .` でも標準テンプレートが入ります。

## 確認すること

変更後は最低限これを確認します。

```bash
python -m compileall atc

cd vscode/atc-helper
npm run compile
```

可能なら wheel にテンプレートが入ることも確認します。

```bash
python -m pip wheel . --no-deps --no-build-isolation -w dist
```

## ブランチ例

```bash
git switch -c feature/your-feature-name
```

Python CLI と VS Code 拡張機能は別々に確認してください。

## 注意

- `.atc/` は実行時に生成される作業ディレクトリです
- `vscode/atc-helper/out/` は TypeScript compile の出力です
- `node_modules/` や生成された `.vsix` は通常 commit 対象ではありません
- 既存ユーザーの contest フォルダや config を壊さないようにしてください
