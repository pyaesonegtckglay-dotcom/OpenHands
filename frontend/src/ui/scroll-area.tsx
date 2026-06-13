import { ReactNode, RefObject } from "react";
import { cn } from "#/utils/utils";

interface ScrollAreaProps {
  children: ReactNode;
  className?: string;
  ref?: RefObject<HTMLDivElement>;
}

export function ScrollArea({ children, className, ref }: ScrollAreaProps) {
  return (
    <div ref={ref} className={cn("overflow-y-auto", className)}>
      {children}
    </div>
  );
}