import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { createContext, useContext, useEffect, useMemo, useRef } from "react";
import {
  CanvasTexture,
  DoubleSide,
  Group,
  LinearFilter,
  MathUtils,
  SRGBColorSpace,
  Vector3,
} from "three";
import { OrbitControls } from "three-stdlib";
import type {
  ForecastImpact,
  Station,
  TrajectoryPoint,
  Vehicle as LineVehicle,
} from "../types";

interface FactorySceneProps {
  stations: Station[];
  vehicles: LineVehicle[];
  selectedId: string;
  onSelect: (id: string) => void;
  onSelectVehicle?: (vehicle: LineVehicle) => void;
  viewAction: "reset" | "zoom-in" | "zoom-out";
  viewTick: number;
  cameraMode: "orbit" | "walk" | "flythrough";
  onCameraModeChange: (mode: "orbit" | "walk" | "flythrough") => void;
  forecastPoint: TrajectoryPoint | null;
  forecastImpacts: ForecastImpact[];
  currentQueues: Record<string, number>;
  qualityScenarioActive: boolean;
}
const STATUS_COLORS = {
  healthy: "#3ba878",
  warning: "#d69a2d",
  critical: "#d55352",
};
const DEFAULT_CAMERA = new Vector3(22.4, 14.2, 25.2);
const DEFAULT_TARGET = new Vector3(0.4, 0.55, 0);
const CELLS: Array<[number, number, number]> = [
  [-10, 0, 4.6],
  [-6, 0, 4.6],
  [-2, 0, 4.6],
  [2, 0, 4.6],
  [6, 0, 4.6],
  [10, 0, 4.6],
  [-8.8, 0, -4.6],
  [-4.4, 0, -4.6],
  [0, 0, -4.6],
  [4.4, 0, -4.6],
  [8.8, 0, -4.6],
];
const FACTORY_X_LIMIT = 14.2,
  FACTORY_Z_LIMIT = 9.2;
const section = (i: number) =>
  i < 3 ? "Body Shop" : i < 6 ? "Paint Shop" : "Final Assembly";
const StationAnimationProgress = createContext(0);

function Box({
  p,
  s,
  c = "#536570",
  m = 0.55,
  r = 0.42,
}: {
  p: [number, number, number];
  s: [number, number, number];
  c?: string;
  m?: number;
  r?: number;
}) {
  return (
    <mesh position={p} castShadow receiveShadow>
      <boxGeometry args={s} />
      <meshStandardMaterial color={c} metalness={m} roughness={r} />
    </mesh>
  );
}
function Label({
  p,
  tone = "#f7f9f8",
  children,
  mode,
  selected,
  stationIndex,
}: {
  p: [number, number, number];
  tone?: string;
  children: string;
  mode: FactorySceneProps["cameraMode"];
  selected: boolean;
  stationIndex: number;
}) {
  const { camera } = useThree(),
    group = useRef<Group>(null),
    world = useRef(new Vector3());
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas"),
      context = canvas.getContext("2d");
    canvas.width = 1024;
    canvas.height = 224;
    if (context) {
      const x = 8,
        y = 8,
        width = 1008,
        height = 208,
        radius = 26;
      context.beginPath();
      context.moveTo(x + radius, y);
      context.lineTo(x + width - radius, y);
      context.arcTo(x + width, y, x + width, y + radius, radius);
      context.lineTo(x + width, y + height - radius);
      context.arcTo(
        x + width,
        y + height,
        x + width - radius,
        y + height,
        radius,
      );
      context.lineTo(x + radius, y + height);
      context.arcTo(x, y + height, x, y + height - radius, radius);
      context.lineTo(x, y + radius);
      context.arcTo(x, y, x + radius, y, radius);
      context.closePath();
      context.fillStyle = tone;
      context.fill();
      context.strokeStyle = "#b8c7cc";
      context.lineWidth = 5;
      context.stroke();
      let fontSize = 72;
      context.textAlign = "center";
      context.textBaseline = "middle";
      do {
        context.font = `600 ${fontSize}px Inter, Segoe UI, Arial, sans-serif`;
        fontSize -= 2;
      } while (context.measureText(children).width > 880 && fontSize > 38);
      context.fillStyle = "#20343d";
      context.fillText(children, canvas.width / 2, canvas.height / 2 + 3);
    }
    const next = new CanvasTexture(canvas);
    next.colorSpace = SRGBColorSpace;
    next.minFilter = LinearFilter;
    next.magFilter = LinearFilter;
    next.generateMipmaps = false;
    next.needsUpdate = true;
    return next;
  }, [children, tone]);
  useEffect(() => () => texture.dispose(), [texture]);
  useFrame(() => {
    if (group.current && mode !== "walk") {
      group.current.getWorldPosition(world.current);
      group.current.visible =
        selected || camera.position.distanceTo(world.current) < 19;
    }
  });
  if (mode === "walk")
    return (
      <group
        position={[p[0], 1.63, stationIndex < 6 ? -1.04 : 1.04]}
        rotation={[0, stationIndex < 6 ? Math.PI : 0, 0]}
      >
        <Box p={[0, -0.24, 0]} s={[0.04, 0.46, 0.04]} c="#536168" />
        <mesh>
          <planeGeometry args={[1.36, 0.3]} />
          <meshBasicMaterial map={texture} transparent side={DoubleSide} />
        </mesh>
      </group>
    );
  return (
    <group ref={group} position={p}>
      <Box p={[0, -0.22, 0]} s={[0.04, 0.42, 0.04]} c="#536168" />
      <sprite scale={[1.72, 0.39, 1]} renderOrder={8}>
        <spriteMaterial
          map={texture}
          transparent
          depthTest={false}
          depthWrite={false}
        />
      </sprite>
    </group>
  );
}
function Line({
  points,
  color,
}: {
  points: [number, number, number][];
  color: string;
  lineWidth?: number;
}) {
  const [start, end] = points;
  return (
    <Box
      p={[(start[0] + end[0]) / 2, start[1], (start[2] + end[2]) / 2]}
      s={[
        Math.abs(end[0] - start[0]) || 0.05,
        0.012,
        Math.abs(end[2] - start[2]) || 0.05,
      ]}
      c={color}
      m={0.05}
    />
  );
}
function ContactShadows(_: {
  position: [number, number, number];
  opacity?: number;
  scale?: number;
  blur?: number;
  far?: number;
  resolution?: number;
  color?: string;
}) {
  return null;
}

