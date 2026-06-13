import { ReactNode, useState } from "react";
import { cn } from "#/utils/utils";

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  children: ReactNode;
  className?: string;
}

export function Select({ value, onValueChange, children, className }: SelectProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className={cn("relative", className)}>
      <div onClick={() => setOpen(!open)}>
        {children}
      </div>
      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover p-1 text-popover-foreground shadow-lg">
          {React.Children.map(children, (child) => {
            if (React.isValidElement<{ value: string; children: ReactNode }>(child)) {
              if (child.type === SelectContent) return null;
              return (
                <div
                  key={child.props.value}
                  className={cn(
                    "relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 px-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground",
                    value === child.props.value && "bg-accent"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    onValueChange(child.props.value);
                    setOpen(false);
                  }}
                >
                  {child.props.children}
                </div>
              );
            }
            return child;
          })}
        </div>
      )}
    </div>
  );
}

interface SelectTriggerProps {
  children: ReactNode;
  className?: string;
}

export function SelectTrigger({ children, className }: SelectTriggerProps) {
  return (
    <div
      className={cn(
        "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
    >
      {children}
    </div>
  );
}

interface SelectValueProps {
  placeholder?: string;
  children?: ReactNode;
}

export function SelectValue({ placeholder, children }: SelectValueProps) {
  return <span>{children || placeholder}</span>;
}

interface SelectContentProps {
  children: ReactNode;
}

export function SelectContent({ children }: SelectContentProps) {
  return <>{children}</>;
}

interface SelectItemProps {
  value: string;
  children: ReactNode;
}

export function SelectItem({ value, children }: SelectItemProps) {
  return (
    <div data-value={value}>
      {children}
    </div>
  );
}