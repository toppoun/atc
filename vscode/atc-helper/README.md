# AtC Helper

VS Code extension for opening AtCoder contest terminals from `current-contest.json`.

## Local VSIX Install

```bash
npm install
npm run compile
npm install -g @vscode/vsce
npx @vscode/vsce package --allow-missing-repository
code --install-extension ./atc-helper-0.0.1.vsix --force
```

Check the installed extension:

```bash
code --list-extensions --show-versions | findstr atc-helper
```

If `kouki.atc-helper@0.0.1` appears, the extension is installed. After installing the VSIX, reload VS Code. The extension will run in normal VS Code without using Extension Development Host.

## Updating After Changes

After changing the extension code, rebuild the VSIX and reinstall it:

```bash
npm install
npm run compile
npx @vscode/vsce package --allow-missing-repository
code --install-extension ./atc-helper-0.0.1.vsix --force
```

Then run `Developer: Reload Window` in VS Code. The `--force` flag overwrites the installed extension even when the version is still `0.0.1`.

The command `AtC: Open Contest Terminals` opens a split terminal group for the current contest. The extension also watches `.atc/current-contest.json` and opens the terminals when that file changes.
