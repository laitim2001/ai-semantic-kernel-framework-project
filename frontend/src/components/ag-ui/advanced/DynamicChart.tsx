/**
 * DynamicChart - Dynamic Chart Component
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-1: Tool-based Generative UI
 *
 * Renders dynamic charts based on ChartType and ChartData from backend.
 * Supports line, bar, pie, area, scatter, and doughnut chart types.
 *
 * Note: This component provides a placeholder implementation.
 * For production, integrate with a charting library like Chart.js, Recharts, or Visx.
 */

import { FC, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import type { ChartType, ChartData } from '@/types/ag-ui';

export interface DynamicChartProps {
  /** Chart type */
  chartType: ChartType;
  /** Chart data */
  data?: ChartData;
  /** Chart options */
  options?: Record<string, unknown>;
  /** Callback when data point is clicked */
  onDataPointClick?: (data: { label: string; value: number; datasetIndex: number }) => void;
  /** Additional CSS classes */
  className?: string;
  /** Chart height */
  height?: number;
}

// Color palette for charts
const CHART_COLORS = [
  'hsl(var(--primary))',
  'hsl(var(--secondary))',
  'hsl(217, 91%, 60%)', // Blue
  'hsl(142, 71%, 45%)', // Green
  'hsl(48, 96%, 53%)', // Yellow
  'hsl(280, 65%, 60%)', // Purple
  'hsl(15, 80%, 55%)', // Orange
  'hsl(340, 65%, 55%)', // Pink
];

/**
 * Simple Bar Chart Component
 */
const BarChart: FC<{
  data: ChartData;
  height: number;
  onDataPointClick?: DynamicChartProps['onDataPointClick'];
}> = ({ data, height, onDataPointClick }) => {
  const maxValue = useMemo(() => {
    return Math.max(...data.datasets.flatMap((ds) => ds.data));
  }, [data.datasets]);

  return (
    <div className="flex items-end justify-around gap-2" style={{ height }}>
      {data.labels.map((label, labelIndex) => (
        <div key={label} className="flex flex-col items-center flex-1 max-w-20">
          <div className="flex items-end gap-1 w-full justify-center" style={{ height: height - 30 }}>
            {data.datasets.map((dataset, datasetIndex) => {
              const value = dataset.data[labelIndex] || 0;
              const barHeight = (value / maxValue) * 100;
              const color = dataset.backgroundColor
                ? Array.isArray(dataset.backgroundColor)
                  ? dataset.backgroundColor[labelIndex]
                  : dataset.backgroundColor
                : CHART_COLORS[datasetIndex % CHART_COLORS.length];

              return (
                <button
                  key={datasetIndex}
                  className="transition-all hover:opacity-80 cursor-pointer rounded-t min-w-4"
                  style={{
                    height: `${barHeight}%`,
                    backgroundColor: color,
                    minHeight: value > 0 ? 4 : 0,
                  }}
                  onClick={() => onDataPointClick?.({ label, value, datasetIndex })}
                  title={`${dataset.label}: ${value}`}
                />
              );
            })}
          </div>
          <span className="text-xs text-muted-foreground mt-1 truncate w-full text-center">
            {label}
          </span>
        </div>
      ))}
    </div>
  );
};

/**
 * Simple Pie/Doughnut Chart Component
 */
const PieChart: FC<{
  data: ChartData;
  height: number;
  isDoughnut?: boolean;
  onDataPointClick?: DynamicChartProps['onDataPointClick'];
}> = ({ data, height, isDoughnut = false, onDataPointClick }) => {
  const dataset = data.datasets[0];
  const total = useMemo(() => dataset?.data.reduce((a, b) => a + b, 0) || 0, [dataset]);

  const slices = useMemo(() => {
    if (!dataset) return [];
    let currentAngle = 0;
    return dataset.data.map((value, index) => {
      const angle = (value / total) * 360;
      const slice = {
        value,
        label: data.labels[index],
        startAngle: currentAngle,
        endAngle: currentAngle + angle,
        color: dataset.backgroundColor
          ? Array.isArray(dataset.backgroundColor)
            ? dataset.backgroundColor[index]
            : dataset.backgroundColor
          : CHART_COLORS[index % CHART_COLORS.length],
      };
      currentAngle += angle;
      return slice;
    });
  }, [dataset, data.labels, total]);

  // Create conic gradient for pie chart
  const gradient = useMemo(() => {
    const stops = slices
      .map(
        (slice) =>
          `${slice.color} ${slice.startAngle}deg ${slice.endAngle}deg`
      )
      .join(', ');
    return `conic-gradient(${stops})`;
  }, [slices]);

  const size = Math.min(height, 200);

  return (
    <div className="flex items-center justify-center gap-4">
      <div
        className="rounded-full relative cursor-pointer"
        style={{
          width: size,
          height: size,
          background: gradient,
        }}
        onClick={() => onDataPointClick?.({ label: 'chart', value: total, datasetIndex: 0 })}
      >
        {isDoughnut && (
          <div
            className="absolute bg-background rounded-full"
            style={{
              width: size * 0.5,
              height: size * 0.5,
              top: size * 0.25,
              left: size * 0.25,
            }}
          />
        )}
      </div>
      <div className="flex flex-col gap-1">
        {slices.map((slice) => (
          <div key={slice.label} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: slice.color }}
            />
            <span className="text-muted-foreground">{slice.label}:</span>
            <span className="font-medium">{slice.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Simple Line/Area Chart Component
 */
const LineChart: FC<{
  data: ChartData;
  height: number;
  isArea?: boolean;
  onDataPointClick?: DynamicChartProps['onDataPointClick'];
}> = ({ data, height, isArea = false, onDataPointClick }) => {
  const { minValue, maxValue, points } = useMemo(() => {
    const allValues = data.datasets.flatMap((ds) => ds.data);
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const range = max - min || 1;

    const datasetPoints = data.datasets.map((dataset, datasetIndex) => ({
      dataset,
      datasetIndex,
      coords: dataset.data.map((value, index) => ({
        x: (index / (data.labels.length - 1 || 1)) * 100,
        y: 100 - ((value - min) / range) * 100,
        value,
        label: data.labels[index],
      })),
    }));

    return { minValue: min, maxValue: max, points: datasetPoints };
  }, [data]);

  return (
    <div className="relative" style={{ height }}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="w-full h-full"
      >
        {points.map(({ dataset, datasetIndex, coords }) => {
          const color = dataset.borderColor || CHART_COLORS[datasetIndex % CHART_COLORS.length];
          const pathData = coords
            .map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`)
            .join(' ');

          return (
            <g key={datasetIndex}>
              {isArea && (
                <path
                  d={`${pathData} L 100 100 L 0 100 Z`}
                  fill={color}
                  fillOpacity={0.2}
                />
              )}
              <path d={pathData} stroke={color} strokeWidth={2} fill="none" />
              {coords.map((c, i) => (
                <circle
                  key={i}
                  cx={c.x}
                  cy={c.y}
                  r={3}
                  fill={color}
                  className="cursor-pointer hover:r-4"
                  onClick={() =>
                    onDataPointClick?.({
                      label: c.label,
                      value: c.value,
                      datasetIndex,
                    })
                  }
                />
              ))}
            </g>
          );
        })}
      </svg>
      <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-muted-foreground px-1">
        {data.labels.map((label) => (
          <span key={label} className="truncate max-w-12">
            {label}
          </span>
        ))}
      </div>
      <div className="absolute top-0 left-0 bottom-6 flex flex-col justify-between text-xs text-muted-foreground">
        <span>{maxValue}</span>
        <span>{minValue}</span>
      </div>
    </div>
  );
};

/**
 * Scatter Chart Component
 */
const ScatterChart: FC<{
  data: ChartData;
  height: number;
  onDataPointClick?: DynamicChartProps['onDataPointClick'];
}> = ({ data, height, onDataPointClick }) => {
  const { points } = useMemo(() => {
    // For scatter, we expect data in pairs [x, y]
    // If not, use index as X
    const allY = data.datasets.flatMap((ds) => ds.data);
    const maxYVal = Math.max(...allY);
    const maxXVal = data.labels.length - 1 || 1;

    const scatterPoints = data.datasets.map((dataset, datasetIndex) => ({
      dataset,
      datasetIndex,
      coords: dataset.data.map((y, x) => ({
        x: (x / maxXVal) * 100,
        y: 100 - (y / maxYVal) * 100,
        value: y,
        label: data.labels[x],
      })),
    }));

    return { points: scatterPoints, maxX: maxXVal, maxY: maxYVal };
  }, [data]);

  return (
    <div className="relative" style={{ height }}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
        {points.map(({ dataset, datasetIndex, coords }) => {
          const color = dataset.backgroundColor
            ? Array.isArray(dataset.backgroundColor)
              ? dataset.backgroundColor[0]
              : dataset.backgroundColor
            : CHART_COLORS[datasetIndex % CHART_COLORS.length];

          return coords.map((c, i) => (
            <circle
              key={`${datasetIndex}-${i}`}
              cx={c.x}
              cy={c.y}
              r={4}
              fill={color}
              className="cursor-pointer hover:opacity-80"
              onClick={() =>
                onDataPointClick?.({
                  label: c.label,
                  value: c.value,
                  datasetIndex,
                })
              }
            />
          ));
        })}
      </svg>
    </div>
  );
};

/**
 * DynamicChart - Routes to appropriate chart type
 */
export const DynamicChart: FC<DynamicChartProps> = ({
  chartType,
  data,
  options,
  onDataPointClick,
  className,
  height = 200,
}) => {
  // Handle missing data
  if (!data || !data.datasets || data.datasets.length === 0) {
    return (
      <Card className={cn('border-dashed', className)}>
        <CardContent className="flex items-center justify-center" style={{ height }}>
          <p className="text-muted-foreground">No chart data available</p>
        </CardContent>
      </Card>
    );
  }

  const title = (options?.title as { text?: string })?.text;

  return (
    <Card className={className}>
      {title && (
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        {chartType === 'bar' && (
          <BarChart data={data} height={height} onDataPointClick={onDataPointClick} />
        )}
        {chartType === 'line' && (
          <LineChart data={data} height={height} onDataPointClick={onDataPointClick} />
        )}
        {chartType === 'area' && (
          <LineChart data={data} height={height} isArea onDataPointClick={onDataPointClick} />
        )}
        {chartType === 'pie' && (
          <PieChart data={data} height={height} onDataPointClick={onDataPointClick} />
        )}
        {chartType === 'doughnut' && (
          <PieChart data={data} height={height} isDoughnut onDataPointClick={onDataPointClick} />
        )}
        {chartType === 'scatter' && (
          <ScatterChart data={data} height={height} onDataPointClick={onDataPointClick} />
        )}
      </CardContent>
    </Card>
  );
};

export default DynamicChart;
