import { useEffect, useMemo, useRef, useState } from 'react';
import type { InputHTMLAttributes } from 'react';
import { Alert, Button, Empty, Input, message, Space, Spin, Tree } from 'antd';
import {
  FileOutlined,
  FolderOpenOutlined,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { simulationApi } from '../api/simulation';
import type {
  LocalFileEntry,
  UploadFileContentResponse,
  UploadFileInfo,
  UploadPackageType,
} from '../types/simulation';
import { fileListToEntries } from '../utils/files';
import { formatBytes } from '../utils/format';

interface RemoteBundleEditorProps {
  title: string;
  packageType: UploadPackageType;
  uploadSessionId: string | null;
  refreshToken: number;
  onUpload: (entries: LocalFileEntry[]) => Promise<void>;
  onChanged: () => void;
}

type MutableTreeNode = { key: string; title: string; isLeaf?: boolean; selectable?: boolean; children?: MutableTreeNode[] };

function buildTree(files: UploadFileInfo[]): MutableTreeNode[] {
  const root: MutableTreeNode[] = [];

  for (const file of files) {
    const parts = file.path.split('/').filter(Boolean);
    let level = root;
    let currentPath = '';

    parts.forEach((part, index) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLeaf = index === parts.length - 1;
      const key = isLeaf ? `file:${file.path}` : `dir:${currentPath}`;
      let node = level.find((item) => item.key === key);
      if (!node) {
        node = {
          key,
          title: part,
          isLeaf,
          selectable: isLeaf,
          children: isLeaf ? undefined : [],
        };
        level.push(node);
      }
      if (!isLeaf) level = node.children || [];
    });
  }

  const sortNodes = (nodes: MutableTreeNode[]) => {
    nodes.sort((a, b) => {
      const aLeaf = a.isLeaf ? 1 : 0;
      const bLeaf = b.isLeaf ? 1 : 0;
      if (aLeaf !== bLeaf) return aLeaf - bLeaf;
      return String(a.title).localeCompare(String(b.title), 'zh-CN');
    });
    nodes.forEach((node) => {
      if (node.children) sortNodes(node.children);
    });
  };
  sortNodes(root);
  return root;
}

export function RemoteBundleEditor({
  title,
  packageType,
  uploadSessionId,
  refreshToken,
  onUpload,
  onChanged,
}: RemoteBundleEditorProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<UploadFileInfo[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<UploadFileContentResponse | null>(null);
  const [content, setContent] = useState('');
  const [contentLoading, setContentLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const treeData = useMemo(() => [
    {
      key: `root:${packageType}`,
      title,
      selectable: false,
      children: buildTree(files),
    },
  ], [files, packageType, title]);

  const loadFiles = async () => {
    if (!uploadSessionId) {
      setFiles([]);
      setSelectedPath(null);
      setFileContent(null);
      return;
    }
    setListLoading(true);
    try {
      const response = await simulationApi.listUploadFiles(uploadSessionId, packageType);
      setFiles(response.files);
      if (selectedPath && !response.files.some((item) => item.path === selectedPath)) {
        setSelectedPath(null);
        setFileContent(null);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    void loadFiles();
    // refreshToken is deliberately a reload trigger supplied by the parent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadSessionId, packageType, refreshToken]);

  async function selectFile(path: string) {
    if (!uploadSessionId) return;
    setSelectedPath(path);
    setContentLoading(true);
    try {
      const response = await simulationApi.getUploadFileContent(uploadSessionId, packageType, path);
      setFileContent(response);
      setContent(response.content || '');
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setContentLoading(false);
    }
  }

  async function saveContent() {
    if (!uploadSessionId || !selectedPath || !fileContent?.editable) return;
    setSaving(true);
    try {
      await simulationApi.updateUploadFileContent(uploadSessionId, packageType, selectedPath, content);
      message.success(`已保存 ${selectedPath}`);
      onChanged();
      await loadFiles();
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  async function handleDirectory(filesList: FileList | null) {
    const entries = fileListToEntries(filesList);
    if (!entries.length) return;
    setUploading(true);
    try {
      await onUpload(entries);
      message.success(`${title} 已替换为新上传目录`);
      setSelectedPath(null);
      setFileContent(null);
      await loadFiles();
    } catch (error) {
      message.error(error instanceof Error ? error.message : String(error));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  const directoryProps = {
    webkitdirectory: '',
    directory: '',
  } as unknown as InputHTMLAttributes<HTMLInputElement>;

  return (
    <section className="bundle-editor">
      <div className="bundle-editor-head">
        <h3>{title}</h3>
        <Space>
          <Button icon={<ReloadOutlined />} disabled={!uploadSessionId} onClick={() => void loadFiles()}>
            刷新
          </Button>
          <Button icon={<FolderOpenOutlined />} loading={uploading} onClick={() => inputRef.current?.click()}>
            重新上传
          </Button>
          <input
            ref={inputRef}
            className="hidden-file-input"
            type="file"
            multiple
            {...directoryProps}
            onChange={(event) => void handleDirectory(event.target.files)}
          />
        </Space>
      </div>

      {!uploadSessionId || files.length === 0 ? (
        <div className="bundle-editor-empty">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无配置文件" />
        </div>
      ) : (
        <div className="bundle-editor-grid">
          <aside className="bundle-tree-pane">
            <div className="pane-title">文件结构</div>
            <Spin spinning={listLoading}>
              <Tree
                key={`${uploadSessionId}-${refreshToken}-${files.length}`}
                showLine
                blockNode
                defaultExpandAll
                treeData={treeData}
                selectedKeys={selectedPath ? [`file:${selectedPath}`] : []}
                onSelect={(keys) => {
                  const key = String(keys[0] || '');
                  if (key.startsWith('file:')) void selectFile(key.slice(5));
                }}
              />
            </Spin>
          </aside>

          <div className="bundle-content-pane">
            <div className="pane-title">文件预览 / 编辑</div>
            {contentLoading ? (
              <div className="bundle-content-loading"><Spin /></div>
            ) : fileContent ? (
              <>
                <div className="file-meta-bar">
                  <div><FileOutlined /> <strong>{fileContent.path}</strong></div>
                  <span>{formatBytes(fileContent.size_bytes)}</span>
                </div>
                {fileContent.editable ? (
                  <>
                    <Input.TextArea
                      className="config-editor"
                      value={content}
                      onChange={(event) => setContent(event.target.value)}
                      spellCheck={false}
                    />
                    <div className="editor-actions editor-actions-simple">
                      <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => void saveContent()}>
                        保存修改
                      </Button>
                    </div>
                  </>
                ) : (
                  <Alert
                    type="info"
                    showIcon
                    message="该文件为只读资产"
                    description="如需调整，请重新上传对应配置目录。"
                  />
                )}
              </>
            ) : (
              <div className="bundle-content-empty">
                <Empty description="选择左侧文件进行预览" />
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
