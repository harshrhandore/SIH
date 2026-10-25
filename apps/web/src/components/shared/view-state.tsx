"use client";
import { AlertTriangle } from "lucide-react";
import { ApiError } from "@/lib/api";

export function State({
  loading,
  error,
  children,
  retry,
}: {
  loading?: boolean;
  error?: ApiError | null;
  children: React.ReactNode;
  retry?: () => void;
}) {
  if (error)
    return (
      <div className="error" role="alert">
        <AlertTriangle />
        {error.message}
        <small>{error.requestId}</small>
        <button onClick={retry}>Retry</button>
      </div>
    );
  if (loading)
    return (
      <div role="status" aria-label="Loading records" className="skeleton">
        <span />
        <span />
        <span />
      </div>
    );
  return children;
}
