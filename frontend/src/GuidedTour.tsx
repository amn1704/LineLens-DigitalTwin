import { useEffect, useState } from "react";
import { CheckCircle2, ChevronLeft, ChevronRight, LoaderCircle, X } from "lucide-react";
import { TOUR_STEPS } from "./tour";
import type { GuideChapter, TourStep } from "./tour";

type TourMode = "welcome" | "active" | "complete" | null;
type Rect = { left: number; top: number; width: number; height: number };

function useTargetRect(active: boolean, target?: string) {
  const [rect, setRect] = useState<Rect | null>(null);
  useEffect(() => {
    if (!active || !target) return;
    let observer: ResizeObserver | null = null;
    const locate = () => {
      const element = document.querySelector<HTMLElement>(`[data-tour="${target}"]`);
      if (!element) return setRect(null);
      const box = element.getBoundingClientRect();
      setRect({ left: Math.max(8, box.left - 6), top: Math.max(8, box.top - 6), width: Math.max(24, box.width + 12), height: Math.max(24, box.height + 12) });
    };
    const frame = requestAnimationFrame(() => {
      locate();
      const element = document.querySelector<HTMLElement>(`[data-tour="${target}"]`);
      if (element) { observer = new ResizeObserver(locate); observer.observe(element); }
    });
    window.addEventListener("resize", locate);
    return () => { cancelAnimationFrame(frame); observer?.disconnect(); window.removeEventListener("resize", locate); };
  }, [active, target]);
  return rect;
}

export function GuidedTour({ mode, step, busy, onStart, onBack, onNext, onExit, onExplore }: {
  mode: TourMode; step: number; busy: boolean; onStart: () => void; onBack: () => void; onNext: () => void; onExit: () => void; onExplore: () => void;
}) {
  const current = TOUR_STEPS[step];
  const rect = useTargetRect(mode === "active", current?.target);
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape" && mode) onExit(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [mode, onExit]);
  if (!mode) return null;
  if (mode === "welcome") return <div className="tour-welcome-backdrop" onMouseDown={onExit}><section className="tour-welcome" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}><button className="guide-close" aria-label="Close welcome" onClick={onExit}><X size={16}/></button><span>Welcome to LineLens</span><h1>See problems earlier.<br/>Trace quality issues faster.</h1><p>LineLens keeps an evolving view of the production line and the vehicles moving through it.</p><div><button onClick={onStart}>Start full tour</button><button className="secondary" onClick={onExplore}>Explore on my own</button></div></section></div>;
  if (mode === "complete") return <div className="tour-welcome-backdrop" onMouseDown={onExit}><section className="tour-welcome tour-finish" role="dialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}><button className="guide-close" aria-label="Close tour" onClick={onExit}><X size={16}/></button><CheckCircle2 size={32}/><span>Tour complete</span><h1>You now know the LineLens story.</h1><p>See now. Predict next. Trace affected vehicles. Respond with evidence. People stay in control.</p><div><button onClick={onExplore}>Explore LineLens</button><button className="secondary" onClick={onExit}>Reset to healthy factory</button></div></section></div>;
  return <div className="tour-layer" aria-live="polite">{rect && <div className="tour-spotlight" style={rect} />}<section className="tour-card"><header><span>Full product tour · {String(step + 1).padStart(2, "0")} / {String(TOUR_STEPS.length).padStart(2, "0")}</span><button aria-label="Exit tour" onClick={onExit}><X size={15}/></button></header><div className="tour-progress"><i style={{ width: `${((step + 1) / TOUR_STEPS.length) * 100}%` }} /></div><h2>{current.title}</h2><p>{busy ? "Preparing real simulated factory output…" : current.text}</p>{!busy && current.hint && <small>{current.hint}</small>}<footer><button className="tour-back" disabled={step === 0 || busy} onClick={onBack}><ChevronLeft size={14}/> Back</button><button disabled={busy} onClick={onNext}>{busy ? <LoaderCircle className="spin" size={14}/> : step === TOUR_STEPS.length - 1 ? "Finish tour" : <>Next <ChevronRight size={14}/></>}</button></footer></section></div>;
}

export function HelpPopover({ open, onStart, onActivity, onValidation, onClose }: { open: boolean; onStart: () => void; onActivity: () => void; onValidation: () => void; onClose: () => void }) {
  useEffect(() => { const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); }; if (open) window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close); }, [open, onClose]);
  if (!open) return null;
  return <div className="help-popover-backdrop" onMouseDown={onClose}><aside className="help-popover" role="dialog" aria-label="Help" onMouseDown={(event) => event.stopPropagation()}><button className="guide-close" aria-label="Close help" onClick={onClose}><X size={15}/></button><span>Full product tour</span><b>Learn LineLens from factory data to plant response.</b><small>About 5 minutes · uses real simulator output</small><button onClick={onStart}>Start tour</button><div><button className="text-action" onClick={onActivity}>Activity</button><button className="text-action" onClick={onValidation}>About LineLens / Validation</button></div></aside></div>;
}

export function PageGuide({ chapter, step, onBack, onNext, onExit }: { chapter: GuideChapter; step: number; onBack: () => void; onNext: () => void; onExit: () => void }) {
  const current: TourStep = chapter.steps[step];
  const rect = useTargetRect(true, current.target);
  useEffect(() => { const close = (event: KeyboardEvent) => { if (event.key === "Escape") onExit(); }; window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close); }, [onExit]);
  return <div className="tour-layer" aria-live="polite">{rect && <div className="tour-spotlight" style={rect}/>}<section className="tour-card"><header><span>{chapter.label} guide · {step + 1} / {chapter.steps.length}</span><button aria-label="Exit guide" onClick={onExit}><X size={15}/></button></header><div className="tour-progress"><i style={{width:`${((step + 1)/chapter.steps.length)*100}%`}}/></div><h2>{current.title}</h2><p>{current.text}</p><footer><button className="tour-back" disabled={step===0} onClick={onBack}><ChevronLeft size={14}/> Back</button><button onClick={onNext}>{step===chapter.steps.length-1?"Finish guide":<>Next <ChevronRight size={14}/></>}</button></footer></section></div>;
}
