import { useEffect, useState } from "react";
import { CheckCircle2, ChevronLeft, ChevronRight, LoaderCircle, X } from "lucide-react";
import { TOUR_STEPS } from "./tour";

type TourMode = "welcome" | "active" | "complete" | null;
type Rect = { left: number; top: number; width: number; height: number };

export function GuidedTour({ mode, step, busy, onStart, onBack, onNext, onSkip, onExplore, onDemo }: {
  mode: TourMode;
  step: number;
  busy: boolean;
  onStart: () => void;
  onBack: () => void;
  onNext: () => void;
  onSkip: () => void;
  onExplore: () => void;
  onDemo: (kind: "bottleneck" | "quality") => void;
}) {
  const [rect, setRect] = useState<Rect | null>(null);
  const current = TOUR_STEPS[step];

  useEffect(() => {
    if (mode !== "active" || !current) return;
    let frame = 0;
    let observer: ResizeObserver | null = null;
    const locate = () => {
      const element = document.querySelector<HTMLElement>(`[data-tour="${current.target}"]`);
      if (!element) { setRect(null); return; }
      const box = element.getBoundingClientRect();
      setRect({ left: Math.max(8, box.left - 6), top: Math.max(8, box.top - 6), width: Math.max(24, box.width + 12), height: Math.max(24, box.height + 12) });
    };
    frame = requestAnimationFrame(() => {
      locate();
      const element = document.querySelector<HTMLElement>(`[data-tour="${current.target}"]`);
      if (element) {
        observer = new ResizeObserver(locate);
        observer.observe(element);
      }
    });
    window.addEventListener("resize", locate);
    return () => { cancelAnimationFrame(frame); observer?.disconnect(); window.removeEventListener("resize", locate); };
  }, [mode, current]);

  if (!mode) return null;
  if (mode === "welcome") return <div className="tour-welcome-backdrop"><section className="tour-welcome"><span>Welcome to LineLens</span><h1>See problems earlier.<br/>Trace quality issues faster.</h1><p>LineLens keeps a live digital model of the factory and the vehicles moving through it.</p><div><button onClick={onStart}>Start quick tour</button><button className="secondary" onClick={onSkip}>Explore myself</button></div></section></div>;
  if (mode === "complete") return <div className="tour-welcome-backdrop"><section className="tour-welcome tour-finish"><CheckCircle2 size={32}/><span>Tour complete</span><h1>You’ve seen the LineLens story.</h1><p>Live factory. Early warning. Vehicle history. Common patterns. Human response.</p><div><button onClick={onExplore}>Explore LineLens</button><button className="secondary" onClick={() => onDemo("bottleneck")}>Run bottleneck demo</button><button className="secondary" onClick={() => onDemo("quality")}>Run quality demo</button></div></section></div>;
  return <div className="tour-layer" aria-live="polite">
    {rect && <div className="tour-spotlight" style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }} />}
    <section className="tour-card">
      <header><span>{String(step + 1).padStart(2, "0")} / {String(TOUR_STEPS.length).padStart(2, "0")}</span><button aria-label="Skip tour" onClick={onSkip}><X size={15}/></button></header>
      <div className="tour-progress"><i style={{ width: `${((step + 1) / TOUR_STEPS.length) * 100}%` }}/></div>
      <h2>{current.title}</h2><p>{busy ? "Running a short factory simulation…" : current.text}</p>{!busy && current.hint && <small>{current.hint}</small>}
      <footer><button className="tour-back" disabled={step === 0 || busy} onClick={onBack}><ChevronLeft size={14}/> Back</button><button disabled={busy} onClick={onNext}>{busy ? <LoaderCircle className="spin" size={14}/> : step === TOUR_STEPS.length - 1 ? "Finish tour" : <>Next <ChevronRight size={14}/></>}</button></footer>
    </section>
  </div>;
}
