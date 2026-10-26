"use client";
import { useEffect, useRef, useState } from "react";

export function ReasonDialog({
  title,
  onConfirm,
  onClose,
}: {
  title: string;
  onConfirm: (reason: string) => Promise<void>;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = dialog.current;
    element?.showModal();
    return () => {
      element?.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      aria-labelledby="reason-dialog-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <form
        className="panel padded"
        onSubmit={async (event) => {
          event.preventDefault();
          if (busy) return;
          setBusy(true);
          setError("");
          try {
            await onConfirm(reason.trim());
            onClose();
          } catch (cause) {
            setError((cause as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <h2 id="reason-dialog-title">{title}</h2>
        <p>
          This records a review decision and does not merge student identities.
        </p>
        <label>
          Reason (10–1,000 characters)
          <textarea
            autoFocus
            minLength={10}
            maxLength={1000}
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        {error ? <p role="alert">{error}</p> : null}
        <button type="button" disabled={busy} onClick={onClose}>
          Cancel
        </button>
        <button
          type="submit"
          className="primary"
          disabled={busy || reason.trim().length < 10}
        >
          {busy ? "Recording…" : "Confirm decision"}
        </button>
      </form>
    </dialog>
  );
}
