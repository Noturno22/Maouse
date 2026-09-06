"use client";

import {
  createContext,
  useContext,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { copy, type Copy, type Lang } from "@/lib/i18n";

interface LangValue {
  lang: Lang;
  t: Copy;
  set: (lang: Lang) => void;
}

const LangContext = createContext<LangValue>(null!);

type Listener = () => void;
const listeners = new Set<Listener>();
let current: Lang = "pt";

function readStored(): Lang {
  try {
    const stored = localStorage.getItem("maouse_lang");
    return stored === "en" || stored === "pt" ? stored : current;
  } catch {
    return current;
  }
}

function subscribe(cb: Listener) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

function getSnapshot(): Lang {
  return readStored();
}

function getServerSnapshot(): Lang {
  return "pt";
}

function commit(next: Lang) {
  current = next;
  try {
    localStorage.setItem("maouse_lang", next);
  } catch {}
  listeners.forEach((cb) => cb());
}

export function LangProvider({ children }: { children: ReactNode }) {
  const lang = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  return (
    <LangContext.Provider value={{ lang, t: copy[lang], set: commit }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang(): LangValue {
  return useContext(LangContext);
}