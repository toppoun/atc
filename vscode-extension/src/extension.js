const childProcess = require("child_process");
const fs = require("fs");
const path = require("path");
const vscode = require("vscode");

const VIEW_TYPE = "atc-helper.main";

function activate(context) {
  const provider = new AtcViewProvider(context);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(VIEW_TYPE, provider),
    vscode.commands.registerCommand("atc.openPanel", async () => {
      await vscode.commands.executeCommand(`${VIEW_TYPE}.focus`);
    })
  );
}

function deactivate() {}

class AtcViewProvider {
  constructor(context) {
    this.context = context;
    this.view = undefined;
    this.currentProcess = undefined;
    this.currentBaseDirectory = context.workspaceState.get("baseDirectory");
    this.currentContestName = context.workspaceState.get("contestName", "");
    this.contestNameSaveQueue = Promise.resolve();
  }

  resolveWebviewView(webviewView) {
    this.view = webviewView;
    webviewView.webview.options = {
      enableScripts: true
    };
    webviewView.webview.html = this.getHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(async (message) => {
      try {
        await this.handleMessage(message);
      } catch (error) {
        this.appendLog(error instanceof Error ? error.message : String(error), "error");
        this.setRunning(false);
      }
    });
  }

  async handleMessage(message) {
    switch (message.type) {
      case "ready":
        this.postWorkspace();
        break;
      case "setBaseDirectory":
        await this.setBaseDirectory(message.value);
        break;
      case "refreshDirectories":
        this.postWorkspace();
        break;
      case "setContestName":
        await this.setContestName(message.value);
        break;
      case "createContest":
        await this.createContest(message);
        break;
      case "runProblem":
        await this.runProblem(message);
        break;
      case "manualCreate":
        await this.manualCreate(message);
        break;
      case "chooseDirectory":
        await this.chooseDirectory(message.target);
        break;
      case "clearOutput":
        this.post({ type: "clearOutput" });
        break;
      case "stop":
        this.stopCurrentProcess();
        break;
      default:
        break;
    }
  }

  async createContest(message) {
    const contest = normalizeContestName(message.contest);
    const lang = message.lang === "py" ? "py" : "cpp";
    const baseDirectory = this.getBaseDirectory();

    if (!baseDirectory) {
      throw new Error("VS Code で作業フォルダを開いてください。");
    }
    if (!contest) {
      throw new Error("コンテスト名を入力してください。");
    }

    await this.setContestName(contest);
    const code = await this.runAtc(["new", contest, lang], baseDirectory);
    if (code === 0) {
      this.post({ type: "contestCreated", contest });
    }
  }

  async runProblem(message) {
    const problem = normalizeToken(message.problem).toUpperCase();
    const contest = normalizeContestName(message.contest);
    const interpreter = message.interpreter === "pypy" ? "pypy" : "python";

    if (!problem) {
      throw new Error("問題を選択してください。");
    }
    if (!contest) {
      throw new Error("コンテスト名を入力してください。");
    }

    await this.setContestName(contest);
    const cwd = this.resolveWorkingDirectory(contest);
    if (!fs.existsSync(cwd)) {
      throw new Error(`作業フォルダが見つかりません: ${cwd}`);
    }

    await this.runAtc(["run", problem, interpreter], cwd);
  }

  async manualCreate(message) {
    const lang = message.lang === "py" ? "py" : "cpp";
    const targets = String(message.targets || "")
      .split(/[\s,]+/)
      .map((target) => target.trim().toUpperCase())
      .filter(Boolean);
    const cwd = this.resolveWorkingDirectory(message.directory);

    if (!targets.length) {
      throw new Error("作成する問題を入力してください。");
    }
    if (!fs.existsSync(cwd)) {
      throw new Error(`作業フォルダが見つかりません: ${cwd}`);
    }

    await this.runAtc(["manual", ...targets, lang], cwd);
  }

