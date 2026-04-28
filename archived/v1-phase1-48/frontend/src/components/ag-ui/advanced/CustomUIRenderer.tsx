/**
 * CustomUIRenderer - Dynamic UI Component Renderer
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-1: Tool-based Generative UI
 *
 * Renders dynamic UI components based on backend UIComponentDefinition.
 * Routes to appropriate component type: form, chart, card, table, or custom.
 */

import { FC, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import type { UIComponentDefinition, UIComponentEvent } from '@/types/ag-ui';
import { DynamicForm } from './DynamicForm';
import { DynamicChart } from './DynamicChart';
import { DynamicCard } from './DynamicCard';
import { DynamicTable } from './DynamicTable';

export interface CustomUIRendererProps {
  /** Component definition from backend */
  definition: UIComponentDefinition;
  /** Callback when component emits an event */
  onEvent?: (event: UIComponentEvent) => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether the component is in loading state */
  isLoading?: boolean;
  /** Error message to display */
  error?: string;
}

/**
 * CustomUIRenderer - Routes to appropriate dynamic component based on type
 */
export const CustomUIRenderer: FC<CustomUIRendererProps> = ({
  definition,
  onEvent,
  className,
  isLoading = false,
  error,
}) => {
  // Create event handler with component context
  const handleEvent = useMemo(() => {
    if (!onEvent) return undefined;
    return (eventType: UIComponentEvent['eventType'], data: Record<string, unknown>) => {
      onEvent({
        componentId: definition.componentId,
        eventType,
        data,
        timestamp: new Date().toISOString(),
      });
    };
  }, [definition.componentId, onEvent]);

  // Render error state
  if (error) {
    return (
      <Card className={cn('border-destructive', className)}>
        <CardHeader>
          <CardTitle className="text-destructive">Error</CardTitle>
          <CardDescription>{error}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('animate-pulse', className)}>
        <CardHeader>
          <div className="h-6 w-1/3 bg-muted rounded" />
          <div className="h-4 w-2/3 bg-muted rounded mt-2" />
        </CardHeader>
        <CardContent>
          <div className="h-32 bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  // Route to appropriate component based on type
  const renderComponent = () => {
    switch (definition.componentType) {
      case 'form':
        return (
          <DynamicForm
            fields={definition.props.fields || []}
            submitLabel={definition.props.submitLabel}
            cancelLabel={definition.props.cancelLabel}
            onSubmit={(data) => handleEvent?.('submit', data)}
            onCancel={() => handleEvent?.('click', { action: 'cancel' })}
          />
        );

      case 'chart':
        return (
          <DynamicChart
            chartType={definition.props.chartType || 'bar'}
            data={definition.props.data}
            options={definition.props.options}
            onDataPointClick={(data) => handleEvent?.('click', data)}
          />
        );

      case 'card':
        return (
          <DynamicCard
            title={definition.props.title}
            subtitle={definition.props.subtitle}
            content={definition.props.content}
            imageUrl={definition.props.imageUrl}
            actions={definition.props.actions}
            onAction={(action) => handleEvent?.('click', { action })}
          />
        );

      case 'table':
        return (
          <DynamicTable
            columns={definition.props.columns || []}
            rows={definition.props.rows || []}
            pagination={definition.props.pagination}
            pageSize={definition.props.pageSize}
            onRowSelect={(row) => handleEvent?.('select', { row })}
            onSort={(column, direction) =>
              handleEvent?.('change', { sort: { column, direction } })
            }
          />
        );

      case 'custom':
        return (
          <Card>
            <CardHeader>
              <CardTitle>{definition.props.customType || 'Custom Component'}</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm bg-muted p-4 rounded overflow-auto">
                {JSON.stringify(definition.props.customProps, null, 2)}
              </pre>
            </CardContent>
          </Card>
        );

      default:
        return (
          <Card className="border-warning">
            <CardHeader>
              <CardTitle>Unknown Component Type</CardTitle>
              <CardDescription>
                Component type &quot;{definition.componentType}&quot; is not supported.
              </CardDescription>
            </CardHeader>
          </Card>
        );
    }
  };

  return (
    <div className={cn('ag-ui-component', className)} data-component-id={definition.componentId}>
      {(definition.title || definition.description) && (
        <div className="mb-4">
          {definition.title && (
            <h3 className="text-lg font-semibold">{definition.title}</h3>
          )}
          {definition.description && (
            <p className="text-sm text-muted-foreground">{definition.description}</p>
          )}
        </div>
      )}
      {renderComponent()}
    </div>
  );
};

export default CustomUIRenderer;
