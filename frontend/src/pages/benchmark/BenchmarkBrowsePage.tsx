import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Empty, Select, Skeleton } from 'antd';
import { useNavigate } from 'react-router-dom';
import { benchmarkApi } from '../../api/benchmark';
import { PageHeading } from '../../components/PageHeading';
import type { ChipDetail, ChipSummary } from '../../types/benchmark';

interface ChipCardModel extends ChipSummary {
  benchmarkCount: number | null;
}

const ALL = '__all__';

function displayVendor(value: string) {
  if (!value) return '—';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function displayChip(value: string) {
  return value.toUpperCase();
}

export function BenchmarkBrowsePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ChipCardModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [vendor, setVendor] = useState(ALL);
  const [chipGeneration, setChipGeneration] = useState(ALL);
  const [loadError, setLoadError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const response = await benchmarkApi.listChips();
      const details = await Promise.allSettled(
        response.items.map((chip) => benchmarkApi.getChip(chip.vendor, chip.chip)),
      );

      setItems(response.items.map((chip, index) => {
        const detail = details[index];
        return {
          ...chip,
          benchmarkCount: detail.status === 'fulfilled'
            ? (detail.value as ChipDetail).benchmark_count
            : null,
        };
      }));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : String(error));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const vendorOptions = useMemo(() => {
    const values = Array.from(new Set(items.map((item) => item.vendor))).sort();
    return [
      { value: ALL, label: '全部厂商' },
      ...values.map((value) => ({ value, label: displayVendor(value) })),
    ];
  }, [items]);

  const chipOptions = useMemo(() => {
    const candidates = vendor === ALL
      ? items
      : items.filter((item) => item.vendor === vendor);
    const values = Array.from(new Set(candidates.map((item) => item.chip))).sort();
    return [
      { value: ALL, label: '全部代次' },
      ...values.map((value) => ({ value, label: displayChip(value) })),
    ];
  }, [items, vendor]);

  const filteredItems = useMemo(() => items.filter((item) => {
    if (vendor !== ALL && item.vendor !== vendor) return false;
    if (chipGeneration !== ALL && item.chip !== chipGeneration) return false;
    return true;
  }), [items, vendor, chipGeneration]);

  const handleVendorChange = (value: string) => {
    setVendor(value);
    setChipGeneration(ALL);
  };

  return (
    <div className="page-container benchmark-page">
      <PageHeading
        title="Benchmark"
        subtitle="按厂商和芯片代次筛选，点击芯片进入 Benchmark 主页"
      />

      {loadError ? <Alert className="benchmark-load-error" type="error" showIcon title="Benchmark 数据暂不可用" description={loadError} /> : null}

      <div className="benchmark-browser-panel">
        <div className="benchmark-filter-grid">
          <div className="benchmark-filter-field">
            <div className="benchmark-filter-label">厂商</div>
            <Select
              value={vendor}
              options={vendorOptions}
              onChange={handleVendorChange}
              className="benchmark-filter-select"
              aria-label="厂商筛选"
            />
          </div>

          <div className="benchmark-filter-field">
            <div className="benchmark-filter-label">芯片代次</div>
            <Select
              value={chipGeneration}
              options={chipOptions}
              onChange={setChipGeneration}
              className="benchmark-filter-select"
              aria-label="芯片代次筛选"
            />
          </div>
        </div>

        {loading ? (
          <div className="benchmark-chip-grid">
            {[0, 1, 2].map((value) => (
              <div className="benchmark-chip-card" key={value}>
                <Skeleton active paragraph={{ rows: 2 }} />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="benchmark-empty-panel benchmark-empty-panel-inline">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无已注册芯片" />
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="benchmark-empty-panel benchmark-empty-panel-inline">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前筛选条件下暂无芯片" />
          </div>
        ) : (
          <div className="benchmark-chip-grid">
            {filteredItems.map((item) => (
              <button
                type="button"
                className="benchmark-chip-card benchmark-chip-card-button"
                key={`${item.vendor}/${item.chip}`}
                onClick={() => navigate(`/benchmark/chips/${encodeURIComponent(item.vendor)}/${encodeURIComponent(item.chip)}`)}
              >
                <div className="benchmark-chip-title">
                  {displayVendor(item.vendor)} / {displayChip(item.chip)}
                </div>
                <div className="benchmark-chip-meta">
                  Benchmark {item.benchmarkCount == null ? '—' : item.benchmarkCount}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
