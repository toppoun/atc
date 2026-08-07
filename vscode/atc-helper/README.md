# AtC Helper

VS Code extension for opening AtCoder contest terminals from `current-contest.json`.

Requires VS Code 1.93 or later.

## Local VSIX Install

```bash
npm ci
npm run compile
npm run package -- --out ./atc-helper.vsix
code --install-extension ./atc-helper.vsix --force
```

Check the installed extension:

```bash
code --list-extensions --show-versions | findstr atc-helper
```

If `kouki.atc-helper@0.0.1` appears, the extension is installed. After installing the VSIX, reload VS Code. The extension will run in normal VS Code without using Extension Development Host.

## Updating After Changes

After changing the extension code, rebuild the VSIX and reinstall it:

```bash
npm ci
npm run compile
npm run package -- --out ./atc-helper.vsix
code --install-extension ./atc-helper.vsix --force
```

Then run `Developer: Reload Window` in VS Code. The `--force` flag overwrites the installed extension even when the version is still `0.0.1`.

The command `AtC: Open Contest Terminals` ensures a split terminal group for the current contest. The extension also watches `.atc/current-contest.json` and reuses its managed terminals when that file changes. When switching contests, Terminal Shell Integration synchronizes stopping and restarting `atc watch`; if shell integration is unavailable, only the managed watch terminal is recreated.