function CameraRig({
  selectedIndex,
  viewAction,
  viewTick,
  mode,
  onModeChange,
}: {
  selectedIndex: number;
  viewAction: FactorySceneProps["viewAction"];
  viewTick: number;
  mode: FactorySceneProps["cameraMode"];
  onModeChange: FactorySceneProps["onCameraModeChange"];
}) {
  const { camera, gl } = useThree();
  const controls = useRef<OrbitControls | null>(null),
    desired = useRef(DEFAULT_CAMERA.clone()),
    target = useRef(DEFAULT_TARGET.clone());
  const savedPosition = useRef(DEFAULT_CAMERA.clone()),
    savedTarget = useRef(DEFAULT_TARGET.clone()),
    walkPosition = useRef(new Vector3(-9, 1.68, 0));
  const keys = useRef(new Set<string>()),
    yaw = useRef(-Math.PI / 2),
    pitch = useRef(-0.05),
    lastTick = useRef(-1),
    transitioning = useRef(true),
    lockedOnce = useRef(false),
    tourStart = useRef<number | null>(null);
  const setControlsEnabled = (enabled: boolean) => {
    if (controls.current)
      (controls.current as unknown as { enabled: boolean }).enabled = enabled;
  };
  useEffect(() => {
    const control = new OrbitControls(camera, gl.domElement);
    control.enableDamping = true;
    control.dampingFactor = 0.065;
    control.enablePan = true;
    const constrained = control as unknown as OrbitControls & {
      panSpeed: number;
      minPolarAngle: number;
    };
    constrained.panSpeed = 0.45;
    constrained.minPolarAngle = Math.PI * 0.14;
    control.minDistance = 7.5;
    control.maxDistance = 42;
    control.maxPolarAngle = Math.PI * 0.44;
    control.target.copy(DEFAULT_TARGET);
    controls.current = control;
    return () => control.dispose();
  }, [camera, gl]);
  useEffect(() => {
    if (mode !== "orbit") return;
    const cell = CELLS[selectedIndex] ?? CELLS[0];
    const topRow = selectedIndex < 6,
      side = cell[0] < 0 ? -1 : 1;
    target.current.set(cell[0], 0.75, cell[2]);
    desired.current.set(
      cell[0] + side * 3.4,
      5.6,
      cell[2] + (topRow ? -7.2 : 7.2),
    );
    transitioning.current = true;
  }, [selectedIndex, mode]);
  useEffect(() => {
    const down = (event: KeyboardEvent) => {
      keys.current.add(event.code);
      if (event.code === "Escape" && mode !== "orbit") onModeChange("orbit");
    };
    const up = (event: KeyboardEvent) => keys.current.delete(event.code);
    const move = (event: MouseEvent) => {
      if (mode === "walk" && document.pointerLockElement === gl.domElement) {
        yaw.current -= event.movementX * 0.002;
        pitch.current = MathUtils.clamp(
          pitch.current - event.movementY * 0.0018,
          -0.72,
          0.55,
        );
      }
    };
    const lockChange = () => {
      if (document.pointerLockElement === gl.domElement)
        lockedOnce.current = true;
      else if (mode === "walk" && lockedOnce.current) onModeChange("orbit");
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("mousemove", move);
    document.addEventListener("pointerlockchange", lockChange);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("mousemove", move);
      document.removeEventListener("pointerlockchange", lockChange);
    };
  }, [gl, mode, onModeChange]);
  useEffect(() => {
    const control = controls.current;
    if (!control) return;
    if (mode === "walk") {
      savedPosition.current.copy(camera.position);
      savedTarget.current.copy(control.target);
      walkPosition.current.set(-12.8, 1.68, 0);
      lockedOnce.current = false;
      setControlsEnabled(false);
      // Pointer lock must start from an intentional scene click, not on mode entry.
    }
    if (mode === "flythrough") {
      savedPosition.current.copy(camera.position);
      savedTarget.current.copy(control.target);
      tourStart.current = performance.now() / 1000;
      setControlsEnabled(false);
    }
    if (mode === "orbit") {
      tourStart.current = null;
      if (document.pointerLockElement === gl.domElement)
        document.exitPointerLock();
      desired.current.copy(savedPosition.current);
      target.current.copy(savedTarget.current);
      transitioning.current = true;
      setControlsEnabled(true);
    }
  }, [camera, gl, mode]);
  useFrame((_, delta) => {
    const control = controls.current;
    if (!control) return;
    if (mode === "walk") {
      const step =
        (keys.current.has("ShiftLeft") || keys.current.has("ShiftRight")
          ? 3.4
          : 1.9) * Math.min(delta, 0.05);
      const forward = new Vector3(
          -Math.sin(yaw.current),
          0,
          -Math.cos(yaw.current),
        ),
        right = new Vector3(forward.z, 0, -forward.x),
        candidate = walkPosition.current.clone();
      if (keys.current.has("KeyW") || keys.current.has("ArrowUp")) candidate.addScaledVector(forward, step);
      if (keys.current.has("KeyS") || keys.current.has("ArrowDown")) candidate.addScaledVector(forward, -step);
      if (keys.current.has("KeyA") || keys.current.has("ArrowLeft")) candidate.addScaledVector(right, -step);
      if (keys.current.has("KeyD") || keys.current.has("ArrowRight")) candidate.addScaledVector(right, step);
      candidate.x = MathUtils.clamp(
        candidate.x,
        -FACTORY_X_LIMIT,
        FACTORY_X_LIMIT,
      );
      candidate.z = MathUtils.clamp(
        candidate.z,
        -FACTORY_Z_LIMIT,
        FACTORY_Z_LIMIT,
      );
      candidate.y = 1.68;
      const blocked = CELLS.some(
        ([x, , z]) =>
          Math.abs(candidate.x - x) < 1.48 && Math.abs(candidate.z - z) < 1.18,
      );
      if (!blocked) walkPosition.current.copy(candidate);
      camera.position.copy(walkPosition.current);
      camera.rotation.order = "YXZ";
      camera.rotation.set(pitch.current, yaw.current, 0);
      return;
    }
    if (mode === "flythrough") {
      if (tourStart.current === null) {
        tourStart.current = performance.now() / 1000;
        return;
      }
      const elapsed = performance.now() / 1000 - tourStart.current;
      const stops = [
        [DEFAULT_CAMERA, DEFAULT_TARGET],
        [new Vector3(-6, 8.2, 15.2), new Vector3(-6, 0.7, 4.6)],
        [new Vector3(12, 8, 14.6), new Vector3(6.2, 0.7, 4.6)],
        [new Vector3(7.8, 7.6, 5.8), new Vector3(-1.8, 0.65, -4.6)],
        [new Vector3(14.2, 8.2, 1.4), new Vector3(7.2, 0.7, -4.6)],
        [DEFAULT_CAMERA, DEFAULT_TARGET],
      ];
      if (elapsed >= 25) {
        onModeChange("orbit");
        return;
      }
      const index = Math.min(4, Math.floor(elapsed / 5)),
        raw = elapsed / 5 - index,
        eased = raw * raw * (3 - 2 * raw);
      camera.position.lerpVectors(stops[index][0], stops[index + 1][0], eased);
      control.target.lerpVectors(stops[index][1], stops[index + 1][1], eased);
      control.update();
      return;
    }
    if (lastTick.current !== viewTick) {
      lastTick.current = viewTick;
      if (viewAction === "reset") {
        desired.current.copy(DEFAULT_CAMERA);
        target.current.copy(DEFAULT_TARGET);
      }
      if (viewAction === "zoom-in")
        desired.current.copy(camera.position).lerp(control.target, 0.14);
      if (viewAction === "zoom-out")
        desired.current
          .copy(camera.position)
          .sub(control.target)
          .multiplyScalar(1.15)
          .add(control.target);
      transitioning.current = true;
    }
    if (transitioning.current) {
      const smooth = 1 - Math.exp(-4.35 * Math.min(delta, 0.05));
      camera.position.lerp(desired.current, smooth);
      control.target.lerp(target.current, smooth);
      if (
        camera.position.distanceTo(desired.current) < 0.03 &&
        control.target.distanceTo(target.current) < 0.03
      )
        transitioning.current = false;
    }
    control.update();
  });
  return null;
}

