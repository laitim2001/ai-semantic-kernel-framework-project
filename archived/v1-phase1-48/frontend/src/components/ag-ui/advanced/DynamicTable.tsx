/**
 * DynamicTable - Dynamic Table Component
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-1: Tool-based Generative UI
 *
 * Renders dynamic tables based on TableColumnDefinition and row data.
 * Supports sorting, filtering, pagination, and row selection.
 */

import { FC, useState, useMemo, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/Table';
import type { TableColumnDefinition } from '@/types/ag-ui';

export interface DynamicTableProps {
  /** Column definitions */
  columns: TableColumnDefinition[];
  /** Table row data */
  rows: Record<string, unknown>[];
  /** Enable pagination */
  pagination?: boolean;
  /** Items per page */
  pageSize?: number;
  /** Callback when row is selected */
  onRowSelect?: (row: Record<string, unknown>) => void;
  /** Callback when sort changes */
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  /** Additional CSS classes */
  className?: string;
}

/** Sort direction type */
type SortDirection = 'asc' | 'desc' | null;

/** Sort state */
interface SortState {
  column: string | null;
  direction: SortDirection;
}

/**
 * DynamicTable - Renders tables with sorting, filtering, and pagination
 */
export const DynamicTable: FC<DynamicTableProps> = ({
  columns,
  rows,
  pagination = true,
  pageSize = 10,
  onRowSelect,
  onSort,
  className,
}) => {
  // Sorting state
  const [sortState, setSortState] = useState<SortState>({
    column: null,
    direction: null,
  });

  // Filter state (column key -> filter value)
  const [filters, setFilters] = useState<Record<string, string>>({});

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);

  // Handle column sort click
  const handleSort = useCallback(
    (columnKey: string) => {
      const column = columns.find((c) => c.key === columnKey);
      if (!column?.sortable) return;

      let newDirection: SortDirection = 'asc';
      if (sortState.column === columnKey) {
        if (sortState.direction === 'asc') newDirection = 'desc';
        else if (sortState.direction === 'desc') newDirection = null;
      }

      setSortState({
        column: newDirection ? columnKey : null,
        direction: newDirection,
      });

      if (newDirection && onSort) {
        onSort(columnKey, newDirection);
      }
    },
    [columns, sortState, onSort]
  );

  // Handle filter change
  const handleFilterChange = useCallback((columnKey: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [columnKey]: value,
    }));
    setCurrentPage(1); // Reset to first page on filter change
  }, []);

  // Filter rows
  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      return Object.entries(filters).every(([key, filterValue]) => {
        if (!filterValue) return true;
        const cellValue = String(row[key] || '').toLowerCase();
        return cellValue.includes(filterValue.toLowerCase());
      });
    });
  }, [rows, filters]);

  // Sort rows
  const sortedRows = useMemo(() => {
    if (!sortState.column || !sortState.direction) {
      return filteredRows;
    }

    return [...filteredRows].sort((a, b) => {
      const aValue = a[sortState.column!];
      const bValue = b[sortState.column!];

      // Handle null/undefined
      if (aValue == null && bValue == null) return 0;
      if (aValue == null) return 1;
      if (bValue == null) return -1;

      // Compare values
      let comparison = 0;
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        comparison = aValue - bValue;
      } else {
        comparison = String(aValue).localeCompare(String(bValue));
      }

      return sortState.direction === 'asc' ? comparison : -comparison;
    });
  }, [filteredRows, sortState]);

  // Paginate rows
  const paginatedRows = useMemo(() => {
    if (!pagination) return sortedRows;
    const start = (currentPage - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, pagination, currentPage, pageSize]);

  // Calculate total pages
  const totalPages = useMemo(() => {
    return Math.ceil(sortedRows.length / pageSize);
  }, [sortedRows.length, pageSize]);

  // Format cell value
  const formatCellValue = (column: TableColumnDefinition, value: unknown): string => {
    if (value == null) return '-';

    if (column.format) {
      switch (column.format) {
        case 'date':
          return new Date(value as string).toLocaleDateString();
        case 'datetime':
          return new Date(value as string).toLocaleString();
        case 'currency':
          return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
          }).format(value as number);
        case 'percent':
          return `${((value as number) * 100).toFixed(1)}%`;
        case 'number':
          return new Intl.NumberFormat().format(value as number);
      }
    }

    return String(value);
  };

  // Get sort indicator
  const getSortIndicator = (columnKey: string) => {
    if (sortState.column !== columnKey) return null;
    return sortState.direction === 'asc' ? ' ↑' : ' ↓';
  };

  // Filterable columns
  const filterableColumns = columns.filter((c) => c.filterable);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Filters */}
      {filterableColumns.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {filterableColumns.map((column) => (
            <div key={column.key} className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">{column.header}:</label>
              <Input
                type="text"
                placeholder={`Filter ${column.header}...`}
                value={filters[column.key] || ''}
                onChange={(e) => handleFilterChange(column.key, e.target.value)}
                className="h-8 w-40"
              />
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="rounded-md border overflow-auto">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead
                  key={column.key}
                  className={cn(
                    column.sortable && 'cursor-pointer select-none hover:bg-muted/50',
                    column.align === 'center' && 'text-center',
                    column.align === 'right' && 'text-right'
                  )}
                  style={{ width: column.width }}
                  onClick={() => handleSort(column.key)}
                >
                  {column.header}
                  {getSortIndicator(column.key)}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedRows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center text-muted-foreground py-8"
                >
                  No data available
                </TableCell>
              </TableRow>
            ) : (
              paginatedRows.map((row, rowIndex) => (
                <TableRow
                  key={rowIndex}
                  className={cn(onRowSelect && 'cursor-pointer hover:bg-muted/50')}
                  onClick={() => onRowSelect?.(row)}
                >
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      className={cn(
                        column.align === 'center' && 'text-center',
                        column.align === 'right' && 'text-right'
                      )}
                    >
                      {formatCellValue(column, row[column.key])}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, sortedRows.length)} of {sortedRows.length} results
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <span className="text-sm">
              Page {currentPage} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DynamicTable;
