import * as vscode from "vscode";

const CONTEST_GROUPS: Record<string, string> = {
  abc: "ABC(Atcoder Beginner Contest)",
  arc: "ARC(Atcoder Regular Contest)",
  agc: "AGC(Atcoder Grand Contest)"
};
const CONTEST_GROUP_NAMES = Object.values(CONTEST_GROUPS);

type CurrentContestResult =
  | { kind: "missing" }
  | { kind: "found"; contestDir: vscode.Uri; requestId?: string; source: vscode.Uri }
  | { kind: "invalid"; message: string };
type CurrentContestFileStatus = "missing" | "file" | "notFile";

type Utf8TextDecoder = new (label?: string) => { decode(input: Uint8Array): string };
type ConsoleLogger = { log(message?: unknown, ...optionalParams: unknown[]): void };

function decodeUtf8(bytes: Uint8Array): string {
  const TextDecoderCtor = (globalThis as unknown as { TextDecoder: Utf8TextDecoder }).TextDecoder;
  return new TextDecoderCtor("utf-8").decode(bytes);
}

function logMessage(message: string): void {
  (globalThis as unknown as { console: ConsoleLogger }).console.log(message);
}

function logCurrentContestLookup(uri: vscode.Uri): void {
  logMessage(`[atc-helper] looking for current contest: ${uri.fsPath}`);
}

function isAbsolutePath(input: string): boolean {
  return /^[A-Za-z]:[\\/]/.test(input) || input.startsWith("\\\\") || input.startsWith("/");
}

async function isDirectory(uri: vscode.Uri): Promise<boolean> {
  try {
    const stat = await vscode.workspace.fs.stat(uri);
    return stat.type === vscode.FileType.Directory;
  } catch {
    return false;
  }
}

async function getCurrentContestFileStatus(uri: vscode.Uri): Promise<CurrentContestFileStatus> {
  try {
    const stat = await vscode.workspace.fs.stat(uri);
    return stat.type === vscode.FileType.File ? "file" : "notFile";
  } catch {
    return "missing";
  }
}

function joinWorkspacePath(workspaceFolder: vscode.WorkspaceFolder, input: string): vscode.Uri {
  const segments = input.split(/[\\/]+/).filter(Boolean);
  return vscode.Uri.joinPath(workspaceFolder.uri, ...segments);
}

async function resolveContestDir(input: string): Promise<vscode.Uri | undefined> {
  if (isAbsolutePath(input)) {
    const uri = vscode.Uri.file(input);
    return (await isDirectory(uri)) ? uri : undefined;
  }

  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (!workspaceFolder) {
    return undefined;
  }

  const contestIdMatch = /^(abc|arc|agc)\d+$/i.exec(input);
  if (contestIdMatch) {
    const group = CONTEST_GROUPS[contestIdMatch[1].toLowerCase()];
    const contestGroupUri = vscode.Uri.joinPath(workspaceFolder.uri, group, input);
    if (await isDirectory(contestGroupUri)) {
      return contestGroupUri;
    }
  }

  const workspaceRelativeUri = joinWorkspacePath(workspaceFolder, input);
  return (await isDirectory(workspaceRelativeUri)) ? workspaceRelativeUri : undefined;
}

function currentContestUri(baseUri: vscode.Uri): vscode.Uri {
  return vscode.Uri.joinPath(baseUri, ".atc", "current-contest.json");
}

function pathSegments(uri: vscode.Uri): string[] {
  return uri.fsPath.split(/[\\/]+/).filter(Boolean);
}

function pushUniqueUri(uris: vscode.Uri[], seen: Set<string>, uri: vscode.Uri): void {
  const key = uri.toString();
  if (!seen.has(key)) {
    seen.add(key);
    uris.push(uri);
  }
}

