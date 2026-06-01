"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const DEFAULT_PATHS = {
    root: ""
};
const DEFAULT_CONTEST_PATH_RULES = {
    "abc\\d+": "ABC",
    "arc\\d+": "ARC",
    "agc\\d+": "AGC",
    "adt_.*": "ATD"
};
const CONFIG_FILE_NAME = "config.toml";
const reportedConfigErrors = new Set();
let lastWatchedRequestKey;
function decodeUtf8(bytes) {
    const TextDecoderCtor = globalThis.TextDecoder;
    return new TextDecoderCtor("utf-8").decode(bytes);
}
function logMessage(message) {
    globalThis.console.log(message);
}
function logCurrentContestLookup(uri) {
    logMessage(`[atc-helper] looking for current contest: ${uri.fsPath}`);
}
function homeDir() {
    const processLike = globalThis.process;
    return processLike?.env?.HOME || processLike?.env?.USERPROFILE;
}
function isAbsolutePath(input) {
    return /^[A-Za-z]:[\\/]/.test(input) || input.startsWith("\\\\") || input.startsWith("/");
}
function expandHomePath(input) {
    const home = homeDir();
    if (!home) {
        return input;
    }
    if (input === "~") {
        return home;
    }
    if (input.startsWith("~/") || input.startsWith("~\\")) {
        return `${home}${input.slice(1)}`;
    }
    return input;
}
function splitPathInput(input) {
    return input.split(/[\\/]+/).filter((segment) => segment && segment !== ".");
}
function joinUriPath(baseUri, input) {
    const segments = splitPathInput(input);
    return segments.length ? vscode.Uri.joinPath(baseUri, ...segments) : baseUri;
}
function parentUri(uri) {
    const parent = vscode.Uri.joinPath(uri, "..");
    return parent.fsPath === uri.fsPath ? undefined : parent;
}
function pushUniqueUri(uris, seen, uri) {
    const key = uri.toString();
    if (!seen.has(key)) {
        seen.add(key);
        uris.push(uri);
    }
}
async function isDirectory(uri) {
    try {
        const stat = await vscode.workspace.fs.stat(uri);
        return stat.type === vscode.FileType.Directory;
    }
    catch {
        return false;
    }
}
async function exists(uri) {
    try {
        await vscode.workspace.fs.stat(uri);
        return true;
    }
    catch {
        return false;
    }
}
async function getCurrentContestFileStatus(uri) {
    try {
        const stat = await vscode.workspace.fs.stat(uri);
        return stat.type === vscode.FileType.File ? "file" : "notFile";
    }
    catch {
        return "missing";
    }
}
async function readDirectoryNames(uri) {
    try {
        const entries = await vscode.workspace.fs.readDirectory(uri);
        return entries
            .filter(([, type]) => type === vscode.FileType.Directory)
            .map(([name]) => name)
            .filter((name) => ![".git", ".venv", "node_modules"].includes(name));
    }
    catch {
        return [];
    }
}
function currentContestUri(baseUri) {
    return vscode.Uri.joinPath(baseUri, ".atc", "current-contest.json");
}
function configUri(baseUri) {
    return vscode.Uri.joinPath(baseUri, ".atc", CONFIG_FILE_NAME);
}
function configProjectRoot(configFileUri) {
    const atcDir = parentUri(configFileUri);
    const projectRoot = atcDir ? parentUri(atcDir) : undefined;
    return projectRoot ?? configFileUri;
}
async function findConfigFiles() {
    const configs = [];
    const seen = new Set();
    const workspaceFolders = vscode.workspace.workspaceFolders ?? [];
    let missingWorkspaceConfig = workspaceFolders.length === 0;
    for (const workspaceFolder of workspaceFolders) {
        let current = workspaceFolder.uri;
        let foundForWorkspace = false;
        while (current) {
            const candidate = configUri(current);
            if (await exists(candidate)) {
                pushUniqueUri(configs, seen, candidate);
                foundForWorkspace = true;
                break;
            }
            current = parentUri(current);
        }
        if (!foundForWorkspace) {
            missingWorkspaceConfig = true;
        }
    }
    const home = homeDir();
    if (missingWorkspaceConfig && home) {
        const homeConfig = vscode.Uri.file(`${home}/.atc/${CONFIG_FILE_NAME}`);
        if (await exists(homeConfig)) {
            pushUniqueUri(configs, seen, homeConfig);
        }
    }
    return configs;
}
function stripTomlComment(line) {
    let quote;
    let escaped = false;
    for (let i = 0; i < line.length; i += 1) {
        const char = line[i];
        if (quote) {
            if (quote === "\"" && char === "\\" && !escaped) {
                escaped = true;
                continue;
            }
            if (char === quote && !escaped) {
                quote = undefined;
            }
            escaped = false;
            continue;
        }
        if (char === "\"" || char === "'") {
            quote = char;
            continue;
        }
        if (char === "#") {
            return line.slice(0, i);
        }
    }
    if (quote) {
        throw new Error("unterminated string");
    }
    return line;
}
function parseTomlStringValue(value, lineNumber) {
    const trimmed = value.trim();
    if (!trimmed) {
        throw new Error(`line ${lineNumber}: missing value`);
    }
    const quote = trimmed[0];
    if (quote !== "\"" && quote !== "'") {
        throw new Error(`line ${lineNumber}: [paths] values must be strings`);
    }
    if (!trimmed.endsWith(quote)) {
        throw new Error(`line ${lineNumber}: unterminated string`);
    }
    const body = trimmed.slice(1, -1);
    if (quote === "'") {
        return body;
    }
    try {
        return JSON.parse(trimmed);
    }
    catch {
        throw new Error(`line ${lineNumber}: invalid string escape`);
    }
}
function parseAtcConfig(content) {
    const paths = {};
    let contests;
    let contestSectionSeen = false;
    let section = "";
    const lines = content.split(/\r?\n/);
    for (let index = 0; index < lines.length; index += 1) {
        const lineNumber = index + 1;
        const line = stripTomlComment(lines[index]).trim();
        if (!line) {
            continue;
        }
        const sectionMatch = /^\[([A-Za-z0-9_.-]+)\]$/.exec(line);
        if (sectionMatch) {
            section = sectionMatch[1];
            if (section === "paths.contests") {
                contestSectionSeen = true;
            }
            continue;
        }
        if (section !== "paths" && section !== "paths.contests") {
            continue;
        }
        const keyValueMatch = /^([A-Za-z0-9_-]+)\s*=\s*(.+)$/.exec(line);
        const contestKeyValueMatch = /^((?:"(?:\\.|[^"])*")|(?:'(?:[^']*)')|(?:[A-Za-z0-9_-]+))\s*=\s*(.+)$/.exec(line);
        if (section === "paths" && !keyValueMatch) {
            throw new Error(`line ${lineNumber}: invalid [paths] syntax`);
        }
        if (section === "paths.contests" && !contestKeyValueMatch) {
            throw new Error(`line ${lineNumber}: invalid [paths.contests] syntax`);
        }
        if (section === "paths") {
            if (keyValueMatch[1] === "contests") {
                throw new Error("[paths.contests] must be a table.");
            }
            paths[keyValueMatch[1]] = parseTomlStringValue(keyValueMatch[2], lineNumber);
        }
        else {
            if (!contests) {
                contests = {};
            }
            contests[parseTomlStringValue(contestKeyValueMatch[1], lineNumber)] = parseTomlStringValue(contestKeyValueMatch[2], lineNumber);
        }
    }
    return { paths, contests: contestSectionSeen ? contests ?? {} : undefined };
}
async function readAtcConfig(configFileUri) {
    let content;
    try {
        content = decodeUtf8(await vscode.workspace.fs.readFile(configFileUri));
    }
    catch {
        reportConfigError(configFileUri, `Failed to read config.toml: ${configFileUri.fsPath}`);
        return undefined;
    }
    try {
        const parsed = parseAtcConfig(content);
        return {
            uri: configFileUri,
            projectRoot: configProjectRoot(configFileUri),
            paths: {
                ...DEFAULT_PATHS,
                ...parsed.paths
            },
            contests: parsed.contests ?? { ...DEFAULT_CONTEST_PATH_RULES }
        };
    }
    catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        reportConfigError(configFileUri, `Invalid config.toml: ${configFileUri.fsPath}\n${message}`);
        return undefined;
    }
}
function reportConfigError(configFileUri, message) {
    const key = `${configFileUri.toString()}::${message}`;
    logMessage(`[atc-helper] ${message}`);
    if (!reportedConfigErrors.has(key)) {
        reportedConfigErrors.add(key);
        vscode.window.showErrorMessage(message);
    }
}
function resolvePathFromConfigRoot(config, value) {
    const rootValue = value.trim();
    if (!rootValue) {
        return undefined;
    }
    const expanded = expandHomePath(rootValue);
    if (isAbsolutePath(expanded)) {
        return vscode.Uri.file(expanded);
    }
    return joinUriPath(config.projectRoot, expanded);
}
async function getAtcConfigs() {
    const configs = [];
    for (const configFile of await findConfigFiles()) {
        const config = await readAtcConfig(configFile);
        if (config) {
            configs.push(config);
        }
    }
    return configs;
}
async function findMarkerRoot(startUri) {
    let markerCandidate;
    let current = startUri;
    while (current) {
        if (await exists(vscode.Uri.joinPath(current, ".git"))) {
            return current;
        }
        if (!markerCandidate && (await exists(vscode.Uri.joinPath(current, ".vscode")) ||
            await exists(vscode.Uri.joinPath(current, "pyproject.toml")))) {
            markerCandidate = current;
        }
        current = parentUri(current);
    }
    return markerCandidate;
}
async function getAtcoderRoots() {
    const roots = [];
    const seen = new Set();
    const configs = await getAtcConfigs();
    for (const config of configs) {
        const root = resolvePathFromConfigRoot(config, config.paths.root ?? "");
        if (root) {
            logMessage(`[atc-helper] config root: ${root.fsPath} (${config.uri.fsPath})`);
            pushUniqueUri(roots, seen, root);
        }
    }
    const workspaceFolders = vscode.workspace.workspaceFolders ?? [];
    for (const workspaceFolder of workspaceFolders) {
        const markerRoot = await findMarkerRoot(workspaceFolder.uri);
        if (markerRoot) {
            pushUniqueUri(roots, seen, markerRoot);
        }
        pushUniqueUri(roots, seen, workspaceFolder.uri);
    }
    return roots;
}
async function getWorkspaceRootCandidates() {
    const roots = [];
    const seen = new Set();
    const workspaceFolders = vscode.workspace.workspaceFolders ?? [];
    for (const workspaceFolder of workspaceFolders) {
        pushUniqueUri(roots, seen, workspaceFolder.uri);
        const parent = parentUri(workspaceFolder.uri);
        if (parent) {
            pushUniqueUri(roots, seen, parent);
            const grandParent = parentUri(parent);
            if (grandParent) {
                pushUniqueUri(roots, seen, grandParent);
            }
        }
        const firstLevelNames = await readDirectoryNames(workspaceFolder.uri);
        for (const firstLevelName of firstLevelNames) {
            const firstLevelUri = vscode.Uri.joinPath(workspaceFolder.uri, firstLevelName);
            pushUniqueUri(roots, seen, firstLevelUri);
            const secondLevelNames = await readDirectoryNames(firstLevelUri);
            for (const secondLevelName of secondLevelNames) {
                pushUniqueUri(roots, seen, vscode.Uri.joinPath(firstLevelUri, secondLevelName));
            }
        }
    }
    return roots;
}
async function getCurrentContestRootCandidates() {
    const roots = [];
    const seen = new Set();
    for (const root of await getAtcoderRoots()) {
        pushUniqueUri(roots, seen, root);
    }
    for (const root of await getWorkspaceRootCandidates()) {
        pushUniqueUri(roots, seen, root);
    }
    return roots;
}
async function getCurrentContestJsonCandidates() {
    return (await getCurrentContestRootCandidates()).map(currentContestUri);
}
function contestGroupFor(contest, contests, configFileUri) {
    const lowered = contest.toLowerCase();
    let matchedGroup;
    for (const [pattern, group] of Object.entries(contests)) {
        let regex;
        try {
            regex = new RegExp(`^(?:${pattern})$`);
        }
        catch {
            reportConfigError(configFileUri, `invalid contest path regex: ${pattern}`);
            return undefined;
        }
        if (regex.test(lowered) && matchedGroup === undefined) {
            matchedGroup = group.trim();
        }
    }
    return matchedGroup;
}
async function resolveContestDirFromConfig(input) {
    for (const config of await getAtcConfigs()) {
        const root = resolvePathFromConfigRoot(config, config.paths.root ?? "");
        if (!root) {
            continue;
        }
        const categoryDir = contestGroupFor(input, config.contests, config.uri);
        const contestDir = categoryDir ? joinUriPath(root, `${categoryDir}/${input}`) : joinUriPath(root, input);
        if (await isDirectory(contestDir)) {
            return contestDir;
        }
    }
    return undefined;
}
async function resolveContestDir(input) {
    if (isAbsolutePath(input)) {
        const uri = vscode.Uri.file(expandHomePath(input));
        return (await isDirectory(uri)) ? uri : undefined;
    }
    const configResolved = await resolveContestDirFromConfig(input);
    if (configResolved) {
        return configResolved;
    }
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (!workspaceFolder) {
        return undefined;
    }
    const workspaceRelativeUri = joinUriPath(workspaceFolder.uri, input);
    return (await isDirectory(workspaceRelativeUri)) ? workspaceRelativeUri : undefined;
}
async function readCurrentContestFile(currentContestUri) {
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
    let content;
    try {
        content = decodeUtf8(await vscode.workspace.fs.readFile(currentContestUri));
    }
    catch {
        return {
            kind: "invalid",
            message: `Failed to read current contest file: ${currentContestUri.fsPath}`
        };
    }
    let parsed;
    try {
        parsed = JSON.parse(content);
    }
    catch {
        return {
            kind: "invalid",
            message: `Invalid current contest JSON: ${currentContestUri.fsPath}`
        };
    }
    if (!parsed ||
        typeof parsed !== "object" ||
        typeof parsed.contestDir !== "string" ||
        !parsed.contestDir.trim()) {
        return {
            kind: "invalid",
            message: `current-contest.json must contain a contestDir string: ${currentContestUri.fsPath}`
        };
    }
    const contestDirInput = parsed.contestDir.trim();
    const contestDir = await resolveContestDir(contestDirInput);
    if (!contestDir) {
        return {
            kind: "invalid",
            message: `Contest directory not found from ${currentContestUri.fsPath}: ${contestDirInput}`
        };
    }
    const requestId = parsed.requestId;
    logMessage(`[atc-helper] current contest loaded: ${currentContestUri.fsPath}`);
    return {
        kind: "found",
        contestDir,
        requestId: typeof requestId === "string" ? requestId : undefined,
        source: currentContestUri
    };
}
async function readCurrentContestDir() {
    const candidates = await getCurrentContestJsonCandidates();
    for (const currentContestUri of candidates) {
        logCurrentContestLookup(currentContestUri);
        const currentContest = await readCurrentContestFile(currentContestUri);
        if (currentContest.kind !== "missing") {
            return currentContest;
        }
    }
    return { kind: "missing" };
}
function currentContestRequestKey(currentContest) {
    return `${currentContest.source.toString()}::${currentContest.requestId ?? currentContest.contestDir.toString()}`;
}
async function openContestTerminals(contestDir) {
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
async function openContestTerminalsFromCurrentContestOrInput() {
    const currentContest = await readCurrentContestDir();
    if (currentContest.kind === "invalid") {
        vscode.window.showErrorMessage(currentContest.message);
        return;
    }
    let contestDir = currentContest.kind === "found" ? currentContest.contestDir : undefined;
    if (!contestDir) {
        const input = await vscode.window.showInputBox({
            prompt: "contestDir",
            placeHolder: "abc336 or path/to/abc336",
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
async function openContestTerminalsFromWatchedFile(currentContestUri) {
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
async function registerCurrentContestWatchers(context) {
    for (const rootUri of await getCurrentContestRootCandidates()) {
        const currentContest = currentContestUri(rootUri);
        logMessage(`[atc-helper] watching current contest: ${currentContest.fsPath}`);
        const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(rootUri.fsPath, ".atc/current-contest.json"));
        const handleChange = (uri) => {
            void openContestTerminalsFromWatchedFile(uri);
        };
        watcher.onDidCreate(handleChange, undefined, context.subscriptions);
        watcher.onDidChange(handleChange, undefined, context.subscriptions);
        context.subscriptions.push(watcher);
    }
}
function activate(context) {
    void registerCurrentContestWatchers(context);
    const disposable = vscode.commands.registerCommand("atc-helper.openContestTerminals", openContestTerminalsFromCurrentContestOrInput);
    context.subscriptions.push(disposable);
}
function deactivate() { }
//# sourceMappingURL=extension.js.map