function Conveyor({
  z,
  from = -13,
  to = 13.2,
}: {
  z: number;
  from?: number;
  to?: number;
}) {
  const slats = Array.from(
    { length: 37 },
    (_, i) => from + 0.45 + i * ((to - from - 0.9) / 36),
  );
  return (
    <group>
      <Box
        p={[(from + to) / 2, 0.13, z - 0.38]}
        s={[to - from, 0.12, 0.1]}
        c="#3f515b"
      />
      <Box
        p={[(from + to) / 2, 0.13, z + 0.38]}
        s={[to - from, 0.12, 0.1]}
        c="#3f515b"
      />
      <Box
        p={[(from + to) / 2, 0.08, z]}
        s={[to - from, 0.1, 0.84]}
        c="#73818a"
        m={0.7}
      />
      {slats.map((x) => (
        <Box
          key={x}
          p={[x, 0.145, z]}
          s={[0.045, 0.04, 0.72]}
          c="#b7c0c4"
          m={0.5}
          r={0.55}
        />
      ))}
    </group>
  );
}
function FlowChevrons({ z }: { z: number }) {
  return (
    <group>
      {[-11, -7, -3, 1, 5, 9].map((x) => (
        <group key={x} position={[x, 0.046, z]}>
          {[-1, 1].map((side) => (
            <mesh
              key={side}
              rotation={[-Math.PI / 2, 0, side * 0.72]}
              position={[side * 0.1, 0, side * 0.1]}
            >
              <planeGeometry args={[0.38, 0.055]} />
              <meshBasicMaterial color="#e1b840" transparent opacity={0.72} />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}
function Fence() {
  return (
    <group>
      {[
        [-1.34, -1.08],
        [1.34, -1.08],
        [-1.34, 1.08],
        [1.34, 1.08],
      ].map(([x, z]) => (
        <mesh key={`${x}${z}`} position={[x, 0.86, z]} castShadow>
          <cylinderGeometry args={[0.045, 0.055, 1.72, 8]} />
          <meshStandardMaterial
            color="#e4b443"
            metalness={0.42}
            roughness={0.48}
          />
        </mesh>
      ))}
      {[-1.08, 1.08].map((z) => (
        <group key={z}>
          {[0.54, 1.2].map((y) => (
            <Box key={y} p={[0, y, z]} s={[2.68, 0.045, 0.045]} c="#7c8b91" />
          ))}
        </group>
      ))}
    </group>
  );
}

function Robot({
  p,
  rot = 0,
  active,
  progress,
  phase = 0,
}: {
  p: [number, number, number];
  rot?: number;
  active: boolean;
  progress?: number;
  phase?: number;
}) {
  const contextProgress = useContext(StationAnimationProgress),
    shoulder = useRef<Group>(null),
    elbow = useRef<Group>(null),
    displayed = useRef(0);
  useFrame((_, delta) => {
    const target = active ? (progress ?? contextProgress) : 0;
    displayed.current = MathUtils.damp(
      displayed.current,
      target,
      6.2,
      Math.min(delta, 0.05),
    );
    const cycle = (displayed.current + phase * 0.08) % 1,
      approach =
        cycle < 0.25
          ? cycle / 0.25
          : cycle < 0.65
            ? 1
            : cycle < 0.85
              ? 1 - (cycle - 0.65) / 0.2
              : 0,
      weld =
        cycle > 0.25 && cycle < 0.65
          ? Math.sin((cycle - 0.25) * Math.PI * 10) * 0.12
          : 0;
    if (shoulder.current)
      shoulder.current.rotation.z = MathUtils.damp(
        shoulder.current.rotation.z,
        -0.62 + approach * 0.27 + weld,
        9,
        Math.min(delta, 0.05),
      );
    if (elbow.current)
      elbow.current.rotation.z = MathUtils.damp(
        elbow.current.rotation.z,
        0.88 - approach * 0.34 - weld * 0.7,
        9,
        Math.min(delta, 0.05),
      );
  });
  return (
    <group position={p} rotation={[0, rot, 0]}>
      <mesh castShadow position={[0, 0.13, 0]}>
        <cylinderGeometry args={[0.28, 0.34, 0.26, 14]} />
        <meshStandardMaterial
          color="#2f4651"
          metalness={0.66}
          roughness={0.28}
        />
      </mesh>
      <group ref={shoulder} position={[0, 0.3, 0]}>
        <mesh position={[0, 0.15, 0]} castShadow>
          <sphereGeometry args={[0.22, 14, 12]} />
          <meshStandardMaterial
            color="#d7a93e"
            metalness={0.35}
            roughness={0.37}
          />
        </mesh>
        <mesh
          position={[0.43, 0.15, 0]}
          rotation={[0, 0, Math.PI / 2]}
          castShadow
        >
          <cylinderGeometry args={[0.11, 0.14, 0.78, 12]} />
          <meshStandardMaterial
            color="#e0b345"
            metalness={0.34}
            roughness={0.38}
          />
        </mesh>
        <group ref={elbow} position={[0.79, 0.15, 0]}>
          <mesh castShadow>
            <sphereGeometry args={[0.16, 12, 10]} />
            <meshStandardMaterial
              color="#334d58"
              metalness={0.62}
              roughness={0.3}
            />
          </mesh>
          <mesh
            position={[0.32, -0.04, 0]}
            rotation={[0, 0, Math.PI / 2.45]}
            castShadow
          >
            <cylinderGeometry args={[0.085, 0.11, 0.62, 10]} />
            <meshStandardMaterial
              color="#d4a941"
              metalness={0.32}
              roughness={0.4}
            />
          </mesh>
          <mesh position={[0.58, -0.28, 0]} castShadow>
            <cylinderGeometry args={[0.09, 0.1, 0.3, 10]} />
            <meshStandardMaterial
              color="#2e434d"
              metalness={0.7}
              roughness={0.28}
            />
          </mesh>
        </group>
      </group>
    </group>
  );
}

function Vehicle({
  stage,
  color,
  variant,
}: {
  stage: "body" | "painted" | "complete";
  color: string;
  variant: string;
}) {
  const suv = variant === "SUV",
    ev = variant === "EV",
    bh = suv ? 0.31 : 0.25,
    ch = suv ? 0.42 : 0.32,
    bc = stage === "body" ? "#9eabb3" : color;
  return (
    <group position={[0, 0.52, 0]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[1.65, bh, 0.74]} />
        <meshStandardMaterial
          color={bc}
          metalness={stage === "body" ? 0.88 : 0.52}
          roughness={stage === "body" ? 0.3 : 0.28}
        />
      </mesh>
      <mesh position={[-0.45, bh * 0.35, 0]} castShadow>
        <boxGeometry args={[0.52, bh * 0.62, 0.7]} />
        <meshStandardMaterial
          color={bc}
          metalness={stage === "body" ? 0.82 : 0.48}
          roughness={0.3}
        />
      </mesh>
      <group position={[0.08, bh / 2 + ch / 2 - 0.02, 0]}>
        <mesh castShadow>
          <boxGeometry args={[suv ? 0.86 : 0.78, ch, suv ? 0.69 : 0.65]} />
          <meshStandardMaterial
            color={stage === "body" ? "#b8c2c7" : "#243a46"}
            metalness={stage === "body" ? 0.7 : 0.35}
            roughness={stage === "body" ? 0.34 : 0.14}
            transparent={stage !== "body"}
            opacity={stage === "body" ? 1 : 0.82}
          />
        </mesh>
        {stage !== "body" && (
          <mesh position={[0.02, 0.02, 0.331]} rotation={[0, 0.18, 0]}>
            <planeGeometry args={[0.55, ch * 0.72]} />
            <meshStandardMaterial color="#a5d0d9" transparent opacity={0.54} />
          </mesh>
        )}
      </group>
      {ev && (
        <Box p={[-0.86, 0.02, 0]} s={[0.05, 0.1, 0.51]} c="#49aab5" m={0.2} />
      )}{" "}
      {stage === "complete" &&
        [-0.56, 0.56].map((x) =>
          [-0.43, 0.43].map((z) => (
            <group
              key={`${x}${z}`}
              position={[x, -bh / 2 - 0.04, z]}
              rotation={[Math.PI / 2, 0, 0]}
            >
              <mesh>
                <cylinderGeometry args={[0.16, 0.16, 0.1, 16]} />
                <meshStandardMaterial color="#202a30" roughness={0.74} />
              </mesh>
              <mesh position={[0, 0, 0.055]}>
                <cylinderGeometry args={[0.075, 0.075, 0.012, 12]} />
                <meshStandardMaterial
                  color="#adb8bd"
                  metalness={0.72}
                  roughness={0.25}
                />
              </mesh>
            </group>
          )),
        )}
    </group>
  );
}
function LiveVehicle({
  vehicle,
  stations,
  vehicles,
  onSelect,
}: {
  vehicle: LineVehicle;
  stations: Station[];
  vehicles: LineVehicle[];
  onSelect?: (v: LineVehicle) => void;
}) {
  const ref = useRef<Group>(null),
    target = useRef(new Vector3()),
    lastTarget = useRef(new Vector3());
  const find = (id: string | null) => stations.findIndex((s) => s.id === id),
    current = find(vehicle.current_station),
    next = find(vehicle.next_station),
    a = CELLS[Math.max(0, current)],
    b = CELLS[Math.max(0, next)];
  const stage =
    vehicle.production_stage === "Body"
      ? "body"
      : vehicle.production_stage === "Paint"
        ? "painted"
        : "complete";
  
  // Phase 4: Quality indicator
  const showQualityIndicator = vehicle.quality_risk >= 0.35; // WATCH threshold
  const qualityColor = vehicle.quality_risk >= 0.82 ? "#d55352" : vehicle.quality_risk >= 0.60 ? "#f08c37" : "#4f85a6";
  
  if (vehicle.status === "TRANSFERRING" && current >= 0 && next >= 0) {
    const t = MathUtils.smoothstep(vehicle.progress, 0, 1);
    if (current === 5 && next === 6) {
      const one = 1 - t,
        control = new Vector3(12.4, 0.12, 0);
      target.current.set(
        one * one * a[0] + 2 * one * t * control.x + t * t * b[0],
        0.12,
        one * one * a[2] + 2 * one * t * control.z + t * t * b[2],
      );
    } else
      target.current.set(
        MathUtils.lerp(a[0], b[0], t),
        0.12,
        MathUtils.lerp(a[2], b[2], t),
      );
  } else if (vehicle.status === "BUFFERED") {
    const peers = vehicles
        .filter(
          (v) =>
            v.status === "BUFFERED" &&
            (vehicle.buffer_id
              ? v.buffer_id === vehicle.buffer_id
              : v.current_station === vehicle.current_station),
        )
        .sort((x, y) => x.vehicle_id.localeCompare(y.vehicle_id)),
      rank = Math.max(
        0,
        peers.findIndex((v) => v.vehicle_id === vehicle.vehicle_id),
      );
    if (vehicle.buffer_id === "BODY-ACC")
      target.current.set(-1.5 + rank, 0.12, 7.25);
    else if (vehicle.buffer_id === "PBS")
      target.current.set(12.45, 0.12, 3.2 - rank * 1.6);
    else target.current.set(a[0] - 1.55 - rank * 0.9, 0.12, a[2]);
  } else target.current.set(a[0], 0.12, a[2]);
  useFrame((_, delta) => {
    const group = ref.current;
    if (!group) return;
    lastTarget.current.copy(group.position);
    const dt = Math.min(delta, 0.05),
      smooth = 1 - Math.exp(-7.2 * dt);
    group.position.lerp(target.current, smooth);
    const dx = group.position.x - lastTarget.current.x,
      dz = group.position.z - lastTarget.current.z;
    if (Math.abs(dx) + Math.abs(dz) > 0.001)
      group.rotation.y = MathUtils.damp(
        group.rotation.y,
        -Math.atan2(dz, dx),
        8.5,
        dt,
      );
  });
  return (
    <group
      ref={ref}
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.(vehicle);
      }}
    >
      {/* Phase 4: Subtle quality indicator */}
      {showQualityIndicator && (
        <group position={[0, 0.15, 0]}>
          {[0, 0.5, 1, 1.5, 2, 2.5].map((angle) => (
            <mesh key={angle} rotation={[0, angle, 0]} position={[0.8, 0, 0]}>
              <boxGeometry args={[0.08, 0.02, 0.02]} />
              <meshBasicMaterial color={qualityColor} transparent opacity={0.4} />
            </mesh>
          ))}
        </group>
      )}
      <Vehicle
        stage={stage}
        color={vehicle.body_color}
        variant={vehicle.variant}
      />
    </group>
  );
}

function Arch({ type }: { type: "trim" | "adas" | "inspection" }) {
  return (
    <group>
      {[-0.92, 0.92].map((x) => (
        <Box key={x} p={[x, 1.12, 0]} s={[0.13, 2.12, 0.2]} c="#536a74" />
      ))}
      <Box p={[0, 2.12, 0]} s={[2.02, 0.16, 0.24]} c="#536a74" />
      {type === "trim" &&
        [-0.88, 0.88].map((x) => (
          <Box
            key={x}
            p={[x, 0.62, 0.72]}
            s={[0.46, 0.75, 0.24]}
            c="#d3d6d4"
            m={0.2}
          />
        ))}
      {type === "adas" &&
        [-0.52, 0.52].map((x) => (
          <mesh key={x} position={[x, 1.35, -0.7]}>
            <circleGeometry args={[0.26, 20]} />
            <meshStandardMaterial
              color="#b4e3e4"
              emissive="#256873"
              emissiveIntensity={0.32}
            />
          </mesh>
        ))}
      {type === "inspection" &&
        [-0.56, 0.56].map((x) => (
          <Box
            key={x}
            p={[x, 1.22, -0.68]}
            s={[0.52, 0.7, 0.08]}
            c="#dce6e5"
            m={0.15}
          />
        ))}
    </group>
  );
}

function ProcessMotion({
  index,
  station,
}: {
  index: number;
  station: Station;
}) {
  const primary = useRef<Group>(null),
    secondary = useRef<Group>(null),
    progress = useRef(0);
  const target =
    station.operational_state === "BLOCKED"
      ? 1
      : station.operational_state === "RUNNING"
        ? station.cycle_progress
        : 0;
  useFrame((_, delta) => {
    progress.current = MathUtils.damp(
      progress.current,
      target,
      5.2,
      Math.min(delta, 0.05),
    );
    const p = progress.current,
      engage =
        p < 0.2 ? p / 0.2 : p < 0.78 ? 1 : Math.max(0, 1 - (p - 0.78) / 0.22);
    if (!primary.current) return;
    if (index === 0) {
      primary.current.scale.x = 1 - engage * 0.34;
      primary.current.position.y = 0.56 + engage * 0.05;
      if (secondary.current)
        secondary.current.position.y = 2.04 - engage * 0.14;
    }
    if (index === 1) {
      const weld =
        p > 0.25 && p < 0.65 ? Math.max(0.05, Math.sin(p * Math.PI * 34)) : 0;
      primary.current.scale.setScalar(weld);
    }
    if (index === 2) primary.current.position.y = 0.38 + engage * 0.32;
    if (index === 3) primary.current.position.x = -0.82 + p * 1.64;
    if (index === 4) {
      primary.current.position.x = Math.sin(p * Math.PI * 2) * 0.62;
      primary.current.position.y = 0.72 + engage * 0.18;
    }
    if (index === 5) primary.current.scale.x = 0.25 + engage * 0.75;
    if (index === 6)
      primary.current.position.x = Math.sin(p * Math.PI * 2) * 0.7;
    if (index === 7) {
      const lift =
        p < 0.2
          ? 0
          : p < 0.55
            ? (p - 0.2) / 0.35
            : p < 0.78
              ? 1
              : Math.max(0, 1 - (p - 0.78) / 0.22);
      primary.current.position.y = 0.34 + lift * 0.62;
      if (secondary.current) secondary.current.position.y = 1.45 - lift * 0.18;
    }
    if (index === 8)
      primary.current.scale.set(1 - engage * 0.28, 1, 1 - engage * 0.28);
    if (index >= 9) primary.current.position.x = -0.72 + p * 1.44;
  });
  if (index === 0)
    return (
      <group>
        <group ref={primary}>
          {[-1, 1].map((x) => (
            <Box
              key={x}
              p={[x, 0.56, 0]}
              s={[0.22, 0.34, 0.9]}
              c="#d2a93f"
              m={0.42}
            />
          ))}
        </group>
        <group ref={secondary}>
          <Box p={[0, 0, 0]} s={[1.5, 0.1, 0.84]} c="#8b9ca2" />
        </group>
      </group>
    );
  if (index === 1)
    return (
      <group ref={primary} scale={0}>
        <pointLight intensity={2.2} distance={2.2} color="#bfefff" />
        {[-0.28, 0.28].map((x) => (
          <mesh key={x} position={[x, 0.72, 0]}>
            <sphereGeometry args={[0.035, 8, 6]} />
            <meshStandardMaterial
              color="#e8fbff"
              emissive="#a8eaff"
              emissiveIntensity={2}
            />
          </mesh>
        ))}
      </group>
    );
  if (index === 2)
    return (
      <group ref={primary}>
        <Box p={[0, 0, 0]} s={[1.72, 0.12, 0.8]} c="#9caeb4" m={0.68} />
      </group>
    );
  if (index === 3)
    return (
      <group ref={primary}>
        {[-0.36, 0, 0.36].map((z) => (
          <mesh key={z} position={[0, 0.9, z]}>
            <sphereGeometry args={[0.055, 8, 6]} />
            <meshStandardMaterial
              color="#6cc3b4"
              emissive="#286d62"
              emissiveIntensity={0.7}
            />
          </mesh>
        ))}
      </group>
    );
  if (index === 4)
    return (
      <group ref={primary}>
        <Box p={[0, 0.9, -0.55]} s={[0.12, 1.15, 0.12]} c="#4d6974" />
        {[-0.35, 0, 0.35].map((z) => (
          <mesh key={z} position={[0, 0.38, z]} rotation={[0, 0, Math.PI / 2]}>
            <coneGeometry args={[0.06, 0.16, 10]} />
            <meshStandardMaterial
              color="#7bc1cc"
              emissive="#235d68"
              emissiveIntensity={0.35}
            />
          </mesh>
        ))}
      </group>
    );
  if (index === 5)
    return (
      <group ref={primary}>
        {[-0.55, 0, 0.55].map((z) => (
          <Box
            key={z}
            p={[0, 1.18, z]}
            s={[1.8, 0.055, 0.08]}
            c="#c77b52"
            m={0.18}
          />
        ))}
      </group>
    );
  if (index === 6)
    return (
      <group ref={primary}>
        <Box p={[0, 1.72, 0]} s={[0.55, 0.16, 0.28]} c="#d6aa3d" />
        <Box p={[0, 1.25, 0]} s={[0.07, 0.8, 0.07]} c="#536a74" />
      </group>
    );
  if (index === 7)
    return (
      <group>
        <group ref={primary}>
          <Box p={[0, 0, 0]} s={[1.72, 0.2, 0.78]} c="#263d47" />
          <Box p={[0, 0.16, 0]} s={[1.3, 0.08, 0.56]} c="#4c6873" />
        </group>
        <group ref={secondary}>
          <Box p={[0, 0, 0]} s={[1.55, 0.12, 0.72]} c="#9ba9ae" m={0.72} />
        </group>
      </group>
    );
  if (index === 8)
    return (
      <group ref={primary}>
        {[-0.82, 0.82].map((x) =>
          [-0.5, 0.5].map((z) => (
            <group key={`${x}${z}`} position={[x, 0.55, z]}>
              <Box p={[0, 0, 0]} s={[0.18, 0.18, 0.18]} c="#d3a83e" />
              <Box p={[0, -0.32, 0]} s={[0.08, 0.55, 0.08]} c="#455d67" />
            </group>
          )),
        )}
      </group>
    );
  return (
    <group ref={primary}>
      <mesh position={[0, 1.02, 0]}>
        <boxGeometry args={[0.035, 1.55, 1.55]} />
        <meshStandardMaterial
          color={index === 9 ? "#5fc3ce" : "#80b7c1"}
          emissive={index === 9 ? "#23707a" : "#325c65"}
          emissiveIntensity={0.65}
          transparent
          opacity={0.58}
        />
      </mesh>
    </group>
  );
}
function Equipment({ i, active }: { i: number; active: boolean }) {
  if (i === 0)
    return (
      <group>
        <Box p={[0, 0.2, 0]} s={[2.45, 0.22, 1.35]} c="#344d58" />
        <Box p={[-0.82, 1.18, 0]} s={[0.14, 1.95, 0.14]} c="#405965" />
        <Box p={[0.82, 1.18, 0]} s={[0.14, 1.95, 0.14]} c="#405965" />
        <Box p={[0, 2.08, 0]} s={[1.8, 0.16, 0.16]} c="#405965" />
        <Robot p={[-1.02, 0, -0.55]} rot={0.38} active={active} />
        <Robot p={[1.02, 0, 0.55]} rot={-2.7} active={active} phase={2.5} />
      </group>
    );
  if (i === 1)
    return (
      <group>
        <Fence />
        <Box p={[0, 0.22, 0]} s={[1.75, 0.25, 0.98]} c="#3b5360" />
        {[
          [-0.98, -0.68, 0.42],
          [0.98, -0.68, 2.55],
          [-0.98, 0.68, -0.42],
          [0.98, 0.68, -2.55],
        ].map(([x, z, r], n) => (
          <Robot
            key={n}
            p={[x, 0, z]}
            rot={r}
            active={active}
            phase={n * 1.4}
          />
        ))}
      </group>
    );
  if (i === 2)
    return (
      <group>
        <Box p={[0, 0.32, 0]} s={[2.45, 0.24, 1.22]} c="#4a616b" />
        {[-0.95, 0.95].map((x) => (
          <group key={x}>
            <Box p={[x, 0.72, 0]} s={[0.18, 0.82, 0.82]} c="#596e78" />
            <Box p={[x, 1.18, 0]} s={[0.35, 0.1, 0.9]} c="#aebcc0" />
          </group>
        ))}
        <Box p={[0, 1.68, 0]} s={[2.3, 0.14, 0.95]} c="#5f747c" />
      </group>
    );
  if (i === 3)
    return (
      <group>
        <Box p={[0, 1.05, 0]} s={[2.58, 1.95, 1.58]} c="#79909a" m={0.38} />
        <Box p={[-1.31, 0.73, 0]} s={[0.08, 0.94, 1.02]} c="#344b55" />
        <Box p={[1.31, 0.73, 0]} s={[0.08, 0.94, 1.02]} c="#344b55" />
        <Box p={[0, 2.22, 0]} s={[2.36, 0.18, 0.9]} c="#526872" />
      </group>
    );
  if (i === 4)
    return (
      <group>
        <Box p={[0, 0.15, 0]} s={[2.62, 0.16, 1.72]} c="#526b74" />
        {[-1.18, 1.18].map((x) => (
          <Box
            key={x}
            p={[x, 1.02, 0]}
            s={[0.08, 1.78, 1.48]}
            c="#d4e1e1"
            m={0.25}
          />
        ))}
        <mesh position={[0, 1.02, -0.76]}>
          <boxGeometry args={[2.28, 1.58, 0.045]} />
          <meshPhysicalMaterial
            color="#9fc7ce"
            transparent
            opacity={0.28}
            roughness={0.18}
          />
        </mesh>
        <Box p={[0, 2.02, 0]} s={[2.52, 0.26, 1.56]} c="#e1e8e7" m={0.22} />
        <Box p={[0, 2.34, 0]} s={[1.9, 0.16, 0.62]} c="#485d66" />
      </group>
    );
  if (i === 5)
    return (
      <group>
        <Box p={[0, 1.05, 0]} s={[2.8, 1.96, 1.74]} c="#786963" m={0.28} />
        <Box p={[-1.42, 0.74, 0]} s={[0.07, 0.98, 1.1]} c="#2f434b" />
        <Box p={[1.42, 0.74, 0]} s={[0.07, 0.98, 1.1]} c="#2f434b" />
        <mesh position={[0, 1.02, -0.88]}>
          <boxGeometry args={[2.25, 1.38, 0.04]} />
          <meshStandardMaterial
            color="#4e403c"
            emissive="#3a221c"
            emissiveIntensity={0.35}
          />
        </mesh>
        <Box p={[0, 2.22, 0]} s={[2.86, 0.14, 1.78]} c="#4a5b60" />
      </group>
    );
  if (i === 6) return <Arch type="trim" />;
  if (i === 7)
    return (
      <group>
        <Box p={[0, 0.2, 0]} s={[2.7, 0.22, 1.35]} c="#354e59" />
        <Box p={[0, 0.53, 0]} s={[1.75, 0.18, 0.72]} c="#273d47" />
        <Box p={[-0.92, 1.12, 0]} s={[0.16, 1.8, 0.18]} c="#7e9095" />
        <Box p={[0.92, 1.12, 0]} s={[0.16, 1.8, 0.18]} c="#7e9095" />
        <Box p={[0, 2, 0]} s={[2.05, 0.16, 0.24]} c="#536b73" />
        <Robot p={[-1.12, 0, 0.48]} rot={0.62} active={active} phase={0.7} />
        <Robot p={[1.12, 0, -0.48]} rot={-2.5} active={active} phase={3.2} />
      </group>
    );
  if (i === 8)
    return (
      <group>
        <Box p={[0, 0.22, 0]} s={[2.3, 0.19, 1.22]} c="#4d6670" />
        {[-0.67, 0.67].map((x) =>
          [-0.44, 0.44].map((z) => (
            <group key={`${x}${z}`} position={[x, 0.25, z]}>
              <mesh>
                <cylinderGeometry args={[0.19, 0.19, 0.18, 12]} />
                <meshStandardMaterial color="#334e59" metalness={0.6} />
              </mesh>
              <Box p={[0, 0.46, 0]} s={[0.13, 0.52, 0.13]} c="#e0b343" />
            </group>
          )),
        )}
      </group>
    );
  return <Arch type={i === 9 ? "adas" : "inspection"} />;
}

function StationCell({
  station,
  i,
  selected,
  onSelect,
  cameraMode,
  forecast,
  qualityScenarioActive,
}: {
  station: Station;
  i: number;
  selected: boolean;
  onSelect: () => void;
  cameraMode: FactorySceneProps["cameraMode"];
  forecast: boolean;
  qualityScenarioActive: boolean;
}) {
  const { gl } = useThree(),
    p = CELLS[i],
    active = station.operational_state === "RUNNING",
    color = STATUS_COLORS[station.health],
    animationProgress =
      station.operational_state === "BLOCKED"
        ? 1
        : active
          ? station.cycle_progress
          : 0;
  return (
    <group
      position={p}
      onClick={(e) => {
        e.stopPropagation();
        if (document.pointerLockElement !== gl.domElement) onSelect();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        if (document.pointerLockElement !== gl.domElement)
          gl.domElement.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        gl.domElement.style.cursor = "default";
      }}
    >
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0.018, 0]}
        receiveShadow
      >
        <planeGeometry args={[2.75, 2.12]} />
        <meshStandardMaterial
          color={section(i) === "Paint Shop" ? "#d9e2e2" : "#dde4e6"}
          roughness={0.88}
        />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.032, 0]}>
        <ringGeometry args={[1.36, 1.43, 48]} />
        <meshBasicMaterial
          color={selected ? "#149db6" : color}
          transparent
          opacity={selected ? 0.92 : 0.62}
        />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.036, 0]}>
        <ringGeometry args={[1.47, 1.49, 48]} />
        <meshBasicMaterial
          color={selected ? "#a7e7ed" : "#fff"}
          transparent
          opacity={selected ? 0.75 : 0.22}
        />
      </mesh>
      {forecast && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.041, 0]}>
          <ringGeometry args={[1.54, 1.59, 64]} />
          <meshBasicMaterial color="#d39a38" transparent opacity={0.78} />
        </mesh>
      )}
      {qualityScenarioActive && i === 1 && (
        <group position={[0.86, 0.3, -0.78]}>
          <mesh><sphereGeometry args={[0.12, 16, 16]} /><meshBasicMaterial color="#d99432" /></mesh>
          <mesh position={[0, 0.1, 0]}><cylinderGeometry args={[0.025, 0.025, 0.4, 10]} /><meshBasicMaterial color="#d99432" transparent opacity={0.7} /></mesh>
        </group>
      )}
      <StationAnimationProgress.Provider value={animationProgress}>
        <group position={[0, 0.05, 0]}>
          <Equipment i={i} active={active} />
        </group>
      </StationAnimationProgress.Provider>
      <Label
        p={[0, 2.58, 0]}
        mode={cameraMode}
        selected={selected}
        stationIndex={i}
        tone={
          section(i) === "Body Shop"
            ? "#f3f7f7"
            : section(i) === "Paint Shop"
              ? "#f5f8f5"
              : "#f8f9f3"
        }
      >
        {station.name}
      </Label>
    </group>
  );
}

