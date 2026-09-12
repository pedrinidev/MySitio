/**
 * Dashboard del servidor en vivo.
 *
 * Es la pieza que convierte «sé de infraestructura» en algo comprobable: el
 * visitante ve la RAM real del droplet que le está sirviendo la página.
 *
 * Decisiones que importan:
 * - Se refresca cada 15 s, no cada segundo. La API ya cachea 10 s, así que
 *   ir más rápido solo gastaría batería del visitante para ver el mismo dato.
 * - El intervalo se **pausa cuando la pestaña no está visible**. Una pestaña
 *   olvidada durante horas no debe seguir pidiendo datos.
 * - Si la API falla, se muestra un aviso discreto. El resto de la página
 *   sigue perfecta: es HTML estático y no depende de esto.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchLiveMetrics, fetchMetricHistory } from '../../lib/api';
import { formatUptime } from '../../lib/i18n';
import type { Dictionary } from '../../lib/i18n';
import type { LiveMetrics, MetricSnapshot } from '../../lib/types';

interface Props {
  dict: Dictionary;
}

const REFRESH_MS = 15_000;

export default function MetricsDashboard({ dict }: Props) {
  const [live, setLive] = useState<LiveMetrics | null>(null);
  const [history, setHistory] = useState<MetricSnapshot[]>([]);
  const [failed, setFailed] = useState(false);
  const timer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    const { data, error } = await fetchLiveMetrics();
    if (error || !data) {
      setFailed(true);
      return;
    }
    setFailed(false);
    setLive(data);
  }, []);

  useEffect(() => {
    void refresh();
    void fetchMetricHistory(24).then(({ data }) => {
      if (data) setHistory(data);
    });
  }, [refresh]);

  useEffect(() => {
    const start = () => {
      if (timer.current !== null) return;
      timer.current = window.setInterval(refresh, REFRESH_MS);
    };
    const stop = () => {
      if (timer.current === null) return;
      window.clearInterval(timer.current);
      timer.current = null;
    };

    const onVisibilityChange = () => {
      if (document.hidden) {
        stop();
      } else {
        void refresh();
        start();
      }
    };

    if (!document.hidden) start();
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [refresh]);

  if (failed && !live) {
    return (
      <div className="metrics-fallback" role="status">
        <p>{dict.metrics.unavailable}</p>
        <button type="button" className="chip" onClick={() => void refresh()}>
          {dict.common.retry}
        </button>
      </div>
    );
  }

  if (!live) {
    return (
      <div className="metrics-fallback" role="status">
        <span className="spinner" aria-hidden="true" />
        <p>{dict.metrics.loading}</p>
      </div>
    );
  }

  return (
    <div className="metrics">
      <div className="metrics-grid">
        <Gauge
          label={dict.metrics.cpu}
          percent={live.cpu_percent}
          display={`${live.cpu_percent.toFixed(1)}%`}
        />
        <Gauge
          label={dict.metrics.memory}
          percent={live.memory.percent}
          display={`${live.memory.used_mb} / ${live.memory.total_mb} MB`}
        />
        <Gauge
          label={dict.metrics.disk}
          percent={live.disk.percent}
          display={`${live.disk.used_gb} / ${live.disk.total_gb} GB`}
        />
        <div className="metric-tile">
          <p className="metric-label">{dict.metrics.uptime}</p>
          <p className="metric-value">{formatUptime(live.uptime_seconds, dict)}</p>
          <p className="metric-sub">
            {dict.metrics.load} {live.load_1m.toFixed(2)}
          </p>
        </div>
      </div>

      {history.length > 2 && <Sparkline data={history} label={dict.metrics.last24h} />}

      <p className="metrics-stamp">
        <span className="pulse" aria-hidden="true" />
        {new Date(live.measured_at).toLocaleTimeString()}
      </p>
    </div>
  );
}

function Gauge({ label, percent, display }: { label: string; percent: number; display: string }) {
  // Umbrales de color: por debajo del 70 % normal, hasta 88 % atención, por
  // encima crítico. En un droplet de 512 MB, el 88 % de RAM es la antesala
  // del OOM killer.
  const level = percent > 88 ? 'critical' : percent > 70 ? 'warning' : 'ok';

  return (
    <div className="metric-tile">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{display}</p>
      <div
        className={`bar ${level}`}
        role="meter"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <span style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
    </div>
  );
}

function Sparkline({ data, label }: { data: MetricSnapshot[]; label: string }) {
  const width = 600;
  const height = 90;
  const max = Math.max(100, ...data.map((d) => d.cpu_percent));

  // SVG dibujado a mano en vez de una librería de gráficos: son doce líneas
  // de matemática frente a ~50 KB de dependencia para una sola curva.
  const points = data
    .map((snapshot, index) => {
      const x = (index / Math.max(data.length - 1, 1)) * width;
      const y = height - (snapshot.cpu_percent / max) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <figure className="sparkline">
      <figcaption>{label} · CPU</figcaption>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={label}
      >
        <polyline
          points={points}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    </figure>
  );
}
