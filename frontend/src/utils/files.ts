import type { LocalFileEntry } from '../types/simulation';

const CONFIG_EXTENSIONS = new Set(['yml', 'yaml', 'json']);

export function fileListToEntries(fileList: FileList | null): LocalFileEntry[] {
  if (!fileList) return [];

  return Array.from(fileList)
    .map((file) => {
      const rawPath = (file.webkitRelativePath || file.name).replace(/\\/g, '/');
      const parts = rawPath.split('/').filter(Boolean);
      const relativePath = parts.length > 1 ? parts.slice(1).join('/') : parts[0] || file.name;
      return { file, relativePath };
    })
    .sort((a, b) => a.relativePath.localeCompare(b.relativePath));
}

export function summarizeEntries(entries: LocalFileEntry[]) {
  const configFiles = entries.filter(({ relativePath }) => {
    const extension = relativePath.split('.').pop()?.toLowerCase() || '';
    return CONFIG_EXTENSIONS.has(extension);
  }).length;

  const totalBytes = entries.reduce((sum, entry) => sum + entry.file.size, 0);

  return {
    totalFiles: entries.length,
    configFiles,
    assetFiles: entries.length - configFiles,
    totalBytes,
  };
}

export async function readFirstConfigPreview(entries: LocalFileEntry[]): Promise<{
  path: string;
  text: string;
} | null> {
  const entry = entries.find(({ relativePath }) => {
    const extension = relativePath.split('.').pop()?.toLowerCase() || '';
    return CONFIG_EXTENSIONS.has(extension);
  });

  if (!entry) return null;
  const text = await entry.file.text();
  return {
    path: entry.relativePath,
    text: text.slice(0, 7000),
  };
}
