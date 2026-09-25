import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  padding?: "sm" | "md" | "lg" | "none";
}

export const Card: React.FC<CardProps> = ({
  children,
  className = "",
  padding = "md",
  ...props
}) => {
  const paddingStyles = {
    none: "",
    sm: "p-3",
    md: "p-4 sm:p-5",
    lg: "p-6",
  }[padding];

  return (
    <div
      className={`bg-white border border-slate-200 rounded-lg shadow-sm ${paddingStyles} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = "",
}) => <div className={`border-b border-slate-100 pb-3 mb-4 ${className}`}>{children}</div>;

export const CardTitle: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = "",
}) => <h3 className={`text-base font-semibold text-slate-900 ${className}`}>{children}</h3>;

export const CardDescription: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = "",
}) => <p className={`text-xs text-slate-500 mt-0.5 ${className}`}>{children}</p>;
