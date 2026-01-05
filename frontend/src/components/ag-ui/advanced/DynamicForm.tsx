/**
 * DynamicForm - Dynamic Form Component
 *
 * Sprint 60: AG-UI Advanced Features
 * S60-1: Tool-based Generative UI
 *
 * Renders dynamic forms based on FormFieldDefinition array from backend.
 * Supports all field types: text, number, email, select, checkbox, etc.
 */

import { FC, useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';
import { Checkbox } from '@/components/ui/Checkbox';
import { RadioGroup, RadioGroupItem } from '@/components/ui/RadioGroup';
import type { FormFieldDefinition } from '@/types/ag-ui';

export interface DynamicFormProps {
  /** Form field definitions */
  fields: FormFieldDefinition[];
  /** Submit button label */
  submitLabel?: string;
  /** Cancel button label */
  cancelLabel?: string;
  /** Callback when form is submitted */
  onSubmit?: (data: Record<string, unknown>) => void;
  /** Callback when form is cancelled */
  onCancel?: () => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether form is submitting */
  isSubmitting?: boolean;
}

/**
 * DynamicForm - Renders forms dynamically from field definitions
 */
export const DynamicForm: FC<DynamicFormProps> = ({
  fields,
  submitLabel = 'Submit',
  cancelLabel = 'Cancel',
  onSubmit,
  onCancel,
  className,
  isSubmitting = false,
}) => {
  // Initialize form state from field defaults
  const [formData, setFormData] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    fields.forEach((field) => {
      if (field.defaultValue !== undefined) {
        initial[field.name] = field.defaultValue;
      } else if (field.fieldType === 'checkbox') {
        initial[field.name] = false;
      } else {
        initial[field.name] = '';
      }
    });
    return initial;
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Handle field value change
  const handleChange = useCallback((name: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  // Validate form
  const validate = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    fields.forEach((field) => {
      const value = formData[field.name];

      // Required validation
      if (field.required) {
        if (value === undefined || value === null || value === '') {
          newErrors[field.name] = `${field.label} is required`;
          return;
        }
      }

      // Type-specific validation
      if (value && field.validation) {
        const { minLength, maxLength, min, max, pattern } = field.validation as Record<
          string,
          unknown
        >;

        if (typeof value === 'string') {
          if (minLength && value.length < (minLength as number)) {
            newErrors[field.name] = `Minimum ${minLength} characters required`;
          }
          if (maxLength && value.length > (maxLength as number)) {
            newErrors[field.name] = `Maximum ${maxLength} characters allowed`;
          }
          if (pattern && !new RegExp(pattern as string).test(value)) {
            newErrors[field.name] = 'Invalid format';
          }
        }

        if (typeof value === 'number') {
          if (min !== undefined && value < (min as number)) {
            newErrors[field.name] = `Minimum value is ${min}`;
          }
          if (max !== undefined && value > (max as number)) {
            newErrors[field.name] = `Maximum value is ${max}`;
          }
        }
      }

      // Email validation
      if (field.fieldType === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value as string)) {
          newErrors[field.name] = 'Invalid email address';
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [fields, formData]);

  // Handle form submit
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (validate() && onSubmit) {
        onSubmit(formData);
      }
    },
    [formData, onSubmit, validate]
  );

  // Render field based on type
  const renderField = (field: FormFieldDefinition) => {
    const value = formData[field.name];
    const error = errors[field.name];
    const fieldId = `field-${field.name}`;

    const commonProps = {
      id: fieldId,
      'aria-invalid': !!error,
      'aria-describedby': error ? `${fieldId}-error` : undefined,
    };

    switch (field.fieldType) {
      case 'text':
      case 'email':
      case 'password':
        return (
          <Input
            {...commonProps}
            type={field.fieldType}
            value={(value as string) || ''}
            placeholder={field.placeholder}
            onChange={(e) => handleChange(field.name, e.target.value)}
            className={cn(error && 'border-destructive')}
          />
        );

      case 'number':
        return (
          <Input
            {...commonProps}
            type="number"
            value={(value as number) ?? ''}
            placeholder={field.placeholder}
            onChange={(e) => handleChange(field.name, parseFloat(e.target.value) || '')}
            className={cn(error && 'border-destructive')}
          />
        );

      case 'textarea':
        return (
          <Textarea
            {...commonProps}
            value={(value as string) || ''}
            placeholder={field.placeholder}
            onChange={(e) => handleChange(field.name, e.target.value)}
            className={cn(error && 'border-destructive')}
          />
        );

      case 'select':
        return (
          <Select
            value={(value as string) || ''}
            onValueChange={(v) => handleChange(field.name, v)}
          >
            <SelectTrigger className={cn(error && 'border-destructive')}>
              <SelectValue placeholder={field.placeholder || 'Select...'} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );

      case 'checkbox':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={fieldId}
              checked={!!value}
              onCheckedChange={(checked) => handleChange(field.name, checked)}
            />
            <Label htmlFor={fieldId} className="text-sm font-normal">
              {field.label}
            </Label>
          </div>
        );

      case 'radio':
        return (
          <RadioGroup
            value={(value as string) || ''}
            onValueChange={(v) => handleChange(field.name, v)}
          >
            {field.options?.map((option) => (
              <div key={option.value} className="flex items-center space-x-2">
                <RadioGroupItem value={option.value} id={`${fieldId}-${option.value}`} />
                <Label htmlFor={`${fieldId}-${option.value}`} className="text-sm font-normal">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
        );

      case 'date':
        return (
          <Input
            {...commonProps}
            type="date"
            value={(value as string) || ''}
            onChange={(e) => handleChange(field.name, e.target.value)}
            className={cn(error && 'border-destructive')}
          />
        );

      case 'datetime':
        return (
          <Input
            {...commonProps}
            type="datetime-local"
            value={(value as string) || ''}
            onChange={(e) => handleChange(field.name, e.target.value)}
            className={cn(error && 'border-destructive')}
          />
        );

      case 'file':
        return (
          <Input
            {...commonProps}
            type="file"
            onChange={(e) => handleChange(field.name, e.target.files?.[0] || null)}
            className={cn(error && 'border-destructive')}
          />
        );

      default:
        return (
          <Input
            {...commonProps}
            type="text"
            value={(value as string) || ''}
            placeholder={field.placeholder}
            onChange={(e) => handleChange(field.name, e.target.value)}
          />
        );
    }
  };

  return (
    <form onSubmit={handleSubmit} className={cn('space-y-4', className)}>
      {fields.map((field) => (
        <div key={field.name} className="space-y-2">
          {field.fieldType !== 'checkbox' && (
            <Label htmlFor={`field-${field.name}`}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
          )}
          {renderField(field)}
          {errors[field.name] && (
            <p
              id={`field-${field.name}-error`}
              className="text-sm text-destructive"
              role="alert"
            >
              {errors[field.name]}
            </p>
          )}
        </div>
      ))}

      <div className="flex justify-end space-x-2 pt-4">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            {cancelLabel}
          </Button>
        )}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Submitting...' : submitLabel}
        </Button>
      </div>
    </form>
  );
};

export default DynamicForm;
