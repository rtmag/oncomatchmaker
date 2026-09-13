import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from "react"

export interface FileDropOptions {
  /** Extensions (".pdf") and/or MIME types ("application/pdf"). */
  accept: string[]
  maxSizeMB: number
  onFile: (file: File) => void
}

const BYTES_PER_MB = 1024 * 1024

export function useFileDrop({ accept, maxSizeMB, onFile }: FileDropOptions) {
  const inputRef = useRef<HTMLInputElement>(null)
  const dragDepth = useRef(0)
  const [isDragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (!file) return
      const name = file.name.toLowerCase()
      const accepted = accept.some((rule) => (rule.startsWith(".") ? name.endsWith(rule) : file.type === rule))
      if (!accepted) {
        setError(`Choose a ${accept.filter((rule) => rule.startsWith(".")).join(" or ")} file.`)
        return
      }
      if (file.size > maxSizeMB * BYTES_PER_MB) {
        setError(`File exceeds the ${maxSizeMB} MB limit.`)
        return
      }
      setError(null)
      onFile(file)
    },
    [accept, maxSizeMB, onFile],
  )

  const dropHandlers = {
    onDragEnter: (event: DragEvent) => {
      event.preventDefault()
      dragDepth.current += 1
      setDragging(true)
    },
    onDragLeave: (event: DragEvent) => {
      event.preventDefault()
      dragDepth.current = Math.max(0, dragDepth.current - 1)
      if (dragDepth.current === 0) setDragging(false)
    },
    onDragOver: (event: DragEvent) => event.preventDefault(),
    onDrop: (event: DragEvent) => {
      event.preventDefault()
      dragDepth.current = 0
      setDragging(false)
      handleFile(event.dataTransfer.files[0])
    },
  }

  const inputProps = {
    ref: inputRef,
    type: "file" as const,
    accept: accept.join(","),
    className: "sr-only",
    onChange: (event: ChangeEvent<HTMLInputElement>) => {
      handleFile(event.target.files?.[0])
      // Reset so choosing the same file again still fires a change.
      event.target.value = ""
    },
  }

  return { isDragging, error, dropHandlers, inputProps, openFileDialog: () => inputRef.current?.click() }
}
