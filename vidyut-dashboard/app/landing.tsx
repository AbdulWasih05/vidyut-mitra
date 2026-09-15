"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import "./landing.css";

// Twilio sandbox CTA - restore once the backend + WhatsApp sandbox are hosted:
// const WHATSAPP_URL = "https://api.whatsapp.com/send?phone=15551445754&text=Hi";
const WHATSAPP_URL = "/chat";

/* ═══════════════════════════════════════════════════════════════
   VidyutMitra - landing page
   Ported from the Claude Design handoff bundle (VidyutMitra.html).
   Hybrid theme: C palette (cream + emerald) · D effects (light rays,
   chamfer, pill nav, serif) · B annotated bill card.
   ═══════════════════════════════════════════════════════════════ */
export default function LandingPage(): React.ReactElement {
  /* Port of vm-site.js - light-ray halos, scroll reveal, animated chat,
     voice waveforms + play toggle, nav shadow on scroll. */
  useEffect(() => {
    const reduce =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cancelled = false;
    const observers: IntersectionObserver[] = [];
    const cleanups: Array<() => void> = [];
    const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

    /* ---------- 1. hero backdrop (radar rings / glow / sparks) ---------- */
    function makeHeroBackdrop(host: Element) {
      host.querySelectorAll(":scope > .hero-bg-svg").forEach((n) => n.remove());
      const cx = window.innerWidth <= 860 ? 600 : 830;
      const cy = 360;
      const rings = [95, 150, 205, 265, 325];
      let ringStr = "";
      rings.forEach((r, i) => {
        const dash = i % 2 ? ' stroke-dasharray="2 11"' : "";
        const op = (0.2 - i * 0.028).toFixed(3);
        ringStr +=
          '<circle class="hb-ring" data-i="' +
          i +
          '" cx="' + cx + '" cy="' + cy + '" r="' + r +
          '" fill="none" stroke="#0e9f6e" stroke-width="1" opacity="' + op + '"' + dash + "/>";
      });
      let spokes = "";
      const ns = 30;
      for (let s = 0; s < ns; s++) {
        const sa = (s / ns) * Math.PI * 2;
        const r0 = 75;
        const r1 = 285 + (s % 3) * 33;
        spokes +=
          '<line x1="' + (cx + Math.cos(sa) * r0).toFixed(1) +
          '" y1="' + (cy + Math.sin(sa) * r0).toFixed(1) +
          '" x2="' + (cx + Math.cos(sa) * r1).toFixed(1) +
          '" y2="' + (cy + Math.sin(sa) * r1).toFixed(1) + '"/>';
      }
      let dots = "";
      for (let k = 0; k < 16; k++) {
        const a = (k * 41) * Math.PI / 180;
        const rr = 90 + (k % 5) * 57;
        const x = (cx + Math.cos(a) * rr).toFixed(1);
        const y = (cy + Math.sin(a) * rr).toFixed(1);
        const col = k % 3 === 0 ? "#0e9f6e" : "#d9714e";
        const rad = k % 4 === 0 ? 3.4 : 2.1;
        dots +=
          '<circle class="hb-dot" data-i="' + k + '" cx="' + x + '" cy="' + y +
          '" r="' + rad + '" fill="' + col + '" opacity="0.55"/>';
      }
      const svg =
        '<svg class="hero-bg-svg" viewBox="0 0 1200 760" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
        '<defs><radialGradient id="glowH" cx="50%" cy="50%" r="50%">' +
        '<stop offset="0%" stop-color="#a7e8cb" stop-opacity="0.55"/>' +
        '<stop offset="45%" stop-color="#0e9f6e" stop-opacity="0.12"/>' +
        '<stop offset="100%" stop-color="#0e9f6e" stop-opacity="0"/></radialGradient></defs>' +
        '<circle class="hb-glow" cx="' + cx + '" cy="' + (cy - 30) + '" r="300" fill="url(#glowH)"/>' +
        '<g class="hb-spokes" stroke="#0e9f6e" stroke-width="1" opacity="0.12">' + spokes + "</g>" +
        '<g class="hb-rings">' + ringStr + "</g>" +
        '<circle class="hb-spin" cx="' + cx + '" cy="' + cy + '" r="205" fill="none" stroke="#d9714e" stroke-width="1.3" stroke-dasharray="3 15" opacity="0.26"/>' +
        dots + "</svg>";
      host.insertAdjacentHTML("afterbegin", svg);
    }

    /* ---------- light rays (why section) ---------- */
    function makeRays(host: Element, o: Record<string, unknown> = {}) {
      host.querySelectorAll(":scope > .rays-svg").forEach((n) => n.remove());
      const cx = (o.cx as number) ?? 640;
      const cy = (o.cy as number) ?? 150;
      const a0 = (o.a0 as number) ?? 8;
      const a1 = (o.a1 as number) ?? 172;
      const color = (o.color as string) || "#0e9f6e";
      const op = (o.opacity as number) ?? 0.16;
      const viewH = (o.viewH as number) || 620;
      const len0 = (o.len0 as number) || 300;
      const lenVar = (o.lenVar as number) ?? 72;
      const arcs = (o.arcs as number[]) || [150, 250, 350];
      const down = !!o.down;
      const dot = (o.dotColor as string) || "#d9714e";
      const n = (o.n as number) || 36;
      let lines = "";
      for (let i = 0; i < n; i++) {
        const t = i / (n - 1);
        const ang = ((a0 + t * (a1 - a0)) * Math.PI) / 180;
        const len = len0 + Math.sin(t * Math.PI) * lenVar + (i % 2 ? 0 : 46);
        const x2 = (cx + Math.cos(ang) * len).toFixed(1);
        const y2 = (cy - Math.sin(ang) * len).toFixed(1);
        lines += '<line x1="' + cx + '" y1="' + cy + '" x2="' + x2 + '" y2="' + y2 + '"/>';
      }
      let arcStr = "";
      arcs.forEach((r) => {
        const sweep = down ? 0 : 1;
        arcStr +=
          '<path d="M ' + (cx - r) + " " + cy + " A " + r + " " + r + " 0 0 " + sweep + " " + (cx + r) + " " + cy + '"/>';
      });
      const svg =
        '<svg class="rays-svg" viewBox="0 0 1280 ' + viewH + '" preserveAspectRatio="xMidYMin slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
        '<g stroke="' + color + '" stroke-width="1" fill="none" opacity="' + op + '">' + lines + arcStr + "</g>" +
        '<circle class="ray-dot" cx="' + cx + '" cy="' + cy + '" r="4.5" fill="' + dot + '" opacity="0.6"/></svg>';
      host.insertAdjacentHTML("afterbegin", svg);
    }

    document.querySelectorAll("[data-herobg]").forEach(makeHeroBackdrop);
    document.querySelectorAll("[data-rays-dark]").forEach((h) =>
      makeRays(h, {
        cx: 640, cy: 30, a0: 205, a1: 335, down: true,
        color: "#73cfa6", dotColor: "#73cfa6", opacity: 0.5,
        viewH: 560, arcs: [180, 300, 420], lenVar: 90,
      })
    );

    /* hero backdrop: entrance + ambient loops */
    if (!reduce) {
      document.querySelectorAll(".ray-dot").forEach((d, i) => {
        (d as SVGElement).animate(
          [{ opacity: 0.3 }, { opacity: 0.8 }, { opacity: 0.3 }],
          { duration: 3400, iterations: Infinity, delay: i * 400 }
        );
      });
      const bg = document.querySelector(".hero-bg-svg");
      if (bg) {
        const ease = "cubic-bezier(.2,.8,.3,1)";
        const glow = bg.querySelector(".hb-glow") as SVGElement | null;
        if (glow) {
          glow.animate(
            [{ opacity: 0, transform: "scale(0.7)" }, { opacity: 1, transform: "scale(1)" }],
            { duration: 1100, easing: ease, fill: "backwards" }
          );
          glow.animate(
            [{ transform: "scale(1)" }, { transform: "scale(1.05)" }, { transform: "scale(1)" }],
            { duration: 6500, iterations: Infinity, delay: 1100 }
          );
        }
        const spk = bg.querySelector(".hb-spokes") as SVGElement | null;
        if (spk) {
          spk.animate(
            [{ opacity: 0, transform: "scale(0.5)" }, { opacity: 0.12, transform: "scale(1)" }],
            { duration: 1200, delay: 150, easing: ease, fill: "backwards" }
          );
          spk.animate(
            [{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }],
            { duration: 170000, iterations: Infinity, delay: 1350 }
          );
        }
        bg.querySelectorAll(".hb-ring").forEach((r) => {
          const i = +(r.getAttribute("data-i") || 0);
          const op = r.getAttribute("opacity") || "0.2";
          (r as SVGElement).animate(
            [{ opacity: 0, transform: "scale(0.3)" }, { opacity: Number(op), transform: "scale(1)" }],
            { duration: 950, delay: i * 120, easing: ease, fill: "backwards" }
          );
        });
        const spin = bg.querySelector(".hb-spin") as SVGElement | null;
        if (spin) {
          spin.animate(
            [{ opacity: 0, transform: "scale(0.3)" }, { opacity: 0.26, transform: "scale(1)" }],
            { duration: 1000, delay: 300, easing: ease, fill: "backwards" }
          );
          spin.animate(
            [{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }],
            { duration: 90000, iterations: Infinity, delay: 1300 }
          );
        }
        bg.querySelectorAll(".hb-dot").forEach((d, i) => {
          (d as SVGElement).animate(
            [{ opacity: 0, transform: "scale(0)" }, { opacity: 0.55, transform: "scale(1)" }],
            { duration: 600, delay: 500 + i * 55, easing: ease, fill: "backwards" }
          );
        });
      }
    }

    /* ---------- 2. scroll reveal ---------- */
    const vh = () => window.innerHeight || document.documentElement.clientHeight || 800;
    const inView = (el: Element) => {
      const r = el.getBoundingClientRect();
      return r.top < vh() * 0.96 && r.bottom > 0;
    };
    const revealEls = document.querySelectorAll(".reveal");
    if (reduce || !("IntersectionObserver" in window)) {
      revealEls.forEach((el) => el.classList.add("in"));
    } else {
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add("in");
              io.unobserve(e.target);
            }
          });
        },
        { threshold: 0.14, rootMargin: "0px 0px -8% 0px" }
      );
      observers.push(io);
      revealEls.forEach((el) => {
        if (inView(el)) el.classList.add("in");
        else io.observe(el);
      });
    }

    /* ---------- 4. build waveforms ---------- */
    function buildWave(el: Element | null, count: number) {
      if (!el) return;
      let frag = "";
      for (let i = 0; i < count; i++) frag += "<span></span>";
      el.innerHTML = frag;
    }
    const heroWave = document.getElementById("wave");
    const featWave = document.getElementById("wave2");
    buildWave(heroWave, 24);
    buildWave(featWave, 30);
    function phase(el: Element | null) {
      if (!el || reduce) return;
      Array.prototype.forEach.call(el.children, (s: HTMLElement) => {
        s.style.animationDelay = (Math.random() * 1.15).toFixed(2) + "s";
      });
    }
    phase(heroWave);
    phase(featWave);
    if (featWave && !reduce) featWave.classList.add("animate");

    /* play toggle (hero voice note) */
    const playBtn = document.querySelector(".msg.voice .play");
    if (playBtn) {
      const onPlay = () => {
        playBtn.classList.toggle("playing");
        const icon = playBtn.querySelector("path");
        if (playBtn.classList.contains("playing")) {
          icon?.setAttribute("d", "M7 5h3v14H7zM14 5h3v14h-3z"); // pause
          if (heroWave) heroWave.classList.add("animate");
        } else {
          icon?.setAttribute("d", "M8 5v14l11-7z"); // play
        }
      };
      playBtn.addEventListener("click", onPlay);
      cleanups.push(() => playBtn.removeEventListener("click", onPlay));
    }

    /* ---------- 3. animated chat ---------- */
    const thread = document.getElementById("thread");
    const chat = document.getElementById("chat");
    if (thread && chat) {
      thread.querySelectorAll(".typing").forEach((t) => t.remove());
      const msgs = Array.prototype.slice.call(thread.querySelectorAll(".msg")) as HTMLElement[];
      if (reduce) {
        msgs.forEach((m) => m.classList.add("in"));
        if (heroWave) heroWave.classList.add("animate");
      } else {
        msgs.forEach((m) => {
          m.classList.remove("in");
          m.classList.add("pending");
        });
        let played = false;
        const playChat = async () => {
          for (let i = 0; i < msgs.length; i++) {
            if (cancelled) return;
            const m = msgs[i];
            const isMe = m.classList.contains("me");
            if (!isMe) {
              const dots = document.createElement("div");
              dots.className = "typing";
              dots.innerHTML = "<span></span><span></span><span></span>";
              thread.appendChild(dots);
              await sleep(i === 0 ? 500 : 850);
              if (cancelled) {
                dots.remove();
                return;
              }
              dots.remove();
            } else {
              await sleep(550);
            }
            if (cancelled) return;
            m.classList.remove("pending");
            void m.offsetWidth;
            m.classList.add("in");
            if (m.classList.contains("voice") && heroWave) heroWave.classList.add("animate");
            await sleep(isMe ? 360 : 480);
          }
        };
        const cio = new IntersectionObserver(
          (entries) => {
            entries.forEach((e) => {
              if (e.isIntersecting && !played) {
                played = true;
                playChat();
                cio.unobserve(chat);
              }
            });
          },
          { threshold: 0.4 }
        );
        observers.push(cio);
        if (inView(chat)) {
          played = true;
          playChat();
        } else {
          cio.observe(chat);
        }
      }
    }

    /* ---------- 5. nav shadow on scroll ---------- */
    const nav = document.getElementById("nav");
    if (nav) {
      const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 24);
      window.addEventListener("scroll", onScroll, { passive: true });
      cleanups.push(() => window.removeEventListener("scroll", onScroll));
      onScroll();
    }

    return () => {
      cancelled = true;
      observers.forEach((o) => o.disconnect());
      cleanups.forEach((fn) => fn());
    };
  }, []);

  return (
    <div className="vm-page">
      {/* reusable glyphs */}
      <svg width="0" height="0" aria-hidden="true" style={{ position: "absolute" }}>
        <defs>
          <symbol id="g-wa" viewBox="0 0 24 24">
            <path
              d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.9-.9L3 21l1.9-5.1A8.5 8.5 0 1 1 21 11.5Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </symbol>
        </defs>
      </svg>

      {/* ===================== NAV ===================== */}
      <header className="nav-wrap">
        <div className="nav" id="nav">
          <a className="brand" href="#top">
            <span className="brand-word">
              <span className="bw-a">Vidyut</span>
              <span className="bw-b">Mitra</span>
            </span>
          </a>
          <nav className="nav-links">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#why">Why it matters</a>
          </nav>
          <div className="nav-right">
            <Link className="nav-dash" href="/dashboard">
              Dashboard
            </Link>
            <a className="nav-cta" href={WHATSAPP_URL}>
              Chat on WhatsApp
            </a>
          </div>
        </div>
      </header>

      <main id="top">
        {/* ===================== HERO ===================== */}
        <section className="hero">
          <div className="hero-bg" data-herobg></div>
          <div className="hero-grid">
            <div className="hero-copy">
              <div className="badge-wrap reveal">
                <div className="badge">India&rsquo;s Kannada-first energy advisor</div>
                <div className="badge-tip"></div>
              </div>
              <h1 className="hero-h1 reveal">
                Your electricity bill, in <em>plain Kannada</em>.
              </h1>
              <p className="hero-lead reveal">
                On WhatsApp, VidyutMitra reads your MESCOM bill in plain Kannada,{" "}
                <em>out loud, too</em>, compares it with past months, and surfaces the
                Karnataka government schemes you can claim.
              </p>
              <div className="hero-cta reveal">
                <a className="btn-ribbon" href={WHATSAPP_URL}>
                  <span className="rib">
                    <svg className="ic ic-gold">
                      <use href="#g-wa" />
                    </svg>
                    Chat on WhatsApp
                  </span>
                </a>
              </div>
              <div className="hero-meta reveal">
                <span>Free to start</span>
                <span className="dot"></span>
                <span>Works on any phone</span>
                <span className="dot"></span>
                <span>Replies in seconds</span>
              </div>
            </div>

            <div className="hero-art reveal">
              <div className="firefly"></div>
              <div className="chat" id="chat">
                <div className="chat-top">
                  <div className="chat-av">
                    <span>V</span>
                  </div>
                  <div className="chat-id">
                    <div className="chat-name">
                      VidyutMitra
                      <svg className="chat-verified" viewBox="0 0 24 24" aria-hidden="true">
                        <circle cx="12" cy="12" r="11" fill="#0e9f6e" />
                        <path
                          d="M7 12.5l3.2 3.2L17 9"
                          fill="none"
                          stroke="#fff"
                          strokeWidth="2.2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </div>
                    <div className="chat-status">
                      <span className="ol"></span>online &middot; replies in seconds
                    </div>
                  </div>
                  <div className="chat-actions" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M23 7l-7 5 7 5V7z" />
                      <rect x="1" y="5" width="15" height="14" rx="2" />
                    </svg>
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <circle cx="12" cy="5" r="1.7" />
                      <circle cx="12" cy="12" r="1.7" />
                      <circle cx="12" cy="19" r="1.7" />
                    </svg>
                  </div>
                </div>
                <div className="thread" id="thread">
                  <div className="msg bot kn" data-step="1">
                    ನಮಸ್ಕಾರ! ನಿಮ್ಮ ವಿದ್ಯುತ್ ಬಿಲ್ ಫೋಟೋ ಕಳುಹಿಸಿ.
                  </div>
                  <div className="msg me kn" data-step="2">
                    ಈ ತಿಂಗಳು ಯಾಕೆ ₹420 ಜಾಸ್ತಿ?
                  </div>
                  <div className="msg bot kn" data-step="3">
                    ಕಳೆದ ತಿಂಗಳಿಗಿಂತ 40 ಯೂನಿಟ್ ಹೆಚ್ಚು ಬಳಕೆ. ಹಳೆಯ ಫ್ರಿಡ್ಜ್ ಕಾರಣ.
                  </div>
                  <div className="msg voice" data-step="4">
                    <button className="play" aria-label="Play voice reply">
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="#fff">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </button>
                    <div className="voice-body">
                      <div className="wave" id="wave"></div>
                      <div className="voice-meta kn">ಕನ್ನಡ ಧ್ವನಿ ಉತ್ತರ &middot; 0:14</div>
                    </div>
                  </div>
                  <div className="msg bot tip kn" data-step="5">
                    ಫ್ರಿಡ್ಜ್ ತಾಪಮಾನ ಸರಿಪಡಿಸಿ, ತಿಂಗಳಿಗೆ ₹180 ಉಳಿಸಿ.{" "}
                    <span className="tip-en">Adjust your fridge setting to save ₹180/month.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ===================== PROBLEM ===================== */}
        <section className="section problem" id="problem">
          <div className="wrap">
            <p className="eyebrow reveal">The everyday problem</p>
            <h2 className="section-h2 reveal">
              Bills you can&rsquo;t read.
              <br />
              Help you can&rsquo;t reach.
            </h2>
            <div className="pain-grid">
              <article className="pain reveal">
                <svg className="pain-ic" viewBox="0 0 48 48" fill="none" stroke="#d9714e" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 6h18l8 8v28H12z" />
                  <path d="M30 6v8h8" />
                  <path d="M19 27c0-3 6-3 6 0 0 2.2-3 2.2-3 4.5" />
                  <circle cx="22" cy="36" r="0.8" fill="#d9714e" stroke="none" />
                </svg>
                <h3>Cryptic charges</h3>
                <p>FPPCA, fixed charges, slab rates: your bill is written for accountants, not for families.</p>
              </article>
              <article className="pain reveal">
                <svg className="pain-ic" viewBox="0 0 48 48" fill="none" stroke="#d9714e" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 8c-3 0-4 2-4 5 0 14 11 25 25 25 3 0 5-1 5-4l-1-6-7-2-3 4c-4-2-8-6-10-10l4-3-2-7z" />
                  <path d="M34 10l8 8M42 10l-8 8" />
                </svg>
                <h3>No one to ask</h3>
                <p>Helplines are busy, in English, and closed exactly when the question keeps you up at night.</p>
              </article>
              <article className="pain reveal">
                <svg className="pain-ic" viewBox="0 0 48 48" fill="none" stroke="#d9714e" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="24" cy="24" r="17" />
                  <path d="M7 24h34M24 7c5 5 5 29 0 34M24 7c-5 5-5 29 0 34" />
                </svg>
                <h3>A language wall</h3>
                <p>Most energy apps assume you read English and navigate menus. Millions of people simply don&rsquo;t.</p>
              </article>
            </div>
          </div>
        </section>

        {/* ===================== HOW IT WORKS ===================== */}
        <section className="section how" id="how">
          <div className="wrap">
            <p className="eyebrow reveal">How it works</p>
            <h2 className="section-h2 reveal">
              Three messages.
              <br />
              That&rsquo;s the whole app.
            </h2>
            <div className="steps">
              <article className="step reveal">
                <div className="step-top">
                  <span className="step-num">01</span>
                  <svg className="step-ic" viewBox="0 0 56 56" fill="none" stroke="#0b7d57" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="16" y="8" width="24" height="40" rx="4" />
                    <circle cx="28" cy="40" r="2.5" />
                    <rect x="21" y="14" width="14" height="10" rx="2" />
                    <circle cx="28" cy="19" r="2.6" />
                    <path d="M24 14l2-2h4l2 2" />
                  </svg>
                </div>
                <h3>Send your bill</h3>
                <p>Snap a photo of your MESCOM bill and send it on WhatsApp. No forms, no login, no download.</p>
              </article>
              <article className="step reveal">
                <div className="step-top">
                  <span className="step-num">02</span>
                  <svg className="step-ic" viewBox="0 0 56 56" fill="none" stroke="#0b7d57" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M10 14h26a4 4 0 0 1 4 4v12a4 4 0 0 1-4 4H22l-8 6v-6h-4a4 4 0 0 1-4-4V18a4 4 0 0 1 4-4z" />
                    <path d="M44 20c3 2 3 14 0 16M48 16c5 4 5 20 0 24" stroke="#d9714e" />
                  </svg>
                </div>
                <h3>Hear it explained</h3>
                <p>VidyutMitra reads every line back in plain Kannada, typed and spoken aloud as a voice note.</p>
              </article>
              <article className="step reveal">
                <div className="step-top">
                  <span className="step-num">03</span>
                  <svg className="step-ic" viewBox="0 0 56 56" fill="none" stroke="#0b7d57" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="28" cy="30" r="16" />
                    <path d="M25 24h7m-7 0c0 3 7 1 7 5 0 3-7 3-7 0m3.5-8v2m0 12v2" strokeWidth="1.5" />
                    <path d="M28 6c2 4 2 6 0 8-2-2-2-4 0-8z" fill="#0e9f6e" stroke="#0b7d57" />
                  </svg>
                </div>
                <h3>Start saving</h3>
                <p>Get specific, personalized tips on what&rsquo;s driving your bill up, and the small changes that cut it down.</p>
              </article>
            </div>
          </div>
        </section>

        {/* ===================== FEATURES ===================== */}
        <section className="section features" id="features">
          <div className="wrap">
            <p className="eyebrow reveal">Features</p>
            <h2 className="section-h2 reveal">
              Made for how you
              <br />
              actually live.
            </h2>

            <div className="bento">
              {/* Bill decoding (B card) */}
              <article className="feat feat-bill reveal">
                <div className="feat-text">
                  <h3>Your bill, decoded line by line</h3>
                  <p>Send the photo; get back a clear breakdown of every charge, and a plain-language reason for any spike.</p>
                </div>
                <div className="bill-stage">
                  <svg className="stamp s1" viewBox="0 0 64 64" fill="none" stroke="#d9714e" strokeWidth="1.4" opacity="0.5">
                    <circle cx="32" cy="32" r="29" />
                    <rect x="14" y="14" width="36" height="36" transform="rotate(45 32 32)" />
                    <circle cx="32" cy="32" r="11" />
                    <path d="M32 3v11M32 50v11M3 32h11M50 32h11" />
                  </svg>
                  <div className="bill">
                    <div className="bill-head">
                      <div>
                        <div className="bill-lbl">Electricity Bill</div>
                        <div className="bill-who">MESCOM &middot; Mangaluru</div>
                      </div>
                      <div className="bill-lbl">Apr 2026</div>
                    </div>
                    <div className="bill-row">
                      <span>Units consumed</span>
                      <span className="amt">248 units</span>
                    </div>
                    <div className="bill-row">
                      <span>Energy charges</span>
                      <span className="amt">₹1,612</span>
                    </div>
                    <div className="bill-row">
                      <span>Fixed + FPPCA</span>
                      <span className="amt">₹130</span>
                    </div>
                    <div className="bill-row flag">
                      <span>Spike &middot; old fridge</span>
                      <span className="amt">+ ₹420</span>
                    </div>
                    <div className="bill-row total">
                      <span>Total payable</span>
                      <span className="amt">₹2,162</span>
                    </div>
                  </div>
                  <div className="bill-tag">
                    <span className="kn">ಇಲ್ಲಿ ಜಾಸ್ತಿ ಆಗಿದೆ</span>
                    <span className="bill-tag-en">it went up here</span>
                  </div>
                </div>
              </article>

              {/* Voice */}
              <article className="feat feat-voice reveal">
                <div className="voice-badge">
                  <span className="kn">ಕ</span>
                </div>
                <h3>Replies you can hear</h3>
                <p>Can&rsquo;t read long messages? VidyutMitra speaks every answer aloud in natural Kannada.</p>
                <div className="wave wave-lg" id="wave2"></div>
              </article>

              {/* Bill comparison */}
              <article className="feat feat-compare reveal">
                <svg className="feat-ic" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 28h24" />
                  <path d="M7 28V16M14 28V9M21 28V19M28 28V6" />
                  <path d="M24.5 9.5L28 6l-1 4.6" />
                </svg>
                <h3>See it vs. last month</h3>
                <p>VidyutMitra lines this bill up against your past months and flags exactly what changed, and why.</p>
              </article>

              {/* Karnataka schemes */}
              <article className="feat feat-schemes reveal">
                <svg className="feat-ic" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="16" cy="12" r="8" />
                  <path d="M11 18.5L8.5 28l7.5-3.6L23.5 28 21 18.5" />
                  <path d="M12.5 12l2.4 2.4L20 9.6" />
                </svg>
                <h3>Schemes you can claim</h3>
                <p>It surfaces the Karnataka government subsidies and welfare schemes you&rsquo;re eligible for, and how to apply.</p>
              </article>

              {/* Savings */}
              <article className="feat feat-save reveal">
                <div className="save-amt">
                  ₹180<span>/mo</span>
                </div>
                <h3>Savings that add up</h3>
                <p>Personalized, practical nudges: small changes worth real rupees, every month.</p>
              </article>
            </div>
          </div>
        </section>

        {/* ===================== WHY IT MATTERS ===================== */}
        <section className="section why" id="why" data-rays-dark>
          <div className="wrap why-wrap">
            <p className="eyebrow light reveal">Why it matters</p>
            <h2 className="why-h2 reveal">
              When the help speaks your language,
              <br />
              <span className="why-em">the lights stay on.</span>
            </h2>
            <p className="why-lead reveal">
              Millions of families across Karnataka run tight monthly budgets in Kannada, not
              English, not buried in app menus. VidyutMitra meets them exactly where they already
              are.
            </p>
            <div className="why-pillars reveal">
              <div className="why-pillar">
                <span className="wp-k">ಮಾತು</span>
                <h4>Speak, don&rsquo;t read</h4>
                <p>Every answer comes back as a Kannada voice note, no literacy barrier.</p>
              </div>
              <div className="why-pillar">
                <span className="wp-k">ಸ್ಪಷ್ಟತೆ</span>
                <h4>Real clarity</h4>
                <p>Each charge explained in the words people actually use at home.</p>
              </div>
              <div className="why-pillar">
                <span className="wp-k">ಉಳಿತಾಯ</span>
                <h4>Money saved</h4>
                <p>Practical nudges and government schemes worth real rupees.</p>
              </div>
            </div>
          </div>
        </section>

        {/* ===================== CREDIBILITY ===================== */}
        <section className="section cred">
          <div className="wrap">
            <p className="cred-label reveal">Built with</p>
            <div className="cred-strip reveal">
              <span className="cred-item">AI bill understanding</span>
              <span className="cred-sep"></span>
              <span className="cred-item">Kannada text-to-speech</span>
              <span className="cred-sep"></span>
              <span className="cred-item">WhatsApp-native</span>
              <span className="cred-sep"></span>
              <span className="cred-item">Made for MESCOM consumers, Karnataka</span>
            </div>
          </div>
        </section>
      </main>

      {/* ===================== FOOTER ===================== */}
      <footer className="footer">
        <div className="footer-jaali"></div>
        <div className="wrap footer-inner">
          <div className="footer-top">
            <div className="footer-brand">
              <span className="brand-word footer-word">
                <span className="bw-a">Vidyut</span>
                <span className="bw-b">Mitra</span>
              </span>
              <p className="footer-tag">
                The friend who reads your electricity bill, in plain Kannada, on WhatsApp.
              </p>
              <a className="footer-cta" href={WHATSAPP_URL}>
                Chat on WhatsApp <span aria-hidden="true">→</span>
              </a>
            </div>
            <div className="footer-cols">
              <div className="footer-col">
                <h4>Product</h4>
                <a href="#how">How it works</a>
                <a href="#features">Features</a>
                <a href="#why">Why it matters</a>
              </div>
              <div className="footer-col">
                <h4>What it does</h4>
                <a href="#features">Decode your bill</a>
                <a href="#features">Compare months</a>
                <a href="#features">Govt schemes</a>
              </div>
              <div className="footer-col">
                <h4>Connect</h4>
                <a href={WHATSAPP_URL}>WhatsApp</a>
                <a href="#why">For MESCOM</a>
                <a href="#top">Back to top</a>
              </div>
            </div>
          </div>
          <div className="footer-script" aria-hidden="true">
            ವಿದ್ಯುತ್ ಮಿತ್ರ
          </div>
          <div className="footer-base">
            <span>© 2026 VidyutMitra &middot; Built for Karnataka</span>
            <span className="kn footer-kn">ಬೆಳಕು ತರುವ ಮಿತ್ರ</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
