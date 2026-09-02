import { useEffect, useState } from "react";
import { CheckCircle2, ChevronLeft, ChevronRight, LoaderCircle, X } from "lucide-react";
import { GUIDE_CHAPTERS, TOUR_STEPS } from "./tour";
import type { GuideChapter, TourStep } from "./tour";

type TourMode = "welcome" | "active" | "complete" | null;
type Rect = { left: number; top: number; width: number; height: number };

export function GuidedTour({ mode, step, busy, onStart, onBack, onNext, onSkip, onExplore, onLearn, onDemo }: {
  mode: TourMode;
  step: number;
  busy: boolean;
  onStart: () => void;
  onBack: () => void;
  onNext: () => void;
  onSkip: () => void;
  onExplore: () => void;
  onLearn: () => void;
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
  if (mode === "complete") return <div className="tour-welcome-backdrop"><section className="tour-welcome tour-finish"><CheckCircle2 size={32}/><span>Tour complete</span><h1>You’ve seen the LineLens story.</h1><p>Live factory. Early warning. Vehicle history. Common patterns. Human response.</p><div><button onClick={onExplore}>Explore LineLens</button><button className="secondary" onClick={onLearn}>Learn each page</button><button className="secondary" onClick={() => onDemo("bottleneck")}>Run bottleneck demo</button><button className="secondary" onClick={() => onDemo("quality")}>Run quality demo</button></div></section></div>;
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

export function ProductGuideMenu({ completed, onQuick, onFull, onChapter, onClose }: { completed: string[]; onQuick: () => void; onFull: () => void; onChapter: (chapter: GuideChapter) => void; onClose: () => void }) {
  return <div className="tour-welcome-backdrop"><section className="tour-welcome guide-home"><button className="guide-close" aria-label="Close guide" onClick={onClose}><X size={16}/></button><span>Learn LineLens</span><h1>Choose the amount of help you need.</h1><button className="guide-choice" onClick={onQuick}><b>Quick Tour</b><small>See the LineLens story · ~90 sec</small></button><button className="guide-choice" onClick={onFull}><b>Full Product Tour</b><small>Learn every workspace · ~5–7 min</small></button><h2>By workspace</h2><div className="guide-chapters">{GUIDE_CHAPTERS.map((chapter: GuideChapter) => <button key={chapter.id} onClick={() => onChapter(chapter)}><span>{completed.includes(chapter.id) ? <CheckCircle2 size={15}/> : <i/>}</span><b>{chapter.label}</b><small>{chapter.summary} · {chapter.duration}</small></button>)}</div></section></div>;
}

export function PageGuide({ chapter, step, onBack, onNext, onExit }: { chapter: GuideChapter; step: number; onBack: () => void; onNext: () => void; onExit: () => void }) {
  const current: TourStep = chapter.steps[step];
  const [rect, setRect] = useState<Rect | null>(null);
  useEffect(() => { const locate = () => { const el=document.querySelector<HTMLElement>(`[data-tour="${current.target}"]`); if (!el) return setRect(null); el.scrollIntoView({block:"nearest",behavior:"smooth"}); const b=el.getBoundingClientRect(); setRect({left:Math.max(8,b.left-6),top:Math.max(8,b.top-6),width:Math.max(24,b.width+12),height:Math.max(24,b.height+12)}); }; const t=window.setTimeout(locate,150); window.addEventListener("resize",locate); return()=>{window.clearTimeout(t);window.removeEventListener("resize",locate);}; },[current]);
  return <div className="tour-layer" aria-live="polite">{rect && <div className="tour-spotlight" style={rect}/>}<section className="tour-card"><header><span>{chapter.label} · {step+1} / {chapter.steps.length}</span><button aria-label="Exit guide" onClick={onExit}><X size={15}/></button></header><div className="tour-progress"><i style={{width:`${((step+1)/chapter.steps.length)*100}%`}}/></div><h2>{current.title}</h2><p>{current.text}</p><footer><button className="tour-back" disabled={step===0} onClick={onBack}><ChevronLeft size={14}/> Back</button><button onClick={onNext}>{step===chapter.steps.length-1?"Finish chapter":<>Next <ChevronRight size={14}/></>}</button></footer></section></div>;
}