function FactoryArchitecture() {
  const columns = [
    [-14.6, -9.4],
    [-14.6, 9.4],
    [14.6, -9.4],
    [14.6, 9.4],
    [-5, -9.4],
    [-5, 9.4],
    [5, -9.4],
    [5, 9.4],
  ];
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[31, 21]} />
        <meshStandardMaterial color="#cdd4d5" roughness={0.96} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.006, 4.6]}>
        <planeGeometry args={[27.6, 1.7]} />
        <meshStandardMaterial color="#bfc9cb" roughness={0.93} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.006, -4.6]}>
        <planeGeometry args={[27.6, 1.7]} />
        <meshStandardMaterial color="#c2cccd" roughness={0.93} />
      </mesh>
      <Line
        points={[
          [-13.5, 0.035, 3.35],
          [13.5, 0.035, 3.35],
        ]}
        color="#e9bd43"
        lineWidth={1.4}
      />
      <Line
        points={[
          [-13.5, 0.035, 5.85],
          [13.5, 0.035, 5.85],
        ]}
        color="#f3f0df"
        lineWidth={1.1}
      />
      <Line
        points={[
          [-13.5, 0.035, -5.85],
          [13.5, 0.035, -5.85],
        ]}
        color="#f3f0df"
        lineWidth={1.1}
      />
      <Line
        points={[
          [-13.5, 0.035, -3.35],
          [13.5, 0.035, -3.35],
        ]}
        color="#e9bd43"
        lineWidth={1.4}
      />
      <Conveyor z={4.6} />
      <Conveyor z={-4.6} />
      {columns.map(([x, z]) => (
        <group key={`${x}${z}`}>
          <Box p={[x, 2.35, z]} s={[0.24, 4.7, 0.24]} c="#738088" m={0.45} />
          <Box p={[x, 4.7, z]} s={[0.52, 0.14, 0.52]} c="#56646b" />
        </group>
      ))}
      {[-9.4, 9.4].map((z) => (
        <Box
          key={z}
          p={[0, 4.52, z]}
          s={[29.4, 0.23, 0.22]}
          c="#536168"
          m={0.6}
        />
      ))}
      {[-10, -3.3, 3.3, 10].map((x) => (
        <Box
          key={x}
          p={[x, 4.68, 0]}
          s={[0.11, 0.11, 18.8]}
          c="#647179"
          m={0.6}
        />
      ))}
      {[
        [-13.5, 8.6],
        [-13.5, -8.5],
        [2, 8.7],
        [13.5, -8.4],
      ].map(([x, z], i) => (
        <group key={i}>
          <Box p={[x, 0.42, z]} s={[0.55, 0.84, 0.42]} c="#788991" m={0.28} />
          <mesh position={[x, 0.6, z + 0.216]}>
            <circleGeometry args={[0.045, 10]} />
            <meshStandardMaterial
              color={i % 2 ? "#4db28a" : "#e0b242"}
              emissive={i % 2 ? "#1c5c49" : "#6d4c12"}
              emissiveIntensity={0.5}
            />
          </mesh>
        </group>
      ))}
      {[-13.2, 13.2].map((x) => (
        <group key={x}>
          {[-7.8, 7.8].map((z) => (
            <mesh key={z} position={[x, 0.46, z]}>
              <cylinderGeometry args={[0.13, 0.15, 0.88, 10]} />
              <meshStandardMaterial
                color="#e5b343"
                metalness={0.28}
                roughness={0.45}
              />
            </mesh>
          ))}
        </group>
      ))}
    </group>
  );
}
function BufferBays() {
  return (
    <group>
      {[-1.5, -0.5, 0.5, 1.5].map((x, rank) => (
        <mesh
          key={`body-${rank}`}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[x, 0.014, 7.25]}
        >
          <planeGeometry args={[0.82, 1.42]} />
          <meshBasicMaterial color="#dce7e5" transparent opacity={0.82} />
        </mesh>
      ))}
      {[3.2, 1.6, 0, -1.6, -3.2].map((z, rank) => (
        <mesh
          key={`pbs-${rank}`}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[12.45, 0.014, z]}
        >
          <planeGeometry args={[1.42, 0.82]} />
          <meshBasicMaterial color="#e3e8df" transparent opacity={0.82} />
        </mesh>
      ))}
    </group>
  );
}
function ForecastLayer({
  stations,
  sourceId,
  point,
  impacts,
  currentQueues,
}: {
  stations: Station[];
  sourceId: string;
  point: TrajectoryPoint;
  impacts: ForecastImpact[];
  currentQueues: Record<string, number>;
}) {
  const sourceIndex = stations.findIndex((station) => station.id === sourceId);
  const impactedIndices = impacts
    .filter((impact) => impact.entity_type === "STATION")
    .map((impact) =>
      stations.findIndex((station) => station.id === impact.entity_id),
    )
    .filter((index) => index >= 0);
  const edges = new Set<string>();
  impactedIndices.forEach((target) => {
    const low = Math.min(sourceIndex, target),
      high = Math.max(sourceIndex, target);
    for (let index = low; index < high; index += 1)
      edges.add(`${index}-${index + 1}`);
  });
  return (
    <group>
      {[...edges].map((edge) => {
        const [from, to] = edge.split("-").map(Number),
          a = CELLS[from],
          b = CELLS[to];
        return (
          <Line
            key={edge}
            points={[
              [a[0], 0.075, a[2]],
              [b[0], 0.075, b[2]],
            ]}
            color="#d39a38"
          />
        );
      })}
      {stations.flatMap((station, index) => {
        const projected = point.station_queues[station.id] ?? 0,
          current = currentQueues[station.id] ?? 0,
          extra = Math.min(3, Math.max(0, projected - current));
        return Array.from({ length: extra }, (_, rank) => {
          let position: [number, number, number] = [
            CELLS[index][0] - 1.55 - rank * 0.72,
            0.48,
            CELLS[index][2],
          ];
          if (station.id === "PAINT-01")
            position = [-1.5 + (current + rank), 0.48, 7.25];
          if (station.id === "FA-01")
            position = [12.45, 0.48, 3.2 - (current + rank) * 1.6];
          return (
            <group key={`${station.id}-ghost-${rank}`} position={position}>
              <mesh>
                <boxGeometry args={[1.5, 0.48, 0.68]} />
                <meshBasicMaterial
                  color="#d39a38"
                  wireframe
                  transparent
                  opacity={0.38}
                />
              </mesh>
            </group>
          );
        });
      })}
    </group>
  );
}
function Scene({
  stations,
  vehicles,
  selectedId,
  onSelect,
  onSelectVehicle,
  viewAction,
  viewTick,
  cameraMode,
  onCameraModeChange,
  forecastPoint,
  forecastImpacts,
  currentQueues,
  qualityScenarioActive,
}: FactorySceneProps) {
  const selected = Math.max(
    0,
    stations.findIndex((s) => s.id === selectedId),
  );
  const forecastIds = new Set(
    forecastImpacts.map((impact) => impact.entity_id),
  );
  return (
    <>
      <color attach="background" args={["#dbe4e6"]} />
      <hemisphereLight args={["#f6fbfb", "#62717a", 1.55]} />
      <directionalLight
        position={[12, 16, 10]}
        intensity={2.35}
        castShadow
        shadow-mapSize={[1536, 1536]}
        shadow-bias={-0.0002}
      />
      <directionalLight position={[-12, 8, -8]} intensity={0.65} />
      <pointLight
        position={[0, 6, 0]}
        intensity={5.4}
        distance={30}
        color="#f5f7ef"
      />
      <FactoryArchitecture />
      <BufferBays />
      <FlowChevrons z={4.6} />
      <FlowChevrons z={-4.6} />
      {stations.map((s, i) => (
        <StationCell
          key={s.id}
          station={s}
          i={i}
          selected={i === selected}
          onSelect={() => onSelect(s.id)}
          cameraMode={cameraMode}
          forecast={forecastIds.has(s.id)}
          qualityScenarioActive={qualityScenarioActive}
        />
      ))}
      {stations.map((s, i) => (
        <group key={`motion-${s.id}`} position={CELLS[i]}>
          <ProcessMotion index={i} station={s} />
        </group>
      ))}
      {vehicles.map((v) => (
        <LiveVehicle
          key={v.vehicle_id}
          vehicle={v}
          stations={stations}
          vehicles={vehicles}
          onSelect={onSelectVehicle}
        />
      ))}
      {forecastPoint && (
        <ForecastLayer
          stations={stations}
          sourceId={selectedId}
          point={forecastPoint}
          impacts={forecastImpacts}
          currentQueues={currentQueues}
        />
      )}
      <CameraRig
        selectedIndex={selected}
        viewAction={viewAction}
        viewTick={viewTick}
        mode={cameraMode}
        onModeChange={onCameraModeChange}
      />
    </>
  );
}
export function FactoryScene(props: FactorySceneProps) {
  return (
    <Canvas
      shadows
      camera={{ position: DEFAULT_CAMERA.toArray(), fov: 39 }}
      dpr={[1, 1.55]}
      gl={{ antialias: true, toneMappingExposure: 1.05 }}
      onPointerDown={(event) => {
        if (props.cameraMode !== "walk") return;
        const canvas = event.currentTarget as unknown as HTMLCanvasElement;
        if (document.pointerLockElement !== canvas) canvas.requestPointerLock?.();
      }}
    >
      <Scene {...props} />
    </Canvas>
  );
}
