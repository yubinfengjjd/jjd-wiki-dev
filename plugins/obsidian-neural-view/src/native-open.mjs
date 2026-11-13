import {categoryOf} from './adapter.mjs';
/** Revalidate against live vault state. openFile never creates a missing wikilink target. */
export async function openExistingNote(app, path, isFile) {
  if (!categoryOf(path)) return false;
  const currentFile = app.vault.getAbstractFileByPath(path);
  if (!currentFile || !isFile(currentFile) || currentFile.extension !== 'md' || currentFile.path !== path) return false;
  await app.workspace.getLeaf('tab').openFile(currentFile);
  return true;
}
