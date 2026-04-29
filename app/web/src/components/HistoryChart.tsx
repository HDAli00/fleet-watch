import { useEffect, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";

interface Props {
  title: string;
  xs: number[];
  ys: number[];
  color?: string;
}

export default function HistoryChart({ title, xs, ys, color = "#58a6ff" }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const plotRef = useRef<uPlot | null>(null);

  useEffect(() => {
    if (!hostRef.current) return;
    const opts: uPlot.Options = {
      width: hostRef.current.clientWidth || 320,
      height: 200,
      pxAlign: false,
      cursor: { drag: { setScale: false } },
      legend: { show: false },
      scales: { x: { time: true } },
      axes: [
        { stroke: "#7d8590", grid: { stroke: "#1f2735" } },
        { stroke: "#7d8590", grid: { stroke: "#1f2735" } },
      ],
      series: [
        {},
        { label: title, stroke: color, width: 1.5, points: { show: false } },
      ],
    };
    const data: uPlot.AlignedData = [xs, ys];
    plotRef.current = new uPlot(opts, data, hostRef.current);
    const ro = new ResizeObserver(() => {
      if (plotRef.current && hostRef.current) {
        plotRef.current.setSize({
          width: hostRef.current.clientWidth,
          height: 200,
        });
      }
    });
    ro.observe(hostRef.current);
    return () => {
      ro.disconnect();
      plotRef.current?.destroy();
      plotRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (plotRef.current) {
      plotRef.current.setData([xs, ys] as uPlot.AlignedData);
    }
  }, [xs, ys]);

  return (
    <div className="chart-card">
      <h4>{title}</h4>
      <div ref={hostRef} className="chart-host" />
    </div>
  );
}