function getLikelyAtcoderRootUris(): vscode.Uri[] {
  const workspaceFolders = vscode.workspace.workspaceFolders ?? [];
  const roots: vscode.Uri[] = [];
  const seen = new Set<string>();

  for (const workspaceFolder of workspaceFolders) {
    pushUniqueUri(roots, seen, workspaceFolder.uri);

    const segments = pathSegments(workspaceFolder.uri);
    const currentName = segments[segments.length - 1];
    const parentName = segments[segments.length - 2];

    if (currentName && CONTEST_GROUP_NAMES.includes(currentName)) {
      pushUniqueUri(roots, seen, vscode.Uri.joinPath(workspaceFolder.uri, ".."));
    }

    if (parentName && CONTEST_GROUP_NAMES.includes(parentName)) {
      pushUniqueUri(roots, seen, vscode.Uri.joinPath(workspaceFolder.uri, "..", ".."));
    }
  }

  return roots;
}

async function readDirectoryNames(uri: vscode.Uri): Promise<string[]> {
  try {
    const entries = await vscode.workspace.fs.readDirectory(uri);
    return entries
      .filter(([, type]) => type === vscode.FileType.Directory)
      .map(([name]) => name)
      .filter((name) => ![".git", ".venv", "node_modules"].includes(name));
  } catch {
    return [];
  }
}

async function getCurrentContestCandidates(): Promise<vscode.Uri[]> {
  const workspaceFolders = vscode.workspace.workspaceFolders ?? [];
  const candidates: vscode.Uri[] = [];
  const seen = new Set<string>();

  for (const rootUri of getLikelyAtcoderRootUris()) {
    pushUniqueUri(candidates, seen, currentContestUri(rootUri));
  }

  for (const workspaceFolder of workspaceFolders) {
    for (const group of CONTEST_GROUP_NAMES) {
      pushUniqueUri(candidates, seen, currentContestUri(vscode.Uri.joinPath(workspaceFolder.uri, group)));
    }

    const firstLevelNames = await readDirectoryNames(workspaceFolder.uri);
    for (const firstLevelName of firstLevelNames) {
      const firstLevelUri = vscode.Uri.joinPath(workspaceFolder.uri, firstLevelName);
      pushUniqueUri(candidates, seen, currentContestUri(firstLevelUri));

      const secondLevelNames = await readDirectoryNames(firstLevelUri);
      for (const secondLevelName of secondLevelNames) {
        const secondLevelUri = vscode.Uri.joinPath(firstLevelUri, secondLevelName);
        pushUniqueUri(candidates, seen, currentContestUri(secondLevelUri));
      }
    }
  }

  return candidates;
}

