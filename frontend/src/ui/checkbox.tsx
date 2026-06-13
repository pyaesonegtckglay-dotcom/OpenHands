import React from "react";
import { InputHTMLAttributes } from "react";
import { cn } from "#/utils/utils";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  className?: string;
  onCheckedChange?: (checked: boolean) => void;
}

export function Checkbox({ className, onCheckedChange, ...props }: CheckboxProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (props.onChange) {
      props.onChange(e);
    }
    if (onCheckedChange) {
      onCheckedChange(e.target.checked);
    }
  };

  return (
    <input
      type="checkbox"
      className={cn(
        "h-4 w-4 rounded border-gray-300 text-primary focus:ring-2 focus:ring-primary focus:ring-offset-2",
        className
      )}
      {...props}
      onChange={handleChange}
    />
  );
}