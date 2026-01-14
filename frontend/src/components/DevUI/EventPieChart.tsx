// =============================================================================
// IPA Platform - DevUI Event Pie Chart Component
// =============================================================================
// Sprint 89: S89-1 - Statistics Dashboard
//
// Pure SVG pie chart for displaying event type distribution.
//
// Dependencies:
//   - Tailwind CSS
// =============================================================================

import { FC, useMemo, useState } from 'react';
import { cn } from '@/lib/utils';

interface PieChartData {
  /** Label for the segment */
  label: string;
  /** Numeric value */
  value: number;
  /** Color for the segment */
  color: string;
}

interface EventPieChartProps {
  /** Chart data */
  data: PieChartData[];
  /** Chart size in pixels */
  size?: number;
  /** Donut hole size (0-1, 0 = full pie, 0.6 = donut) */
  innerRadius?: number;
  /** Show legend */
  showLegend?: boolean;
  /** Show center label */
  centerLabel?: string;
  /** Show center value */
  centerValue?: string | number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Calculate path for pie segment
 */
function describeArc(
  x: number,
  y: number,
  outerRadius: number,
  innerRadius: number,
  startAngle: number,
  endAngle: number
): string {
  // Convert angles to radians
  const startRad = ((startAngle - 90) * Math.PI) / 180;
  const endRad = ((endAngle - 90) * Math.PI) / 180;

  // Outer arc points
  const outerStartX = x + outerRadius * Math.cos(startRad);
  const outerStartY = y + outerRadius * Math.sin(startRad);
  const outerEndX = x + outerRadius * Math.cos(endRad);
  const outerEndY = y + outerRadius * Math.sin(endRad);

  // Inner arc points
  const innerStartX = x + innerRadius * Math.cos(startRad);
  const innerStartY = y + innerRadius * Math.sin(startRad);
  const innerEndX = x + innerRadius * Math.cos(endRad);
  const innerEndY = y + innerRadius * Math.sin(endRad);

  // Large arc flag
  const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;

  // Build path
  if (innerRadius === 0) {
    // Full pie slice
    return [
      `M ${x} ${y}`,
      `L ${outerStartX} ${outerStartY}`,
      `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEndX} ${outerEndY}`,
      'Z',
    ].join(' ');
  } else {
    // Donut slice
    return [
      `M ${outerStartX} ${outerStartY}`,
      `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEndX} ${outerEndY}`,
      `L ${innerEndX} ${innerEndY}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStartX} ${innerStartY}`,
      'Z',
    ].join(' ');
  }
}

/**
 * Event Pie Chart Component
 * Pure SVG implementation for event type distribution
 */
export const EventPieChart: FC<EventPieChartProps> = ({
  data,
  size = 200,
  innerRadius = 0.6,
  showLegend = true,
  centerLabel,
  centerValue,
  className,
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Calculate total and angles
  const { total, segments } = useMemo(() => {
    const totalValue = data.reduce((sum, item) => sum + item.value, 0);

    if (totalValue === 0) {
      return { total: 0, segments: [] };
    }

    let currentAngle = 0;
    const segmentData = data.map((item, index) => {
      const angle = (item.value / totalValue) * 360;
      const startAngle = currentAngle;
      const endAngle = currentAngle + angle;
      currentAngle = endAngle;

      return {
        ...item,
        index,
        startAngle,
        endAngle,
        percentage: ((item.value / totalValue) * 100).toFixed(1),
      };
    });

    return { total: totalValue, segments: segmentData };
  }, [data]);

  // Chart dimensions
  const center = size / 2;
  const outerRadius = center - 4; // 4px padding for hover effect
  const innerRadiusValue = outerRadius * innerRadius;

  if (total === 0) {
    return (
      <div className={cn('flex flex-col items-center', className)}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={center}
            cy={center}
            r={outerRadius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="2"
          />
          <text
            x={center}
            y={center}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-gray-400 text-sm"
          >
            No data
          </text>
        </svg>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      {/* Chart */}
      <div className="flex justify-center">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Pie segments */}
          {segments.map((segment) => {
            // Handle full circle case (single segment with 100%)
            if (segment.endAngle - segment.startAngle >= 359.9) {
              return (
                <circle
                  key={segment.index}
                  cx={center}
                  cy={center}
                  r={(outerRadius + innerRadiusValue) / 2}
                  fill="none"
                  stroke={segment.color}
                  strokeWidth={outerRadius - innerRadiusValue}
                  className={cn(
                    'transition-all duration-200 cursor-pointer',
                    hoveredIndex === segment.index && 'opacity-80'
                  )}
                  onMouseEnter={() => setHoveredIndex(segment.index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                />
              );
            }

            return (
              <path
                key={segment.index}
                d={describeArc(
                  center,
                  center,
                  hoveredIndex === segment.index ? outerRadius + 2 : outerRadius,
                  innerRadiusValue,
                  segment.startAngle,
                  segment.endAngle
                )}
                fill={segment.color}
                className={cn(
                  'transition-all duration-200 cursor-pointer',
                  hoveredIndex === segment.index && 'filter brightness-110'
                )}
                onMouseEnter={() => setHoveredIndex(segment.index)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            );
          })}

          {/* Center content */}
          {(centerLabel || centerValue) && innerRadius > 0 && (
            <g>
              {centerValue !== undefined && (
                <text
                  x={center}
                  y={centerLabel ? center - 8 : center}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="fill-gray-900 font-semibold"
                  style={{ fontSize: size * 0.12 }}
                >
                  {centerValue}
                </text>
              )}
              {centerLabel && (
                <text
                  x={center}
                  y={centerValue !== undefined ? center + 12 : center}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="fill-gray-500"
                  style={{ fontSize: size * 0.06 }}
                >
                  {centerLabel}
                </text>
              )}
            </g>
          )}
        </svg>
      </div>

      {/* Tooltip for hovered segment */}
      {hoveredIndex !== null && segments[hoveredIndex] && (
        <div className="text-center text-sm">
          <span className="font-medium">{segments[hoveredIndex].label}</span>
          <span className="text-gray-500 ml-2">
            {segments[hoveredIndex].value} ({segments[hoveredIndex].percentage}%)
          </span>
        </div>
      )}

      {/* Legend */}
      {showLegend && (
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2">
          {segments.map((segment) => (
            <div
              key={segment.index}
              className={cn(
                'flex items-center gap-1.5 cursor-pointer transition-opacity',
                hoveredIndex !== null && hoveredIndex !== segment.index && 'opacity-50'
              )}
              onMouseEnter={() => setHoveredIndex(segment.index)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <div
                className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ backgroundColor: segment.color }}
              />
              <span className="text-xs text-gray-600">
                {segment.label}
                <span className="text-gray-400 ml-1">({segment.percentage}%)</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Get color for event type
 */
export function getEventTypeColor(eventType: string): string {
  const type = eventType.toUpperCase();

  if (type.includes('WORKFLOW')) return '#3b82f6'; // blue
  if (type.includes('EXECUTOR')) return '#6366f1'; // indigo
  if (type.includes('LLM')) return '#a855f7'; // purple
  if (type.includes('TOOL')) return '#22c55e'; // green
  if (type.includes('CHECKPOINT')) return '#eab308'; // yellow
  if (type.includes('ERROR')) return '#ef4444'; // red
  if (type.includes('WARNING')) return '#f97316'; // orange

  return '#6b7280'; // gray
}

export default EventPieChart;