async function readCurrentContestFile(currentContestUri: vscode.Uri): Promise<CurrentContestResult> {
  const fileStatus = await getCurrentContestFileStatus(currentContestUri);
  if (fileStatus === "missing") {
    return { kind: "missing" };
  }
  if (fileStatus === "notFile") {
    return {
      kind: "invalid",
      message: `Current contest file is not a file: ${currentContestUri.fsPath}`
    };
  }

  let content: string;
  try {
    content = decodeUtf8(await vscode.workspace.fs.readFile(currentContestUri));
  } catch {
    return {
      kind: "invalid",
      message: `Failed to read current contest file: ${currentContestUri.fsPath}`
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch {
    return {
      kind: "invalid",
      message: `Invalid current contest JSON: ${currentContestUri.fsPath}`
    };
  }

  if (
    !parsed ||
    typeof parsed !== "object" ||
    typeof (parsed as { contestDir?: unknown }).contestDir !== "string" ||
    !(parsed as { contestDir: string }).contestDir.trim()
  ) {
    return {
      kind: "invalid",
      message: `current-contest.json must contain a contestDir string: ${currentContestUri.fsPath}`
    };
  }

  const contestDirInput = (parsed as { contestDir: string }).contestDir.trim();
  const contestDir = await resolveContestDir(contestDirInput);
  if (!contestDir) {
    return {
      kind: "invalid",
      message: `Contest directory not found from ${currentContestUri.fsPath}: ${contestDirInput}`
    };
  }

  const requestId = (parsed as { requestId?: unknown }).requestId;
  logMessage(`[atc-helper] current contest loaded: ${currentContestUri.fsPath}`);
  return {
    kind: "found",
    contestDir,
    requestId: typeof requestId === "string" ? requestId : undefined,
    source: currentContestUri
  };
}

async function readCurrentContestDir(): Promise<CurrentContestResult> {
  const candidates = await getCurrentContestCandidates();

  for (const currentContestUri of candidates) {
    logCurrentContestLookup(currentContestUri);

    const currentContest = await readCurrentContestFile(currentContestUri);
    if (currentContest.kind !== "missing") {
      return currentContest;
    }
  }

  return { kind: "missing" };
}

let lastWatchedRequestKey: string | undefined;

function currentContestRequestKey(currentContest: Extract<CurrentContestResult, { kind: "found" }>): string {
  return `${currentContest.source.toString()}::${currentContest.requestId ?? currentContest.contestDir.toString()}`;
}

async function openContestTerminals(contestDir: vscode.Uri): Promise<void> {
  const manualTerminal = vscode.window.createTerminal({
    name: "atc terminal",
    cwd: contestDir
  });
  manualTerminal.show();

  const watchTerminal = vscode.window.createTerminal({
    name: "atc watch",
    cwd: contestDir,
    location: {
      parentTerminal: manualTerminal
    }
  });
  watchTerminal.show();
  watchTerminal.sendText("atc watch");
}

async function openContestTerminalsFromCurrentContestOrInput(): Promise<void> {
  const currentContest = await readCurrentContestDir();
  if (currentContest.kind === "invalid") {
    vscode.window.showErrorMessage(currentContest.message);
    return;
  }

  let contestDir = currentContest.kind === "found" ? currentContest.contestDir : undefined;
  if (!contestDir) {
    const input = await vscode.window.showInputBox({
      prompt: "contestDir",
      placeHolder: "abc336 or D:\\atcoder\\ABC(Atcoder Beginner Contest)\\abc336",
      ignoreFocusOut: true
    });

    const contestDirInput = input?.trim();
    if (!contestDirInput) {
      return;
    }

    contestDir = await resolveContestDir(contestDirInput);
    if (!contestDir) {
      vscode.window.showErrorMessage(`Contest directory not found: ${contestDirInput}`);
      return;
    }
  }

  await openContestTerminals(contestDir);
}

async function openContestTerminalsFromWatchedFile(currentContestUri: vscode.Uri): Promise<void> {
  logMessage(`[atc-helper] current contest changed: ${currentContestUri.fsPath}`);

  const currentContest = await readCurrentContestFile(currentContestUri);
  if (currentContest.kind === "missing") {
    return;
  }
  if (currentContest.kind === "invalid") {
    vscode.window.showErrorMessage(currentContest.message);
    return;
  }

  const requestKey = currentContestRequestKey(currentContest);
  if (requestKey === lastWatchedRequestKey) {
    logMessage(`[atc-helper] current contest request already handled: ${requestKey}`);
    return;
  }

  lastWatchedRequestKey = requestKey;
  await openContestTerminals(currentContest.contestDir);
}

function registerCurrentContestWatchers(context: vscode.ExtensionContext): void {
  for (const rootUri of getLikelyAtcoderRootUris()) {
    const currentContest = currentContestUri(rootUri);
    logMessage(`[atc-helper] watching current contest: ${currentContest.fsPath}`);

    const watcher = vscode.workspace.createFileSystemWatcher(
      new vscode.RelativePattern(rootUri.fsPath, ".atc/current-contest.json")
    );
    const handleChange = (uri: vscode.Uri) => {
      void openContestTerminalsFromWatchedFile(uri);
    };

    watcher.onDidCreate(handleChange, undefined, context.subscriptions);
    watcher.onDidChange(handleChange, undefined, context.subscriptions);
    context.subscriptions.push(watcher);
  }
}

export function activate(context: vscode.ExtensionContext) {
  registerCurrentContestWatchers(context);

  const disposable = vscode.commands.registerCommand(
    "atc-helper.openContestTerminals",
    openContestTerminalsFromCurrentContestOrInput
  );

  context.subscriptions.push(disposable);
}

export function deactivate() {}
