const fs = require("fs");
const path = require("path");

const extensionRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(extensionRoot, "..");
const sourceDir = path.join(repoRoot, "atc");
const targetDir = path.join(extensionRoot, "python", "atc");

function copyDirectory(source, target) {
  fs.rmSync(target, { recursive: true, force: true });
  fs.mkdirSync(target, { recursive: true });

  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (entry.name === "__pycache__" || entry.name === ".DS_Store") {
      continue;
    }

    const sourcePath = path.join(source, entry.name);
    const targetPath = path.join(target, entry.name);

    if (entry.isDirectory()) {
      copyDirectory(sourcePath, targetPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(sourcePath, targetPath);
    }
  }
}

if (!fs.existsSync(path.join(sourceDir, "cli.py"))) {
  throw new Error(`Python CLI が見つかりません: ${sourceDir}`);
}

copyDirectory(sourceDir, targetDir);
console.log(`Synced Python CLI to ${path.relative(repoRoot, targetDir)}`);
