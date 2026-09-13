import { LoaderCircle } from "lucide-react"
import { Suspense, lazy } from "react"

import { Dialog, DialogContent } from "@/components/ui/dialog"

// Remotion + the composition only download when the film is opened.
const FilmPlayer = lazy(() => import("./FilmPlayer"))

interface FilmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function FilmDialog({ open, onOpenChange }: FilmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {open && (
        <DialogContent
          eyebrow="Product film · 90 seconds"
          title="From molecular detail to a clearer next step"
          description="Design animation with synthetic data. Not a recording of live clinical analysis."
          className="w-[min(75rem,95vw)]"
        >
          <div className="overflow-hidden rounded-xl border border-border bg-stage">
            <Suspense
              fallback={
                <div className="grid aspect-video place-items-center text-muted-foreground" role="status">
                  <LoaderCircle className="size-6 animate-spin text-primary" aria-label="Loading film" />
                </div>
              }
            >
              <FilmPlayer />
            </Suspense>
          </div>
        </DialogContent>
      )}
    </Dialog>
  )
}
