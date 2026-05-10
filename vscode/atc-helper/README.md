# AtC Helper

VS Code extension for opening AtCoder contest terminals from `current-contest.json`.

## Local VSIX Install

```bash
npm install
npm run compile
npm install -g @vscode/vsce
vsce package
code --install-extension ./atc-helper-0.0.1.vsix
```

After installing the VSIX, reload VS Code. The extension will run in normal VS Code without using Extension Development Host.

The command `AtC: Open Contest Terminals` opens a split terminal group for the current contest. The extension also watches `.atc/current-contest.json` and opens the terminals when that file changes.