  async chooseDirectory(target) {
    const defaultDirectory = target === "baseDir" ? this.getWorkspaceRoot() : this.getBaseDirectory();
    const result = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      defaultUri: defaultDirectory ? vscode.Uri.file(defaultDirectory) : undefined,
      openLabel: "このフォルダを使う"
    });

    if (!result || result.length === 0) {
      return;
    }

    const selectedPath = result[0].fsPath;
    if (target === "baseDir") {
      this.currentBaseDirectory = selectedPath;
      await this.context.workspaceState.update("baseDirectory", selectedPath);
      this.postWorkspace();
      return;
    }

    const baseDirectory = this.getBaseDirectory();
    this.post({
      type: "setDirectory",
      target,
      value: baseDirectory ? toWorkspaceRelative(baseDirectory, selectedPath) : selectedPath
    });
  }

  async runAtc(args, cwd) {
    if (this.currentProcess) {
      throw new Error("別の処理が実行中です。完了してからもう一度実行してください。");
    }

    const command = this.resolveAtcCommand(args);
    const isTestRun = args[0] === "run";
    if (isTestRun) {
      this.post({ type: "clearTestResults" });
    }
    this.setRunning(true);
    this.appendLog(`$ ${quoteCommand(command.executable, command.args)}\n作業フォルダ: ${cwd}\n`, "info");

    return new Promise((resolve) => {
      const child = childProcess.spawn(command.executable, command.args, {
        cwd,
        env: command.env,
        shell: false
      });

      this.currentProcess = child;
      let finished = false;
      let capturedOutput = "";

      const finish = (code) => {
        if (finished) {
          return;
        }
        finished = true;
        if (isTestRun) {
          this.post({
            type: "testResults",
            results: parseTestOutput(capturedOutput, code)
          });
        }
        this.currentProcess = undefined;
        this.appendLog(`\n終了コード: ${code}`, code === 0 ? "info" : "error");
        this.setRunning(false);
        resolve(code);
      };

      child.stdout.on("data", (chunk) => {
        const text = stripAnsi(chunk.toString());
        capturedOutput += text;
        this.appendLog(text, "stdout");
      });
      child.stderr.on("data", (chunk) => {
        const text = stripAnsi(chunk.toString());
        capturedOutput += text;
        this.appendLog(text, "stderr");
      });
      child.on("error", (error) => {
        const text = `起動できませんでした: ${error.message}`;
        capturedOutput += text;
        this.appendLog(text, "error");
        finish(1);
      });
      child.on("close", (code) => {
        finish(code);
      });
    });
  }

  resolveAtcCommand(args) {
    const config = vscode.workspace.getConfiguration("atcHelper");
    const configuredCliPath = String(config.get("cliPath") || "").trim();
    const pythonPath = String(config.get("pythonPath") || "python3").trim() || "python3";

    if (configuredCliPath) {
      return {
        executable: configuredCliPath,
        args,
        env: process.env
      };
    }

    const moduleRoot = this.findLocalPythonModuleRoot();
    if (moduleRoot) {
      return {
        executable: pythonPath,
        args: ["-m", "atc.cli", ...args],
        env: {
          ...process.env,
          PYTHONPATH: prependPath(moduleRoot, process.env.PYTHONPATH)
        }
      };
    }

    return {
      executable: "atc",
      args,
      env: process.env
    };
  }

  findLocalPythonModuleRoot() {
    const extensionPath = this.context.extensionUri.fsPath;
    const candidates = [
      path.resolve(extensionPath, ".."),
      path.resolve(extensionPath, "python")
    ];

    return candidates.find((candidate) => {
      return fs.existsSync(path.join(candidate, "atc", "cli.py"));
    });
  }

  resolveWorkingDirectory(input) {
    const baseDirectory = this.getBaseDirectory();
    const value = String(input || "").trim();

    if (!baseDirectory) {
      throw new Error("VS Code で作業フォルダを開いてください。");
    }
    if (!value) {
      return baseDirectory;
    }
    if (path.isAbsolute(value)) {
      return value;
    }

    return path.join(baseDirectory, value);
  }

  getWorkspaceRoot() {
    const activeEditor = vscode.window.activeTextEditor;
    if (activeEditor) {
      const folder = vscode.workspace.getWorkspaceFolder(activeEditor.document.uri);
      if (folder) {
        return folder.uri.fsPath;
      }
    }

    const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    return folder ? folder.uri.fsPath : undefined;
  }

  getBaseDirectory() {
    const workspaceRoot = this.getWorkspaceRoot();
    if (!workspaceRoot) {
      return undefined;
    }
    if (this.currentBaseDirectory && fs.existsSync(this.currentBaseDirectory)) {
      return this.currentBaseDirectory;
    }

    return workspaceRoot;
  }

  async setBaseDirectory(value) {
    const workspaceRoot = this.getWorkspaceRoot();
    if (!workspaceRoot) {
      throw new Error("VS Code で作業フォルダを開いてください。");
    }

    const rawValue = String(value || "").trim();
    this.currentBaseDirectory = rawValue
      ? (path.isAbsolute(rawValue) ? rawValue : path.join(workspaceRoot, rawValue))
      : workspaceRoot;
    await this.context.workspaceState.update("baseDirectory", this.currentBaseDirectory);
    this.postWorkspace();
  }

  async setContestName(value) {
    this.currentContestName = normalizeContestName(value);
    this.contestNameSaveQueue = this.contestNameSaveQueue.then(() => {
      return this.context.workspaceState.update("contestName", this.currentContestName);
    });
    await this.contestNameSaveQueue;
    this.post({
      type: "contestName",
      value: this.currentContestName
    });
  }

  listWorkspaceDirectories() {
    const workspaceRoot = this.getWorkspaceRoot();
    if (!workspaceRoot) {
      return [];
    }

    const ignored = new Set([".git", ".vscode", "__pycache__", "node_modules", "dist", "build"]);
    try {
      return fs.readdirSync(workspaceRoot, { withFileTypes: true })
        .filter((entry) => entry.isDirectory() && !ignored.has(entry.name))
        .map((entry) => {
          const fullPath = path.join(workspaceRoot, entry.name);
          return {
            label: entry.name,
            value: entry.name,
            path: fullPath
          };
        })
        .sort((a, b) => a.label.localeCompare(b.label, "ja"));
    } catch {
      return [];
    }
  }

  stopCurrentProcess() {
    if (!this.currentProcess) {
      return;
    }

    this.currentProcess.kill();
    this.appendLog("\n処理を停止しました。", "error");
  }

  postWorkspace() {
    const root = this.getWorkspaceRoot();
    const baseDirectory = this.getBaseDirectory();
    this.post({
      type: "workspace",
      root: root || "",
      rootLabel: root || "未選択",
      baseDirectory: baseDirectory || "",
      baseLabel: root && baseDirectory ? toWorkspaceRelative(root, baseDirectory) || "." : "未選択",
      contestName: this.currentContestName || "",
      directories: this.listWorkspaceDirectories()
    });
  }

  appendLog(text, stream) {
    this.post({
      type: "appendOutput",
      text,
      stream
    });
  }

  setRunning(value) {
    this.post({
      type: "running",
      value
    });
  }

  post(message) {
    if (this.view) {
      this.view.webview.postMessage(message);
    }
  }

  getHtml(webview) {
    const nonce = getNonce();
    const workspaceRoot = this.getWorkspaceRoot() || "未選択";

    return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ATC Helper</title>
  <style>
    :root {
      color-scheme: light dark;
    }
    body {
      margin: 0;
      padding: 14px;
      color: var(--vscode-foreground);
      background: var(--vscode-sideBar-background);
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
    }
    main {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    section {
      border: 1px solid var(--vscode-sideBarSectionHeader-border);
      border-radius: 6px;
      padding: 12px;
      background: var(--vscode-editor-background);
    }
    .section-title {
      margin: 0 0 10px;
      font-weight: 700;
    }
    .workspace {
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .workspace-meta {
      display: grid;
      gap: 4px;
      margin-bottom: 10px;
    }
    .workspace-label {
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
    }
    .compact-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 8px;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 5px;
      margin: 10px 0;
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
    }
    input,
    select,
    button {
      box-sizing: border-box;
      width: 100%;
      min-height: 28px;
      border-radius: 4px;
      font: inherit;
    }
    input,
    select {
      border: 1px solid var(--vscode-input-border, transparent);
      color: var(--vscode-input-foreground);
      background: var(--vscode-input-background);
      padding: 4px 7px;
    }
    button {
      border: 1px solid var(--vscode-button-border, transparent);
      color: var(--vscode-button-foreground);
      background: var(--vscode-button-background);
      padding: 5px 8px;
      cursor: pointer;
    }
    button.secondary {
      color: var(--vscode-button-secondaryForeground);
      background: var(--vscode-button-secondaryBackground);
    }
    button:hover {
      background: var(--vscode-button-hoverBackground);
    }
    button.secondary:hover {
      background: var(--vscode-button-secondaryHoverBackground);
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.6;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 74px;
      gap: 8px;
      align-items: end;
    }
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .quick-run-grid {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 6px;
      margin: 10px 0;
    }
    .quick-run {
      min-width: 0;
      min-height: 34px;
      padding: 5px 0;
      font-weight: 700;
    }
    .primary-actions {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      margin: 10px 0;
    }
    .output {
      min-height: 180px;
      max-height: 320px;
      overflow: auto;
      padding: 10px;
      border-radius: 6px;
      border: 1px solid var(--vscode-panel-border);
      color: var(--vscode-terminal-foreground, var(--vscode-foreground));
      background: var(--vscode-terminal-background, var(--vscode-editor-background));
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: var(--vscode-editor-font-family);
      font-size: var(--vscode-editor-font-size);
    }
    .status {
      min-height: 18px;
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
    }
    .hidden {
      display: none;
    }
    .test-summary {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
      margin-bottom: 10px;
      padding: 8px;
      border-radius: 6px;
      border: 1px solid var(--vscode-panel-border);
      background: var(--vscode-sideBar-background);
    }
    .summary-main {
      font-weight: 700;
    }
    .summary-sub {
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
    }
    .summary-score {
      font-family: var(--vscode-editor-font-family);
      font-size: 16px;
      font-weight: 700;
    }
    .test-cases {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .case-card {
      border: 1px solid var(--vscode-panel-border);
      border-left-width: 4px;
      border-radius: 6px;
      overflow: hidden;
      background: var(--vscode-editor-background);
    }
    .case-card.ac {
      border-left-color: var(--vscode-testing-iconPassed, #2ea043);
    }
    .case-card.wa {
      border-left-color: var(--vscode-testing-iconFailed, #f85149);
    }
    .case-card.re,
    .case-card.ce,
    .case-card.unknown {
      border-left-color: var(--vscode-testing-iconErrored, #d29922);
    }
    .case-head {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 8px;
      align-items: center;
      padding: 8px;
    }
    .case-name {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 700;
    }
    .case-time {
      color: var(--vscode-descriptionForeground);
      font-family: var(--vscode-editor-font-family);
      font-size: 12px;
    }
    .badge {
      min-width: 34px;
      padding: 2px 6px;
      border: 1px solid currentColor;
      border-radius: 999px;
      text-align: center;
      font-size: 11px;
      font-weight: 700;
      line-height: 16px;
    }
    .badge.ac {
      color: var(--vscode-testing-iconPassed, #2ea043);
    }
    .badge.wa {
      color: var(--vscode-testing-iconFailed, #f85149);
    }
    .badge.re,
    .badge.ce,
    .badge.unknown {
      color: var(--vscode-testing-iconErrored, #d29922);
    }
    .case-detail {
      display: grid;
      gap: 8px;
      padding: 0 8px 8px;
    }
    .diff-grid {
      display: grid;
      gap: 8px;
    }
    .diff-title {
      margin-bottom: 4px;
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
      font-weight: 700;
    }
    .case-pre {
      max-height: 180px;
      margin: 0;
      overflow: auto;
      padding: 8px;
      border: 1px solid var(--vscode-panel-border);
      border-radius: 4px;
      background: var(--vscode-textCodeBlock-background, var(--vscode-sideBar-background));
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: var(--vscode-editor-font-family);
      font-size: var(--vscode-editor-font-size);
    }
    .empty-results {
      color: var(--vscode-descriptionForeground);
      font-size: 12px;
    }
  </style>
</head>
<body>
  <main>
    <section>
      <div class="section-title">作業場所</div>
      <div class="workspace-meta">
        <div class="workspace-label">VS Code</div>
        <div class="workspace" id="workspaceRoot">${escapeHtml(workspaceRoot)}</div>
      </div>
      <label>
        基準フォルダ
        <select id="baseDir"></select>
      </label>
      <div class="workspace" id="baseDirLabel">.</div>
      <div class="compact-actions">
        <button class="secondary" id="chooseBaseDir">選択</button>
        <button class="secondary" id="refreshDirs">更新</button>
      </div>
    </section>

    <section>
      <div class="section-title">コンテスト</div>
      <label>
        コンテスト名
        <input id="contestName" autocomplete="off" placeholder="abc413">
      </label>
      <label>
        言語
        <select id="newLang">
          <option value="cpp">C++</option>
          <option value="py">Python</option>
        </select>
      </label>
      <label>
        問題
        <select id="problem">
          <option>A</option>
          <option>B</option>
          <option>C</option>
          <option>D</option>
          <option>E</option>
          <option>F</option>
        </select>
      </label>
      <label>
        Python 実行
        <select id="interpreter">
          <option value="python">Python</option>
          <option value="pypy">PyPy</option>
        </select>
      </label>
      <div class="primary-actions">
        <button id="createContest">作成</button>
        <button id="runProblem">テストケース実行</button>
      </div>
      <div class="quick-run-grid" aria-label="問題別クイック実行">
        <button class="quick-run" data-problem="A">A</button>
        <button class="quick-run" data-problem="B">B</button>
        <button class="quick-run" data-problem="C">C</button>
        <button class="quick-run" data-problem="D">D</button>
        <button class="quick-run" data-problem="E">E</button>
        <button class="quick-run" data-problem="F">F</button>
      </div>
    </section>

    <section id="testResultsSection" class="hidden">
      <div class="section-title">テスト結果</div>
      <div class="test-summary" id="testSummary"></div>
      <div class="test-cases" id="testCases"></div>
    </section>

    <section>
      <div class="section-title">手動作成</div>
      <div class="row">
        <label>
          作業フォルダ
          <input id="manualDir" autocomplete="off" placeholder="abc413 または空欄">
        </label>
        <button class="secondary choose-dir" data-target="manualDir">選択</button>
      </div>
      <label>
        問題
        <input id="manualTargets" autocomplete="off" placeholder="A B C / A-E">
      </label>
      <label>
        言語
        <select id="manualLang">
          <option value="cpp">C++</option>
          <option value="py">Python</option>
        </select>
      </label>
      <button id="manualCreate">ファイル作成</button>
    </section>

    <section>
      <div class="section-title">詳細ログ</div>
      <div class="status" id="status">待機中</div>
      <pre class="output" id="output"></pre>
      <div class="actions">
        <button class="secondary" id="clearOutput">クリア</button>
        <button class="secondary" id="stopProcess" disabled>停止</button>
      </div>
    </section>
  </main>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const $ = (id) => document.getElementById(id);
    const output = $("output");
    const status = $("status");
    const baseDir = $("baseDir");
    const contestName = $("contestName");
    const testResultsSection = $("testResultsSection");
    const testSummary = $("testSummary");
    const testCases = $("testCases");
    const buttons = [
      $("createContest"),
      $("runProblem"),
      $("manualCreate"),
      ...document.querySelectorAll(".quick-run")
    ];

    vscode.postMessage({ type: "ready" });

    $("createContest").addEventListener("click", () => {
      vscode.postMessage({
        type: "createContest",
        contest: contestName.value,
        lang: $("newLang").value
      });
    });

    contestName.addEventListener("input", () => {
      vscode.postMessage({
        type: "setContestName",
        value: contestName.value
      });
    });

    baseDir.addEventListener("change", () => {
      vscode.postMessage({
        type: "setBaseDirectory",
        value: baseDir.value
      });
    });

    $("chooseBaseDir").addEventListener("click", () => {
      vscode.postMessage({
        type: "chooseDirectory",
        target: "baseDir"
      });
    });

    $("refreshDirs").addEventListener("click", () => {
      vscode.postMessage({ type: "refreshDirectories" });
    });

    $("runProblem").addEventListener("click", () => {
      runSelectedProblem($("problem").value);
    });

    document.querySelectorAll(".quick-run").forEach((button) => {
      button.addEventListener("click", () => {
        $("problem").value = button.dataset.problem;
        runSelectedProblem(button.dataset.problem);
      });
    });

    function runSelectedProblem(problem) {
      clearTestResults();
      vscode.postMessage({
        type: "runProblem",
        contest: contestName.value,
        problem,
        interpreter: $("interpreter").value
      });
    }

    $("manualCreate").addEventListener("click", () => {
      vscode.postMessage({
        type: "manualCreate",
        directory: $("manualDir").value,
        targets: $("manualTargets").value,
        lang: $("manualLang").value
      });
    });

    document.querySelectorAll(".choose-dir").forEach((button) => {
      button.addEventListener("click", () => {
        vscode.postMessage({
          type: "chooseDirectory",
          target: button.dataset.target
        });
      });
    });

    $("clearOutput").addEventListener("click", () => {
      vscode.postMessage({ type: "clearOutput" });
    });

    $("stopProcess").addEventListener("click", () => {
      vscode.postMessage({ type: "stop" });
    });

    window.addEventListener("message", (event) => {
      const message = event.data;
      switch (message.type) {
        case "workspace":
          renderWorkspace(message);
          setContestName(message.contestName);
          break;
        case "contestName":
          setContestName(message.value);
          break;
        case "appendOutput":
          output.textContent += message.text;
          output.scrollTop = output.scrollHeight;
          break;
        case "clearOutput":
          output.textContent = "";
          clearTestResults();
          break;
        case "clearTestResults":
          clearTestResults();
          break;
        case "testResults":
          renderTestResults(message.results);
          break;
        case "running":
          buttons.forEach((button) => {
            button.disabled = message.value;
          });
          $("stopProcess").disabled = !message.value;
          status.textContent = message.value ? "実行中" : "待機中";
          break;
        case "contestCreated":
          setContestName(message.contest);
          $("manualDir").value = message.contest;
          break;
        case "setDirectory":
          if ($(message.target)) {
            $(message.target).value = message.value;
          }
          break;
        default:
          break;
      }
    });

    function renderWorkspace(message) {
      $("workspaceRoot").textContent = message.rootLabel || "未選択";
      $("baseDirLabel").textContent = "現在: " + (message.baseLabel || ".");

      const current = message.baseDirectory || "";
      const root = message.root || "";
      const options = message.directories || [];
      const selectedDirectory = options.find((directory) => directory.path === current);
      baseDir.replaceChildren();
      baseDir.append(createOption("", "ワークスペース直下"));

      options.forEach((directory) => {
        baseDir.append(createOption(directory.value, directory.label));
      });

      if (current && current !== root && !selectedDirectory) {
        const label = message.baseLabel || current;
        baseDir.append(createOption(current, label));
      }

      baseDir.value = selectedDirectory ? selectedDirectory.value : (current && current !== root ? current : "");
    }

    function setContestName(value) {
      if (document.activeElement !== contestName) {
        contestName.value = value || "";
      }
    }

    function createOption(value, label) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      return option;
    }

    function clearTestResults() {
      testSummary.replaceChildren();
      testCases.replaceChildren();
      testResultsSection.classList.add("hidden");
    }

    function renderTestResults(results) {
      clearTestResults();
      testResultsSection.classList.remove("hidden");

      const summaryText = results.summary
        ? results.summary.text
        : (results.exitCode === 0 ? "テスト実行が完了しました" : "テスト実行でエラーが発生しました");
      const subText = results.cases.length
        ? results.cases.map((item) => item.status).join(" / ")
        : "詳細ログを確認してください";

      const summaryMain = document.createElement("div");
      const summaryTitle = document.createElement("div");
      const summarySub = document.createElement("div");
      const summaryScore = document.createElement("div");
      summaryTitle.className = "summary-main";
      summarySub.className = "summary-sub";
      summaryScore.className = "summary-score";
      summaryTitle.textContent = summaryText;
      summarySub.textContent = subText;
      summaryScore.textContent = results.summary ? results.summary.score : statusLabel(results.exitCode === 0 ? "AC" : "RE");
      summaryMain.append(summaryTitle, summarySub);
      testSummary.append(summaryMain, summaryScore);

      if (!results.cases.length) {
        const empty = document.createElement("div");
        empty.className = "empty-results";
        empty.textContent = results.error || "テストケースを読み取れませんでした。";
        testCases.append(empty);
        return;
      }

      results.cases.forEach((testCase) => {
        testCases.append(createCaseCard(testCase));
      });
    }

    function createCaseCard(testCase) {
      const status = String(testCase.status || "UNKNOWN").toLowerCase();
      const card = document.createElement("article");
      const head = document.createElement("div");
      const badge = document.createElement("span");
      const name = document.createElement("div");
      const time = document.createElement("div");
      card.className = "case-card " + status;
      head.className = "case-head";
      badge.className = "badge " + status;
      name.className = "case-name";
      time.className = "case-time";
      badge.textContent = statusLabel(testCase.status);
      name.textContent = testCase.name;
      time.textContent = testCase.timeMs ? testCase.timeMs + " ms" : "";
      head.append(badge, name, time);
      card.append(head);

      if (testCase.expected || testCase.output || testCase.detail) {
        const detail = document.createElement("div");
        detail.className = "case-detail";
        if (testCase.expected || testCase.output) {
          const diff = document.createElement("div");
          diff.className = "diff-grid";
          diff.append(
            createPreBlock("期待値", testCase.expected || ""),
            createPreBlock("出力", testCase.output || "")
          );
          detail.append(diff);
        }
        if (testCase.detail) {
          detail.append(createPreBlock("詳細", testCase.detail));
        }
        card.append(detail);
      }

      return card;
    }

    function createPreBlock(title, value) {
      const wrapper = document.createElement("div");
      const heading = document.createElement("div");
      const pre = document.createElement("pre");
      heading.className = "diff-title";
      pre.className = "case-pre";
      heading.textContent = title;
      pre.textContent = value || "(空)";
      wrapper.append(heading, pre);
      return wrapper;
    }

    function statusLabel(value) {
      const labels = {
        AC: "AC",
        WA: "WA",
        RE: "RE",
        CE: "CE",
        UNKNOWN: "?"
      };
      return labels[value] || labels.UNKNOWN;
    }
  </script>
</body>
</html>`;
  }
}

function normalizeToken(value) {
  return String(value || "").trim().replace(/[^A-Za-z0-9_-]/g, "");
}

function normalizeContestName(value) {
  return normalizeToken(value).toLowerCase();
}

function stripAnsi(value) {
  return value.replace(/\x1b\[[0-9;]*m/g, "");
}

function parseTestOutput(value, exitCode) {
  const text = String(value || "").replace(/\r\n/g, "\n");
  const cases = [];
  const matches = [...text.matchAll(/^===\s*(.*?)\s*===\s*$/gm)];

  for (let index = 0; index < matches.length; index += 1) {
    const match = matches[index];
    const next = matches[index + 1];
    const bodyStart = match.index + match[0].length;
    const bodyEnd = next ? next.index : text.length;
    cases.push(parseTestCase(match[1], text.slice(bodyStart, bodyEnd)));
  }

  const summaryMatch = text.match(/結果:\s*(\d+)\/(\d+)\s*AC/);
  const summary = summaryMatch
    ? {
        accepted: Number(summaryMatch[1]),
        total: Number(summaryMatch[2]),
        score: `${summaryMatch[1]}/${summaryMatch[2]}`,
        text: `結果: ${summaryMatch[1]}/${summaryMatch[2]} AC`
      }
    : undefined;

  return {
    exitCode,
    summary,
    cases,
    error: cases.length ? "" : extractRunError(text)
  };
}

function parseTestCase(name, body) {
  const statusMatch = body.match(/^\s*(AC|WA|RE|CE)\b/m);
  const timeMatch = body.match(/time:\s*([0-9.]+)\s*ms/i);
  const status = statusMatch ? statusMatch[1] : "UNKNOWN";

  return {
    name,
    status,
    timeMs: timeMatch ? timeMatch[1] : "",
    expected: status === "WA" ? extractBetween(body, "expected:", "output:") : "",
    output: status === "WA" ? extractBetween(body, "output:", "time:") : "",
    detail: status === "RE" ? cleanDetail(body) : ""
  };
}

function extractBetween(value, startLabel, endLabel) {
  const start = value.indexOf(startLabel);
  if (start === -1) {
    return "";
  }

  const contentStart = start + startLabel.length;
  const end = value.indexOf(endLabel, contentStart);
  return value.slice(contentStart, end === -1 ? value.length : end).trim();
}

function cleanDetail(value) {
  return value
    .split("\n")
    .filter((line) => !/^\s*(RE|time:\s*[0-9.]+\s*ms)\s*$/i.test(line))
    .join("\n")
    .trim();
}

function extractRunError(value) {
  const lines = value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const ceIndex = lines.findIndex((line) => line === "CE");
  if (ceIndex !== -1) {
    return ["CE", ...lines.slice(ceIndex + 1)].join("\n");
  }

  return lines.slice(-12).join("\n");
}

function prependPath(value, existing) {
  return existing ? `${value}${path.delimiter}${existing}` : value;
}

function quoteCommand(executable, args) {
  return [executable, ...args].map((part) => {
    return /\s/.test(part) ? `"${part.replace(/"/g, '\\"')}"` : part;
  }).join(" ");
}

function toWorkspaceRelative(workspaceRoot, selectedPath) {
  const relative = path.relative(workspaceRoot, selectedPath);
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative)) {
    return selectedPath;
  }

  return relative;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getNonce() {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let nonce = "";
  for (let i = 0; i < 32; i += 1) {
    nonce += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return nonce;
}

module.exports = {
  activate,
  deactivate
};
