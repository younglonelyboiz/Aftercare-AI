import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Calendar,
  Clock,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import PatientHistoryCalendar from './PatientHistoryCalendar';
import {
  formatCheckinDateVN,
  formatCheckinShortDateVN,
  formatMonthPillVN,
  getCheckinDateKeyVN,
  getMonthKeyVN,
  getRecentDaysVN,
  getSortedHistoryAsc,
} from '../../utils/patientDate';

const ZONE_META = {
  GREEN: {
    label: 'Ổn định',
    chipClass: 'green',
    barClass: 'green',
    icon: ShieldCheck,
  },
  YELLOW: {
    label: 'Cảnh báo',
    chipClass: 'yellow',
    barClass: 'yellow',
    icon: AlertTriangle,
  },
  RED: {
    label: 'Cấp cứu',
    chipClass: 'red',
    barClass: 'red',
    icon: ShieldAlert,
  },
};

function getZoneMeta(zone, pefPct) {
  const normalized = String(zone || '').toUpperCase();
  if (ZONE_META[normalized]) return ZONE_META[normalized];
  if (typeof pefPct === 'number') {
    if (pefPct < 60) return ZONE_META.RED;
    if (pefPct < 80) return ZONE_META.YELLOW;
    return ZONE_META.GREEN;
  }
  return {
    label: 'Chưa có',
    chipClass: 'unknown',
    barClass: 'green',
    icon: Clock,
  };
}

