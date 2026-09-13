// Adapted from 21st.dev · joyco/file-dropzone (single file, busy beam, Astra styling)
import { AlertCircle, LoaderCircle, Upload } from "lucide-react"
import type { ReactNode } from "react"

import { BorderBeam } from "@/components/ui/border-beam"
import { Button } from "@/components/ui/button"
import { useFileDrop } from "@/hooks/useFileDrop"
import { cn } from "@/lib/utils"

interface FileDropzoneProps {
  accept: string[]
  maxSizeMB: number
  onFile: (file: File) => void
  title: string
  hint: string
  icon: ReactNode
  busy?: boolean
  busyLabel?: string
  compact?: boolean
  className?: string
}

export function FileDropzone({ accept, maxSizeMB, onFile, title, hint, icon, busy = false, busyLabel = "Working…", compact = false, className }: FileDropzoneProps) {
  const { isDragging, error, dropHandlers, inputProps, openFileDialog } = useFileDrop({ accept, maxSizeMB, onFile })

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div
        {...dropHandlers}
        data-dragging={isDragging || undefined}
        aria-busy={busy}
        className={cn(
          "group relative flex flex-col items-center justify-center gap-3 overflow-hidden rounded-xl border border-dashed border-primary/30 px-6 text-center",
          "bg-[radial-gradient(ellipse_at_center,color-mix(in_oklab,var(--color-primary)_9%,transparent),transparent_70%)]",
          "transition-[border-color,background-color] duration-200 has-[input:focus-visible]:ring-2 has-[input:focus-visible]:ring-ring",
          "data-[dragging=true]:border-primary data-[dragging=true]:bg-primary/10",
          compact ? "min-h-44 py-6" : "min-h-60 py-8",
        )}
      >
        <input {...inputProps} aria-label={title} disabled={busy} />
        {busy && <BorderBeam size={110} duration={3.5} borderWidth={2} />}
        <div
          aria-hidden="true"
          className="grid size-12 place-items-center rounded-full border border-primary/30 bg-background text-primary transition-transform duration-300 ease-out-expo group-data-[dragging=true]:scale-115"
        >
          {busy ? <LoaderCircle className="size-5 animate-spin" /> : icon}
        </div>
        <div aria-live="polite">
          <p className="font-display text-lg font-medium">{busy ? busyLabel : isDragging ? "Release to add" : title}</p>
          <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={openFileDialog} disabled={busy}>
          <Upload aria-hidden="true" />
          Choose file
        </Button>
      </div>
      {error && (
        <p role="alert" className="flex items-center gap-1.5 text-xs text-destructive">
          <AlertCircle className="size-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  )
}
