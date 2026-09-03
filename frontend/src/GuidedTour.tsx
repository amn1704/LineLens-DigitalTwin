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

export function HelpPopover({ open, chapters, completedChapterIds, onStart, onChapter, onActivity, onValidation, onClose }: { open: boolean; chapters: readonly GuideChapter[]; completedChapterIds: string[]; onStart: () => void; onChapter: (chapter: GuideChapter) => void; onActivity: () => void; onValidation: () => void; onClose: () => void }) {
  useEffect(() => { const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); }; if (open) window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close); }, [open, onClose]);
  if (!open) return null;
  return <div className="help-popover-backdrop" onMouseDown={onClose}>
    <aside className="help-popover" role="dialog" aria-label="Help and guidance" onMouseDown={(event) => event.stopPropagation()}>
      <button className="guide-close" aria-label="Close help" onClick={onClose}><X size={15}/></button>
      <header className="help-heading"><span>Help &amp; guidance</span><h2>Understand the line before acting.</h2><p>LineLens makes simulated production evidence easier to inspect. It recommends where to look; people remain responsible for the decision.</p></header>
      <section className="help-tour-card" aria-label="Full product tour"><div><span>New to LineLens?</span><b>Follow the complete product story</b><small>About 5 minutes · starts from the Dashboard</small></div><button onClick={onStart}>Start tour</button></section>
      <section className="help-guides" aria-labelledby="workspace-guides"><div className="help-section-heading"><span id="workspace-guides">Workspace guides</span><small>Choose the area you are using now.</small></div><div className="help-guide-grid">{chapters.map((chapter) => <button key={chapter.id} className="help-guide-choice" onClick={() => onChapter(chapter)}><span>{chapter.label}</span><small>{chapter.summary}</small><em>{completedChapterIds.includes(chapter.id) ? "Review guide" : chapter.duration}</em></button>)}</div></section>
      <section className="help-reference" aria-label="Supporting information"><button className="text-action" onClick={onActivity}><span>Activity</span><small>Read the current session’s meaningful events.</small></button><button className="text-action" onClick={onValidation}><span>Prediction validation</span><small>See how simulated outcomes are recorded.</small></button></section>
      <p className="help-disclosure">This prototype uses synthetic factory data. It does not connect to or control factory equipment.</p>
    </aside>
  </div>;
}

export function PageGuide({ chapter, step, onBack, onNext, onExit }: { chapter: GuideChapter; step: number; onBack: () => void; onNext: () => void; onExit: () => void }) {
  const current: TourStep = chapter.steps[step];
  const rect = useTargetRect(true, current.target);
  useEffect(() => { const close = (event: KeyboardEvent) => { if (event.key === "Escape") onExit(); }; window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close); }, [onExit]);
  return <div className="tour-layer" aria-live="polite">
    {rect && <div className="tour-spotlight" style={rect}/>}
    <section className="tour-card page-guide-card">
      <header><span>{chapter.label} guide · {step + 1} / {chapter.steps.length}</span><button aria-label="Exit guide" onClick={onExit}><X size={15}/></button></header>
      <div className="tour-progress"><i style={{width:`${((step + 1)/chapter.steps.length)*100}%`}}/></div>
      <div className="guide-context"><span>What you will learn</span><p>{chapter.summary}</p></div>
      <h2>{current.title}</h2>
      <p>{current.text}</p>
      {current.hint && <aside className="guide-tip"><b>Try this</b><span>{current.hint}</span></aside>}
      {!rect && <small className="guide-state-note">This area appears when the current factory state makes it relevant.</small>}
      <footer><button className="tour-back" disabled={step===0} onClick={onBack}><ChevronLeft size={14}/> Back</button><button onClick={onNext}>{step===chapter.steps.length-1?"Finish guide":<>Next <ChevronRight size={14}/></>}</button></footer>
    </section>
  </div>;
}