export default function PatientHistoryView({
  history = [],
  carePlan,
  profile,
  trendRange = '14d',
  onSelectTrendRange,
  monthOptions: passedMonthOptions,
  onOpenCheckin,
}) {
  const [selectedPointKey, setSelectedPointKey] = useState(null);
  const [currentMonthKey] = useState(() => getMonthKeyVN(new Date()));

  const personalBest =
    carePlan?.personal_best_pef ||
    profile?.clinical_status?.personal_best_pef ||
    500;

  const sortedAsc = useMemo(() => getSortedHistoryAsc(history), [history]);

  const monthOptions = useMemo(() => {
    if (Array.isArray(passedMonthOptions)) return passedMonthOptions;
    const uniqueKeys = new Set();
    history.forEach((item) => {
      const mKey = getMonthKeyVN(item);
      if (/^\d{4}-\d{2}$/.test(mKey)) uniqueKeys.add(mKey);
    });
    return Array.from(uniqueKeys)
      .sort((a, b) => b.localeCompare(a))
      .slice(0, 2)
      .map((key) => ({ key, label: formatMonthPillVN(key) }));
  }, [history, passedMonthOptions]);

  const chartItems = useMemo(() => {
    const withPef = sortedAsc.filter(
      (item) => item && item.pef_value !== null && item.pef_value !== undefined && Number(item.pef_value) > 0
    );
    if (withPef.length === 0) return [];

    if (trendRange === '7d') {
      const allowed = new Set(getRecentDaysVN(7).map((d) => d.dateStr));
      return withPef.filter((item) => allowed.has(getCheckinDateKeyVN(item)));
    }
    if (trendRange === '14d') {
      const allowed = new Set(getRecentDaysVN(14).map((d) => d.dateStr));
      return withPef.filter((item) => allowed.has(getCheckinDateKeyVN(item)));
    }
    return withPef.filter((item) => getMonthKeyVN(item) === trendRange);
  }, [sortedAsc, trendRange]);

  const chartScaleMax = useMemo(() => {
    const maxPoint = chartItems.reduce((acc, item) => Math.max(acc, Number(item.pef_value) || 0), 0);
    return Math.max(personalBest, maxPoint, 100);
  }, [chartItems, personalBest]);

  const greenCutoff = Math.round(personalBest * 0.8);
  const refLineBottomPx = 17 + Math.round((greenCutoff / chartScaleMax) * 122);

  const activePoint = useMemo(() => {
    if (chartItems.length === 0) return null;
    const found = chartItems.find((item, idx) => `${getCheckinDateKeyVN(item)}-${idx}` === selectedPointKey);
    return found || chartItems[chartItems.length - 1];
  }, [chartItems, selectedPointKey]);

  const rangeTitleLabel =
    trendRange === '7d'
      ? '7 ngày gần nhất'
      : trendRange === '14d'
      ? '14 ngày gần nhất'
      : formatMonthPillVN(trendRange);

  return (
    <div className="space-y-5">
      {/* Header & Time Filter owned exclusively by History tab */}
      <div className="pw-card space-y-4">
        <div className="pw-card-header mb-0 flex-wrap gap-3">
          <div>
            <h1 className="pw-welcome-heading">Nhật Ký &amp; Xu Hướng Kiểm Soát Hen (14 Ngày)</h1>
            <p className="pw-card-sub mt-1 m-0">
              Biểu đồ lưu lượng đỉnh (PEF), lưới 14 ngày và nhật ký đã lưu theo phác đồ GINA 2023
            </p>
          </div>
          {onOpenCheckin && (
            <button
              type="button"
              onClick={onOpenCheckin}
              className="pw-btn-soft"
            >
              Điền check-in hôm nay
            </button>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 flex-wrap pt-3 border-t border-[#e2e8f0]">
          <div className="pw-period-pills" role="group" aria-label="Bộ lọc khoảng thời gian xu hướng PEF">
            <button
              type="button"
              className={`pw-pill ${trendRange === '7d' ? 'active' : ''}`}
              aria-pressed={trendRange === '7d'}
              onClick={() => onSelectTrendRange?.('7d')}
            >
              7 ngày
            </button>
            <button
              type="button"
              className={`pw-pill ${trendRange === '14d' ? 'active' : ''}`}
              aria-pressed={trendRange === '14d'}
              onClick={() => onSelectTrendRange?.('14d')}
            >
              14 ngày
            </button>

            {monthOptions.length > 0 ? (
              monthOptions.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  className={`pw-pill ${trendRange === opt.key ? 'active' : ''}`}
                  aria-pressed={trendRange === opt.key}
                  onClick={() => onSelectTrendRange?.(opt.key)}
                >
                  <Calendar size={13} className="pw-pill-cal-icon" aria-hidden="true" />
                  <span>
                    <span className="pw-pill-month-short">{opt.key.replace(/^\d{2}(\d{2})-(\d{2})$/, 'T$2/$1')}</span>
                    <span className="pw-pill-month-full">{opt.label}</span>
                  </span>
                </button>
              ))
            ) : (
              <button
                type="button"
                className="pw-pill"
                disabled
                aria-disabled="true"
                title="Chưa có dữ liệu tháng này"
              >
                <Calendar size={13} className="pw-pill-cal-icon" aria-hidden="true" />
                <span>
                  <span className="pw-pill-month-short">{currentMonthKey.replace(/^\d{2}(\d{2})-(\d{2})$/, 'T$2/$1')}</span>
                  <span className="pw-pill-month-full">{formatMonthPillVN(currentMonthKey)} (Chưa có dữ liệu)</span>
                </span>
              </button>
            )}
          </div>

          <span className="pw-chart-ref-tag">Mốc xanh ≥ 80% ({greenCutoff} L/p)</span>
        </div>
      </div>

      {/* Real-data PEF Trend Chart */}
      <section className="pw-card pw-chart-card" aria-label="Xu hướng PEF">
        <div className="pw-card-header mb-0 flex-wrap">
          <div>
            <h2 className="pw-card-title">
              <TrendingUp size={18} className="text-[#2568d4]" aria-hidden="true" />
              <span>Xu hướng PEF</span>
            </h2>
            <div className="pw-card-sub mt-0.5">
              {rangeTitleLabel} • {chartItems.length} lần đo thật
            </div>
          </div>
        </div>

        {chartItems.length > 0 ? (
          <div className="pw-chart-area">
            <div className="pw-chart-bars" role="list" aria-label="Các điểm dữ liệu PEF theo thời gian">
              <div
                className="pw-chart-ref-line"
                style={{ bottom: `${refLineBottomPx}px` }}
                aria-hidden="true"
              />

              {chartItems.map((item, idx) => {
                const val = Number(item.pef_value);
                const pctHeight = Math.min(100, Math.max(10, Math.round((val / chartScaleMax) * 100)));
                const pctPersonal = Math.round((val / personalBest) * 100);
                const meta = getZoneMeta(item.action_zone, pctPersonal);
                const key = `${getCheckinDateKeyVN(item)}-${idx}`;
                const isActive = activePoint === item;

                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelectedPointKey(key)}
                    aria-pressed={isActive}
                    aria-label={`Ngày ${formatCheckinDateVN(item)}, PEF ${val} L/phút, ${meta.label}`}
                    className={`pw-bar-col ${isActive ? 'selected' : ''}`}
                  >
                    <span className="pw-bar-val">{val}</span>
                    <span className="pw-bar-track">
                      <span
                        className={`pw-bar-fill ${meta.barClass}`}
                        style={{ height: `${pctHeight}%` }}
                      />
                    </span>
                    <span className="pw-bar-date">{formatCheckinShortDateVN(item)}</span>
                  </button>
                );
              })}
            </div>

            {activePoint && (() => {
              const pct = Math.round((Number(activePoint.pef_value) / personalBest) * 100);
              const meta = getZoneMeta(activePoint.action_zone, pct);
              const PointIcon = meta.icon;
              return (
                <div className="pw-chart-inspector">
                  <div>
                    <strong className="text-[#172b3a] font-semibold">{formatCheckinDateVN(activePoint)}</strong>
                    <span className="text-[#475569] font-medium">
                      {' '}• PEF {activePoint.pef_value} L/phút ({pct}%)
                      {activePoint.spo2_value != null ? ` • SpO₂ ${activePoint.spo2_value}%` : ''}
                    </span>
                  </div>
                  <span className={`pw-status-chip ${meta.chipClass}`}>
                    <PointIcon size={12} aria-hidden="true" />
                    <span>{meta.label}</span>
                  </span>
                </div>
              );
            })()}
          </div>
        ) : (
          <div className="pw-empty-inline flex flex-col items-center justify-center gap-2">
            <p className="m-0">
              Chưa có điểm đo PEF nào trong khoảng <strong>{rangeTitleLabel}</strong>.
            </p>
            {history.length > 0 && trendRange === '7d' && onSelectTrendRange && (
              <button
                type="button"
                className="pw-btn-soft"
                onClick={() => onSelectTrendRange('14d')}
              >
                Xem 14 ngày gần nhất
              </button>
            )}
          </div>
        )}
      </section>

      {/* 14-day Grid & Detailed Log List (without duplicate Sparkline summary header) */}
      <PatientHistoryCalendar history={history} hideTrendSummary />
    </div>
  );
}
