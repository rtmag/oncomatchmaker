import { Player } from "@remotion/player"

import { Film } from "./Film.jsx"

const FPS = 30
const DURATION_SECONDS = 90

/** Astra's 90-second design film (1920×1080, procedural Three.js, no audio). */
export default function FilmPlayer() {
  return (
    <Player
      component={Film}
      durationInFrames={FPS * DURATION_SECONDS}
      compositionWidth={1920}
      compositionHeight={1080}
      fps={FPS}
      controls
      autoPlay
      acknowledgeRemotionLicense
      style={{ width: "100%", aspectRatio: "16 / 9" }}
    />
  )
}
