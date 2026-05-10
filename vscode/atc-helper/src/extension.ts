import * as vscode from "vscode";

const CONTEST_GROUPS: Record<string, string> = {
  abc: "ABC(Atcoder Beginner Contest)",
  arc: "ARC(Atcoder Regular Contest)",
  agc: "AGC(Atcoder Grand Contest)"
};

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

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand(
    "atc-helper.openContestTerminals",
    async () => {
      const input = await vscode.window.showInputBox({
        prompt: "contestDir",
        placeHolder: "abc336 or D:\\atcoder\\ABC(Atcoder Beginner Contest)\\abc336",
        ignoreFocusOut: true
      });

      const contestDirInput = input?.trim();
      if (!contestDirInput) {
        return;
      }

      const contestDir = await resolveContestDir(contestDirInput);
      if (!contestDir) {
        vscode.window.showErrorMessage(`Contest directory not found: ${contestDirInput}`);
        return;
      }

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
  );

  context.subscriptions.push(disposable);
}

export function deactivate() {}
