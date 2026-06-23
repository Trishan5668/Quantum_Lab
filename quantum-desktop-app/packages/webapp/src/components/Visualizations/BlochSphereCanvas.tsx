import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const SIZE = 240;
const RADIUS = 1;

interface Props {
  x: number;
  y: number;
  z: number;
}

interface SceneRefs {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  arrow: THREE.ArrowHelper;
  arrowGroup: THREE.Group;
  raf: number | null;
  targetDir: THREE.Vector3;
  targetLen: number;
  currentDir: THREE.Vector3;
  currentLen: number;
  animStart: number | null;
  animDuration: number;
  animFromDir: THREE.Vector3;
  animFromLen: number;
}

export function BlochSphereCanvas({ x, y, z }: Props): JSX.Element {
  const mountRef = useRef<HTMLDivElement>(null);
  const refs = useRef<SceneRefs | null>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.set(2.6, 1.8, 2.6);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(SIZE, SIZE);
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.minDistance = 2.2;
    controls.maxDistance = 6;

    // Sphere wireframe
    const sphereGeom = new THREE.SphereGeometry(RADIUS, 32, 32);
    const sphereMat = new THREE.MeshBasicMaterial({
      color: 0x7c3aed,
      transparent: true,
      opacity: 0.07,
    });
    const sphere = new THREE.Mesh(sphereGeom, sphereMat);
    scene.add(sphere);

    const wireGeom = new THREE.SphereGeometry(RADIUS, 24, 16);
    const wireMat = new THREE.LineBasicMaterial({
      color: 0x4b5563,
      transparent: true,
      opacity: 0.35,
    });
    const wire = new THREE.LineSegments(
      new THREE.WireframeGeometry(wireGeom),
      wireMat,
    );
    scene.add(wire);

    // Axes
    const axisLen = RADIUS * 1.25;
    const axisColors = { x: 0xef4444, y: 0x10b981, z: 0x60a5fa };
    const addAxis = (dir: THREE.Vector3, color: number, label: string) => {
      const points = [dir.clone().multiplyScalar(-axisLen), dir.clone().multiplyScalar(axisLen)];
      const geom = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geom, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.55 }));
      scene.add(line);
      const labelCanvas = makeLabelCanvas(label, color);
      const tex = new THREE.CanvasTexture(labelCanvas);
      const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.position.copy(dir.clone().multiplyScalar(axisLen + 0.18));
      sprite.scale.set(0.34, 0.18, 1);
      scene.add(sprite);
    };
    addAxis(new THREE.Vector3(1, 0, 0), axisColors.x, "X");
    addAxis(new THREE.Vector3(0, 1, 0), axisColors.z, "Z");
    addAxis(new THREE.Vector3(0, 0, 1), axisColors.y, "Y");

    // Pole labels |0> and |1>
    const zeroLabel = makeLabelCanvas("|0⟩", 0xa78bfa);
    const oneLabel = makeLabelCanvas("|1⟩", 0xa78bfa);
    const zeroTex = new THREE.CanvasTexture(zeroLabel);
    const oneTex = new THREE.CanvasTexture(oneLabel);
    const zeroSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: zeroTex, transparent: true }),
    );
    const oneSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: oneTex, transparent: true }),
    );
    zeroSprite.position.set(0, RADIUS + 0.2, 0);
    oneSprite.position.set(0, -(RADIUS + 0.2), 0);
    zeroSprite.scale.set(0.32, 0.18, 1);
    oneSprite.scale.set(0.32, 0.18, 1);
    scene.add(zeroSprite);
    scene.add(oneSprite);

    // Equator
    const equatorPoints: THREE.Vector3[] = [];
    for (let i = 0; i <= 64; i++) {
      const a = (i / 64) * Math.PI * 2;
      equatorPoints.push(new THREE.Vector3(Math.cos(a), 0, Math.sin(a)));
    }
    const equator = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(equatorPoints),
      new THREE.LineBasicMaterial({ color: 0xa78bfa, transparent: true, opacity: 0.5 }),
    );
    scene.add(equator);

    const arrowGroup = new THREE.Group();
    const initialDir = new THREE.Vector3(0, 1, 0);
    const arrow = new THREE.ArrowHelper(
      initialDir.clone(),
      new THREE.Vector3(0, 0, 0),
      1.0,
      0xa78bfa,
      0.14,
      0.08,
    );
    arrowGroup.add(arrow);
    scene.add(arrowGroup);

    refs.current = {
      renderer,
      scene,
      camera,
      controls,
      arrow,
      arrowGroup,
      raf: null,
      targetDir: initialDir.clone(),
      targetLen: 0,
      currentDir: initialDir.clone(),
      currentLen: 0,
      animStart: null,
      animDuration: 400,
      animFromDir: initialDir.clone(),
      animFromLen: 0,
    };

    const animate = (now: number) => {
      const r = refs.current;
      if (!r) return;
      controls.update();
      if (r.animStart !== null) {
        const elapsed = now - r.animStart;
        const t = Math.min(1, elapsed / r.animDuration);
        const eased = easeOutCubic(t);
        const dir = slerp(r.animFromDir, r.targetDir, eased);
        const len = r.animFromLen + (r.targetLen - r.animFromLen) * eased;
        r.currentDir.copy(dir);
        r.currentLen = len;
        r.arrow.setDirection(dir);
        r.arrow.setLength(Math.max(0.0001, len), 0.14, 0.08);
        if (t >= 1) r.animStart = null;
      }
      renderer.render(scene, camera);
      r.raf = requestAnimationFrame(animate);
    };
    refs.current.raf = requestAnimationFrame(animate);

    const handleResize = () => {
      // Square aspect locked
      renderer.setSize(SIZE, SIZE);
      camera.aspect = 1;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (refs.current?.raf) cancelAnimationFrame(refs.current.raf);
      controls.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    const r = refs.current;
    if (!r) return;
    // Map quantum Bloch (x, y, z) to Three.js (THREE_x, THREE_z, THREE_y) so
    // Z (computational) is rendered as vertical up in the scene.
    const len = Math.sqrt(x * x + y * y + z * z);
    const dir =
      len > 1e-9
        ? new THREE.Vector3(x / len, z / len, y / len).normalize()
        : new THREE.Vector3(0, 1, 0);
    r.animFromDir = r.currentDir.clone();
    r.animFromLen = r.currentLen;
    r.targetDir = dir;
    r.targetLen = Math.min(1, Math.max(0, len));
    r.animStart = performance.now();
  }, [x, y, z]);

  return (
    <div
      ref={mountRef}
      style={{ width: SIZE, height: SIZE, margin: "0 auto" }}
      className="rounded-md bg-bg-base/60"
    />
  );
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

function slerp(a: THREE.Vector3, b: THREE.Vector3, t: number): THREE.Vector3 {
  const dot = THREE.MathUtils.clamp(a.dot(b), -1, 1);
  const omega = Math.acos(dot);
  if (omega < 1e-6) {
    return a.clone().lerp(b, t);
  }
  const sinO = Math.sin(omega);
  const wa = Math.sin((1 - t) * omega) / sinO;
  const wb = Math.sin(t * omega) / sinO;
  return a.clone().multiplyScalar(wa).add(b.clone().multiplyScalar(wb)).normalize();
}

function makeLabelCanvas(text: string, color: number): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = 96;
  canvas.height = 48;
  const ctx = canvas.getContext("2d");
  if (!ctx) return canvas;
  ctx.font = "600 28px 'JetBrains Mono', monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = `#${color.toString(16).padStart(6, "0")}`;
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);
  return canvas;
}
