declare module 'three-stdlib' {
  import type { Camera, Vector3 } from 'three'

  export class OrbitControls {
    constructor(camera: Camera, domElement: HTMLElement)
    enableDamping: boolean
    dampingFactor: number
    enablePan: boolean
    minDistance: number
    maxDistance: number
    maxPolarAngle: number
    target: Vector3
    update(): void
    dispose(): void
  }
}
