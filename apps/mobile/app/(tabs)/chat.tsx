// P5 Coach Chat — conversation + HITL bottom sheet
// Expo Go SDK 54: no reanimated, no @gorhom, no draggable-flatlist
// Sheet: Animated.Value translateY | Blur: expo-blur BlurView | Rank: PanResponder drag

import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, Animated, KeyboardAvoidingView, Platform, Pressable, PanResponder,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { ImpactFeedbackStyle } from 'expo-haptics';
import { BlurView } from 'expo-blur';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path, Circle as SvgCircle } from 'react-native-svg';
import { useTheme } from '@resilio/ui-mobile';

// ─── Chat-specific tokens (supplement design-tokens) ─────────────────────────

interface ChatTokens {
  bg: string; bgElev: string; surface: string;
  surfaceMuted: string; surfaceSubtle: string;
  border: string; borderStrong: string;
  text: string; textMuted: string; textDim: string;
  accent: string; accentBorder: string;
  userBubble: string; userBubbleText: string;
}

const CHAT_TOKENS: Record<'light' | 'dark', ChatTokens> = {
  light: {
    bg: '#F5F5F2', bgElev: '#FBFBF9', surface: '#FFFFFF',
    surfaceMuted: '#EDEBE5', surfaceSubtle: '#E8E5DE',
    border: 'rgba(40,32,20,0.08)', borderStrong: 'rgba(40,32,20,0.18)',
    text: '#1A1612', textMuted: '#6B645A', textDim: '#9B948A',
    accent: '#B8552E', accentBorder: 'rgba(184,85,46,0.28)',
    userBubble: 'rgba(184,85,46,0.10)', userBubbleText: '#1A1612',
  },
  dark: {
    bg: '#1A1715', bgElev: '#211E1B', surface: '#26231F',
    surfaceMuted: '#2C2824', surfaceSubtle: '#332E29',
    border: 'rgba(245,240,230,0.08)', borderStrong: 'rgba(245,240,230,0.18)',
    text: '#F2EFE9', textMuted: '#A39B90', textDim: '#6B645A',
    accent: '#D97A52', accentBorder: 'rgba(217,122,82,0.32)',
    userBubble: '#3A3530', userBubbleText: '#F2EFE9',
  },
};

// ─── Types ────────────────────────────────────────────────────────────────────

type QuestionType = 'single' | 'multi' | 'rank';

interface Question {
  id: string;
  type: QuestionType;
  title: string;
  subtitle?: string;
  allowOther?: boolean;
  options: string[];
}

interface SingleAnswer { index: number; other: string; }
interface MultiAnswer { indices: number[]; otherSelected: boolean; other: string; }
interface RankAnswer { order: number[]; }
type Answer = SingleAnswer | MultiAnswer | RankAnswer | undefined;

interface Msg {
  id: string;
  role: 'coach' | 'user' | 'summary';
  time: string;
  text?: string;
  showAvatar?: boolean;
  continued?: boolean;
  entries?: Array<{ question: string; answer: string }>;
}

// ─── Scenario data ────────────────────────────────────────────────────────────

const INITIAL_MESSAGES: Msg[] = [
  {
    id: 'm1', role: 'coach', time: '08:42',
    text: "Ton HRV a chuté de 18% sur 24h. Ta séance de seuil prévue demain risque d'être contre-productive.",
    showAvatar: true,
  },
  {
    id: 'm2', role: 'coach', time: '08:42', continued: true,
    text: "J'ai besoin de deux, trois précisions avant d'ajuster ta semaine.",
    showAvatar: false,
  },
];

const QUESTIONS: Question[] = [
  {
    id: 'q1', type: 'single',
    title: "Comment tu veux gérer la séance de demain ?",
    allowOther: true,
    options: [
      "Remplacer par Z2 (50 min, récup active)",
      "Garder la séance mais baisser en Z3",
      "Repos complet demain",
      "Décaler la séance à jeudi",
    ],
  },
  {
    id: 'q2', type: 'multi',
    title: "Quels signaux tu ressens en ce moment ?",
    subtitle: "Plusieurs réponses possibles.",
    allowOther: true,
    options: [
      "Sommeil perturbé",
      "Jambes lourdes",
      "Stress pro/perso élevé",
      "Nutrition sous-optimale",
      "Aucun signal particulier",
    ],
  },
  {
    id: 'q3', type: 'rank',
    title: "Classe tes priorités cette semaine",
    options: ["Course à pied", "Musculation", "Récupération", "Vélo", "Natation"],
  },
];

const QUICK_PROMPTS = ['Adapte ma semaine', 'Pourquoi cette séance ?', 'Je me sens fatigué'];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTime(d: Date): string {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function canaryReply(text: string): string {
  const lower = text.toLowerCase();
  if (lower.includes('fatigué') || lower.includes('fatigue'))
    return "Compris. Je baisse la charge des 48h à venir. TSS plafonné à 180, pas de séance > Z3.";
  if (lower.includes('semaine') || lower.includes('adapte'))
    return "Je recalcule ta semaine. Objectif ACWR autour de 1.1.";
  if (lower.includes('pourquoi'))
    return "Cette séance cible ton seuil lactique. Ton VDOT suggère 5:02/km pendant 4×8 min.";
  return "Noté. Je regarde et je reviens vers toi.";
}

function formatAnswer(q: Question, answer: Answer, skipped: boolean): { question: string; answer: string } | null {
  if (skipped || !answer) return null;
  if (q.type === 'single') {
    const a = answer as SingleAnswer;
    const val = a.index === -1 ? a.other : q.options[a.index] ?? '';
    return { question: q.title, answer: val };
  }
  if (q.type === 'multi') {
    const a = answer as MultiAnswer;
    const picked = (a.indices || []).map(i => q.options[i]);
    if (a.otherSelected && a.other?.trim()) picked.push(a.other);
    return { question: q.title, answer: picked.join(' · ') };
  }
  if (q.type === 'rank') {
    const a = answer as RankAnswer;
    const ordered = a.order.map(i => q.options[i]);
    return { question: q.title, answer: ordered.map((o, i) => `${i + 1}. ${o}`).join('  ') };
  }
  return null;
}

function coachReply(results: Array<{ question: Question; answer: Answer; skipped: boolean }>): string {
  const r0 = results[0];
  if (!r0 || r0.skipped || !r0.answer) return "Noté. Je recalcule ta semaine en fonction de tes priorités. ACWR cible 1.1.";
  const a = r0.answer as SingleAnswer;
  if (a.index === 0) return "Noté. Sortie Z2 de 50 min demain, 6:10/km. ACWR cible 1.1.";
  if (a.index === 1) return "Noté. Ajusté pour 45 min Z3, allure 5:15/km. ACWR cible 1.1.";
  if (a.index === 2) return "Noté. Repos complet demain. Je recalcule ta semaine.";
  if (a.index === 3) return "Noté. Seuil décalé à jeudi, recovery demain. ACWR cible 1.1.";
  return "Noté. Je recalcule ta semaine en fonction de tes priorités. ACWR cible 1.1.";
}

// ─── SVG Icons ────────────────────────────────────────────────────────────────

function IconBack({ color }: { color: string }) {
  return (
    <Svg width={11} height={18} viewBox="0 0 11 18">
      <Path d="M9.5 1.5L2 9l7.5 7.5" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

function IconMore({ color }: { color: string }) {
  return (
    <Svg width={20} height={4} viewBox="0 0 20 4">
      <SvgCircle cx={2} cy={2} r={2} fill={color} />
      <SvgCircle cx={10} cy={2} r={2} fill={color} />
      <SvgCircle cx={18} cy={2} r={2} fill={color} />
    </Svg>
  );
}

function IconSend({ color }: { color: string }) {
  return (
    <Svg width={16} height={16} viewBox="0 0 16 16">
      <Path d="M8 14V2M8 2L2.5 7.5M8 2l5.5 5.5" stroke={color} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

function IconArrowRight({ color, size = 14 }: { color: string; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 16 16">
      <Path d="M3 8h10M9 4l4 4-4 4" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

function IconChevLeft({ color }: { color: string }) {
  return (
    <Svg width={8} height={12} viewBox="0 0 8 12">
      <Path d="M6 1L1 6l5 5" stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

function IconChevRight({ color }: { color: string }) {
  return (
    <Svg width={8} height={12} viewBox="0 0 8 12">
      <Path d="M2 1l5 5-5 5" stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

function IconX({ color }: { color: string }) {
  return (
    <Svg width={12} height={12} viewBox="0 0 12 12">
      <Path d="M2 2l8 8M10 2l-8 8" stroke={color} strokeWidth={1.6} strokeLinecap="round" fill="none" />
    </Svg>
  );
}

function IconCheck({ color }: { color: string }) {
  return (
    <Svg width={11} height={11} viewBox="0 0 12 12">
      <Path d="M2.5 6.5L5 9l4.5-5" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

function IconEdit({ color }: { color: string }) {
  return (
    <Svg width={13} height={13} viewBox="0 0 13 13">
      <Path d="M9 2l2 2-7 7H2v-2l7-7z" stroke={color} strokeWidth={1.4} strokeLinejoin="round" fill="none" />
    </Svg>
  );
}

// ─── Chat header ──────────────────────────────────────────────────────────────

function ChatHeader({ t }: { t: ChatTokens }) {
  return (
    <View style={[s.header, { backgroundColor: t.bg, borderBottomColor: t.border }]}>
      <TouchableOpacity style={s.headerBtn} activeOpacity={0.6}>
        <IconBack color={t.textMuted} />
      </TouchableOpacity>
      <Text style={[s.headerTitle, { color: t.text }]}>Head Coach</Text>
      <TouchableOpacity style={s.headerBtn} activeOpacity={0.6}>
        <IconMore color={t.textMuted} />
      </TouchableOpacity>
    </View>
  );
}

// ─── Avatar ───────────────────────────────────────────────────────────────────

function CoachAvatar({ t }: { t: ChatTokens }) {
  return (
    <View style={[s.avatar, { backgroundColor: t.surfaceSubtle, borderColor: t.borderStrong }]}>
      <Text style={[s.avatarText, { color: t.textMuted }]}>HC</Text>
    </View>
  );
}

// ─── Bubbles ──────────────────────────────────────────────────────────────────

function CoachBubble({ t, msg }: { t: ChatTokens; msg: Msg }) {
  return (
    <View style={[s.coachRow, { marginBottom: msg.continued ? 4 : 14 }]}>
      <View style={s.avatarSlot}>
        {msg.showAvatar ? <CoachAvatar t={t} /> : null}
      </View>
      <View style={s.coachBubbleWrap}>
        <View style={[
          s.coachBubble,
          { backgroundColor: t.surfaceMuted },
          msg.showAvatar ? s.coachBubbleRounded : undefined,
        ]}>
          <Text style={[s.bubbleText, { color: t.text }]}>{msg.text}</Text>
        </View>
        {msg.time ? (
          <Text style={[s.bubbleTime, { color: t.textDim }]}>{msg.time}</Text>
        ) : null}
      </View>
    </View>
  );
}

function UserBubble({ t, msg }: { t: ChatTokens; msg: Msg }) {
  return (
    <View style={[s.userRow, { marginBottom: 14 }]}>
      <View style={s.userBubbleWrap}>
        <View style={[s.userBubble, { backgroundColor: t.userBubble }]}>
          <Text style={[s.bubbleText, { color: t.userBubbleText }]}>{msg.text}</Text>
        </View>
        {msg.time ? (
          <Text style={[s.bubbleTimeRight, { color: t.textDim }]}>{msg.time}</Text>
        ) : null}
      </View>
    </View>
  );
}

function SummaryCard({ t, msg }: { t: ChatTokens; msg: Msg }) {
  const entries = msg.entries ?? [];
  return (
    <View style={[s.userRow, { marginBottom: 14 }]}>
      <View style={s.userBubbleWrap}>
        <View style={[s.summaryCard, { backgroundColor: t.surface, borderColor: t.accentBorder }]}>
          <View style={s.summaryHeader}>
            <IconCheck color={t.accent} />
            <Text style={[s.summaryHeaderText, { color: t.accent }]}>RÉPONSES ENVOYÉES</Text>
          </View>
          {entries.map((e, i) => (
            <View
              key={i}
              style={[
                s.summaryEntry,
                { borderBottomWidth: i < entries.length - 1 ? StyleSheet.hairlineWidth : 0, borderColor: t.border },
              ]}
            >
              <Text style={[s.summaryQ, { color: t.textMuted }]}>{e.question}</Text>
              <Text style={[s.summaryA, { color: t.text }]}>{e.answer}</Text>
            </View>
          ))}
        </View>
        {msg.time ? (
          <Text style={[s.bubbleTimeRight, { color: t.textDim }]}>{msg.time}</Text>
        ) : null}
      </View>
    </View>
  );
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

function TypingIndicator({ t }: { t: ChatTokens }) {
  const dots = [
    useRef(new Animated.Value(0.3)).current,
    useRef(new Animated.Value(0.3)).current,
    useRef(new Animated.Value(0.3)).current,
  ];

  useEffect(() => {
    const anims = dots.map((dot, i) => {
      const loop = Animated.loop(
        Animated.sequence([
          Animated.delay(i * 180),
          Animated.timing(dot, { toValue: 1, duration: 360, useNativeDriver: true }),
          Animated.timing(dot, { toValue: 0.3, duration: 360, useNativeDriver: true }),
          Animated.delay(Math.max(0, 720 - i * 180 * 2)),
        ]),
      );
      loop.start();
      return loop;
    });
    return () => anims.forEach(a => a.stop());
  }, []);

  return (
    <View style={[s.coachRow, { marginBottom: 14 }]}>
      <View style={s.avatarSlot}><CoachAvatar t={t} /></View>
      <View style={[s.typingBubble, { backgroundColor: t.surfaceMuted }]}>
        {dots.map((dot, i) => (
          <Animated.View key={i} style={[s.typingDot, { backgroundColor: t.textDim, opacity: dot }]} />
        ))}
      </View>
    </View>
  );
}

// ─── Input bar ────────────────────────────────────────────────────────────────

interface InputBarProps {
  t: ChatTokens;
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
}

// Standard iOS tab bar height. useBottomTabBarHeight() throws with NativeTabs
// (reads BottomTabBarHeightContext, not provided by native UITabBarController).
const TAB_BAR_HEIGHT = 49;

function InputBar({ t, value, onChange, onSend, disabled }: InputBarProps) {
  const { bottom } = useSafeAreaInsets();
  const canSend = !disabled && value.trim().length > 0;
  return (
    <View style={[s.inputWrap, { backgroundColor: t.bg, borderTopColor: t.border, paddingBottom: bottom + TAB_BAR_HEIGHT + 8 }]}>
      {/* Quick reply chips */}
      <ScrollView
        horizontal showsHorizontalScrollIndicator={false}
        style={s.chipsScroll} contentContainerStyle={s.chipsContent}
      >
        {QUICK_PROMPTS.map((qp, i) => (
          <TouchableOpacity
            key={i} activeOpacity={disabled ? 1 : 0.7}
            onPress={() => { if (!disabled) onChange(qp); }}
            style={[s.chip, { backgroundColor: t.surface, borderColor: t.border }]}
          >
            <Text style={[s.chipText, { color: t.text }]}>{qp}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Input row */}
      <View style={[s.inputRow, { backgroundColor: t.surface, borderColor: t.border }]}>
        <TextInput
          value={value}
          onChangeText={onChange}
          placeholder="Écris au coach…"
          placeholderTextColor={t.textDim}
          editable={!disabled}
          multiline
          style={[s.textInput, { color: t.text }]}
          returnKeyType="send"
          onSubmitEditing={() => { if (canSend) onSend(); }}
        />
        <TouchableOpacity
          activeOpacity={canSend ? 0.75 : 1}
          onPress={() => { if (canSend) onSend(); }}
          style={[s.sendBtn, { backgroundColor: canSend ? t.accent : t.surfaceSubtle }]}
        >
          <IconSend color={canSend ? '#FBFBF9' : t.textDim} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

// ─── HITL Sheet ───────────────────────────────────────────────────────────────

interface SubmitResult { question: Question; answer: Answer; skipped: boolean; }

interface HITLSheetProps {
  t: ChatTokens;
  open: boolean;
  questions: Question[];
  onSubmit: (results: SubmitResult[]) => void;
  onClose: () => void;
  isDark: boolean;
  insetBottom: number;
}

function HITLSheet({ t, open, questions, onSubmit, onClose, isDark, insetBottom }: HITLSheetProps) {
  const slideAnim = useRef(new Animated.Value(600)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [skipped, setSkipped] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (open) {
      setStep(0); setAnswers({}); setSkipped({});
      Animated.parallel([
        Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, tension: 60, friction: 11 }),
        Animated.timing(backdropOpacity, { toValue: 1, duration: 260, useNativeDriver: true }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(slideAnim, { toValue: 600, duration: 260, useNativeDriver: true }),
        Animated.timing(backdropOpacity, { toValue: 0, duration: 220, useNativeDriver: true }),
      ]).start();
    }
  }, [open]);

  if (!questions.length) return null;

  const q = questions[step]!;
  const total = questions.length;
  const answer = answers[q.id];
  const isSkipped = !!skipped[q.id];

  const canAdvance = ((): boolean => {
    if (isSkipped) return true;
    if (!answer) return q.type === 'rank';
    if (q.type === 'single') {
      const a = answer as SingleAnswer;
      if (a.index === -1) return (a.other?.trim().length ?? 0) > 0;
      return typeof a.index === 'number' && a.index >= 0;
    }
    if (q.type === 'multi') {
      const a = answer as MultiAnswer;
      return (a.indices?.length ?? 0) > 0 || (a.otherSelected && (a.other?.trim().length ?? 0) > 0);
    }
    return true; // rank always ok
  })();

  const setAnswer = (v: Answer) => {
    setAnswers(prev => ({ ...prev, [q.id]: v }));
    setSkipped(prev => {
      if (!prev[q.id]) return prev;
      const next = { ...prev };
      delete next[q.id];
      return next;
    });
  };

  const goNext = () => {
    if (step < total - 1) setStep(step + 1);
    else finalSubmit();
  };
  const goPrev = () => { if (step > 0) setStep(step - 1); };
  const skipOne = () => {
    setSkipped(prev => ({ ...prev, [q.id]: true }));
    setAnswers(prev => { const next = { ...prev }; delete next[q.id]; return next; });
    setTimeout(goNext, 60);
  };
  const finalSubmit = () => {
    const result: SubmitResult[] = questions.map(qq => ({
      question: qq,
      skipped: !!skipped[qq.id],
      answer: answers[qq.id],
    }));
    onSubmit(result);
  };

  const multiCount = q.type === 'multi'
    ? ((answer as MultiAnswer)?.indices?.length ?? 0) +
      ((answer as MultiAnswer)?.otherSelected && (answer as MultiAnswer)?.other?.trim() ? 1 : 0)
    : 0;

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents={open ? 'box-none' : 'none'}>
      {/* Blur + dim backdrop */}
      <Animated.View style={[StyleSheet.absoluteFill, { opacity: backdropOpacity }]} pointerEvents={open ? 'auto' : 'none'}>
        <BlurView
          style={StyleSheet.absoluteFill}
          intensity={isDark ? 14 : 10}
          tint={isDark ? 'dark' : 'light'}
        />
        <Pressable
          style={[StyleSheet.absoluteFill, { backgroundColor: isDark ? 'rgba(0,0,0,0.52)' : 'rgba(26,22,18,0.42)' }]}
          onPress={onClose}
        />
      </Animated.View>

      {/* Sheet panel */}
      <Animated.View
        style={[
          s.sheet,
          { backgroundColor: t.bgElev, paddingBottom: insetBottom + TAB_BAR_HEIGHT + 16, transform: [{ translateY: slideAnim }] },
        ]}
        pointerEvents={open ? 'auto' : 'none'}
      >
        {/* Grabber */}
        <View style={s.grabberWrap}>
          <View style={[s.grabber, { backgroundColor: t.borderStrong }]} />
        </View>

        {/* Header */}
        <View style={s.sheetHeader}>
          <Text style={[s.sheetTitle, { color: t.text }]} numberOfLines={2}>{q.title}</Text>
          <View style={s.sheetHeaderRight}>
            {total > 1 && (
              <View style={s.pager}>
                <TouchableOpacity
                  onPress={goPrev} disabled={step === 0}
                  style={[s.pagerBtn, { opacity: step === 0 ? 0.28 : 1 }]}
                >
                  <IconChevLeft color={t.textMuted} />
                </TouchableOpacity>
                <Text style={[s.pagerCount, { color: t.textMuted }]}>{step + 1} / {total}</Text>
                <TouchableOpacity
                  onPress={canAdvance && step < total - 1 ? goNext : undefined}
                  disabled={!canAdvance || step === total - 1}
                  style={[s.pagerBtn, { opacity: (!canAdvance || step === total - 1) ? 0.28 : 1 }]}
                >
                  <IconChevRight color={t.textMuted} />
                </TouchableOpacity>
              </View>
            )}
            <TouchableOpacity onPress={onClose} style={[s.closeBtn, { backgroundColor: t.surfaceMuted }]}>
              <IconX color={t.textMuted} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Subtitle */}
        {q.subtitle ? (
          <Text style={[s.sheetSubtitle, { color: t.textMuted }]}>{q.subtitle}</Text>
        ) : null}

        {/* Body */}
        <ScrollView style={s.sheetBody} contentContainerStyle={s.sheetBodyContent} bounces={false}>
          <QuestionBody t={t} q={q} answer={answer} setAnswer={setAnswer} />
          {q.type === 'rank' && (
            <Text style={[s.rankHint, { color: t.textDim }]}>GLISSE POUR RÉORDONNER</Text>
          )}
        </ScrollView>

        {/* Footer */}
        <View style={[s.sheetFooter, { borderTopColor: t.border }]}>
          <Text style={[s.multiCount, { color: t.textMuted }]}>
            {q.type === 'multi' && multiCount > 0 ? `${multiCount} sélectionné${multiCount > 1 ? 's' : ''}` : ''}
          </Text>
          <TouchableOpacity onPress={skipOne} style={[s.skipBtn, { borderColor: t.borderStrong }]}>
            <Text style={[s.skipText, { color: t.textMuted }]}>Passer</Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={canAdvance ? goNext : undefined}
            activeOpacity={canAdvance ? 0.75 : 1}
            style={[s.nextBtn, { backgroundColor: canAdvance ? t.accent : t.surfaceMuted }]}
          >
            <IconArrowRight color={canAdvance ? '#FBFBF9' : t.textDim} size={16} />
          </TouchableOpacity>
        </View>
      </Animated.View>
    </View>
  );
}

// ─── Question body ────────────────────────────────────────────────────────────

interface QuestionBodyProps {
  t: ChatTokens;
  q: Question;
  answer: Answer;
  setAnswer: (v: Answer) => void;
}

// Module-level constant — not a hook, safe here.
const RANK_ROW_HEIGHT = 52;

function QuestionBody({ t, q, answer, setAnswer }: QuestionBodyProps) {
  // All hooks at top level — never inside conditionals (Rules of Hooks).
  const [rankOrder, setRankOrder] = useState<number[]>(
    q.type === 'rank' && answer
      ? (answer as RankAnswer).order
      : q.options.map((_, i) => i)
  );
  // Drag state for rank type — always initialised regardless of q.type
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const dragY = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (q.type === 'rank') setAnswer({ order: rankOrder });
  }, [rankOrder]);

  if (q.type === 'single') {
    const a = answer as SingleAnswer | undefined;
    const selIdx = a?.index ?? null;
    const otherText = a?.other ?? '';
    return (
      <View>
        {q.options.map((opt, i) => (
          <OptionRow
            key={i} t={t} index={i} label={opt} kind="single"
            selected={selIdx === i}
            onPress={() => setAnswer({ index: i, other: '' })}
            isLast={i === q.options.length - 1 && !q.allowOther}
          />
        ))}
        {q.allowOther && (
          <SomethingElseRow
            t={t} kind="single" value={otherText}
            selected={selIdx === -1}
            onSelect={() => setAnswer({ index: -1, other: otherText })}
            onChange={v => setAnswer({ index: -1, other: v })}
          />
        )}
      </View>
    );
  }

  if (q.type === 'multi') {
    const a = answer as MultiAnswer | undefined;
    const sel = a?.indices ?? [];
    const otherSel = a?.otherSelected ?? false;
    const otherText = a?.other ?? '';
    const toggle = (i: number) => {
      const next = sel.includes(i) ? sel.filter(x => x !== i) : [...sel, i];
      setAnswer({ indices: next, otherSelected: otherSel, other: otherText });
    };
    return (
      <View>
        {q.options.map((opt, i) => (
          <OptionRow
            key={i} t={t} index={i} label={opt} kind="multi"
            selected={sel.includes(i)}
            onPress={() => toggle(i)}
            isLast={i === q.options.length - 1 && !q.allowOther}
          />
        ))}
        {q.allowOther && (
          <SomethingElseRow
            t={t} kind="multi" value={otherText}
            selected={otherSel}
            onSelect={() => setAnswer({ indices: sel, otherSelected: !otherSel, other: otherText })}
            onChange={v => setAnswer({ indices: sel, otherSelected: true, other: v })}
          />
        )}
      </View>
    );
  }

  if (q.type === 'rank') {
    const handleDragStart = (index: number) => {
      setDraggingIndex(index);
      void Haptics.impactAsync(ImpactFeedbackStyle.Light);
    };

    const handleDragMove = (dy: number) => {
      dragY.setValue(dy);
    };

    const handleDragEnd = (dy: number) => {
      const fromIdx = draggingIndex;
      if (fromIdx !== null) {
        const slotsMoved = Math.round(dy / RANK_ROW_HEIGHT);
        if (slotsMoved !== 0) {
          const toIdx = Math.max(0, Math.min(rankOrder.length - 1, fromIdx + slotsMoved));
          if (fromIdx !== toIdx) {
            const newRanks = [...rankOrder];
            const [moved] = newRanks.splice(fromIdx, 1);
            newRanks.splice(toIdx, 0, moved!);
            setRankOrder(newRanks);
            void Haptics.impactAsync(ImpactFeedbackStyle.Medium);
          }
        }
      }
      setDraggingIndex(null);
      Animated.spring(dragY, {
        toValue: 0,
        useNativeDriver: true,
        damping: 20,
        stiffness: 300,
      }).start();
    };

    return (
      <View>
        {rankOrder.map((optIdx, i) => (
          <RankRow
            key={optIdx} t={t}
            index={i} total={rankOrder.length}
            label={q.options[optIdx] ?? ''}
            isDragging={draggingIndex === i}
            dragYValue={dragY}
            onDragStart={handleDragStart}
            onDragMove={handleDragMove}
            onDragEnd={handleDragEnd}
          />
        ))}
      </View>
    );
  }

  return null;
}

// ─── Option row (single / multi) ──────────────────────────────────────────────

interface OptionRowProps {
  t: ChatTokens;
  index: number;
  label: string;
  kind: 'single' | 'multi';
  selected: boolean;
  onPress: () => void;
  isLast: boolean;
}

function OptionRow({ t, index, label, kind, selected, onPress, isLast }: OptionRowProps) {
  const isSelectedSingle = selected && kind === 'single';
  return (
    <TouchableOpacity
      onPress={onPress} activeOpacity={0.7}
      style={[
        s.optionRow,
        { borderBottomWidth: isLast ? 0 : StyleSheet.hairlineWidth, borderBottomColor: t.border },
        isSelectedSingle && { backgroundColor: t.surfaceMuted, borderRadius: 10, marginHorizontal: -8, paddingHorizontal: 12 },
      ]}
    >
      {kind === 'single' ? (
        <View style={[
          s.numPill,
          {
            backgroundColor: isSelectedSingle ? t.text : 'transparent',
            borderColor: isSelectedSingle ? t.text : t.borderStrong,
          },
        ]}>
          <Text style={[s.numText, { color: isSelectedSingle ? t.bg : t.textMuted }]}>{index + 1}</Text>
        </View>
      ) : (
        <View style={[
          s.checkbox,
          {
            backgroundColor: selected ? t.accent : 'transparent',
            borderColor: selected ? t.accent : t.borderStrong,
          },
        ]}>
          {selected && <IconCheck color="#FBFBF9" />}
        </View>
      )}
      <Text style={[
        s.optionLabel,
        { color: t.text, fontFamily: isSelectedSingle ? 'SpaceGrotesk_600SemiBold' : 'SpaceGrotesk_400Regular' },
      ]}>{label}</Text>
      {isSelectedSingle && <IconArrowRight color={t.text} size={14} />}
    </TouchableOpacity>
  );
}

// ─── "Autre chose" row ────────────────────────────────────────────────────────

interface SomethingElseRowProps {
  t: ChatTokens;
  kind: 'single' | 'multi';
  value: string;
  selected: boolean;
  onSelect: () => void;
  onChange: (v: string) => void;
}

function SomethingElseRow({ t, kind, value, selected, onSelect, onChange }: SomethingElseRowProps) {
  const showCheck = kind === 'multi';
  const checkedAndFilled = selected && value.trim().length > 0;
  return (
    <TouchableOpacity
      onPress={onSelect} activeOpacity={0.7}
      style={[s.otherRow, selected && { backgroundColor: t.surfaceMuted }]}
    >
      {showCheck ? (
        <View style={[s.checkbox, {
          backgroundColor: checkedAndFilled ? t.accent : 'transparent',
          borderColor: checkedAndFilled ? t.accent : t.borderStrong,
        }]}>
          {checkedAndFilled && <IconCheck color="#FBFBF9" />}
        </View>
      ) : (
        <View style={s.editIconWrap}>
          <IconEdit color={t.textDim} />
        </View>
      )}
      <TextInput
        value={value}
        onChangeText={onChange}
        onFocus={onSelect}
        placeholder="Autre chose"
        placeholderTextColor={t.textDim}
        style={[s.otherInput, { color: t.text, fontFamily: 'SpaceGrotesk_400Regular' }]}
      />
    </TouchableOpacity>
  );
}

// ─── Rank row ─────────────────────────────────────────────────────────────────

interface RankRowProps {
  t: ChatTokens;
  index: number;
  total: number;
  label: string;
  isDragging: boolean;
  dragYValue: Animated.Value;
  onDragStart: (index: number) => void;
  onDragMove: (dy: number) => void;
  onDragEnd: (dy: number) => void;
}

function GripDots({ color }: { color: string }) {
  return (
    <View style={{ flexDirection: 'row', gap: 3 }}>
      {([0, 1] as const).map(col => (
        <View key={col} style={{ gap: 4 }}>
          {([0, 1, 2] as const).map(row => (
            <View key={row} style={{ width: 3, height: 3, borderRadius: 1.5, backgroundColor: color }} />
          ))}
        </View>
      ))}
    </View>
  );
}

function RankRow({ t, index, total, label, isDragging, dragYValue, onDragStart, onDragMove, onDragEnd }: RankRowProps) {
  const panRef = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        onDragStart(index);
      },
      onPanResponderMove: (_, gs) => {
        onDragMove(gs.dy);
      },
      onPanResponderRelease: (_, gs) => {
        onDragEnd(gs.dy);
      },
    })
  ).current;

  const animatedStyle = isDragging ? {
    transform: [{ translateY: dragYValue }],
    zIndex: 10,
    elevation: 4,
    shadowOpacity: 0.15,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    opacity: 0.95,
  } : {};

  return (
    <Animated.View style={[
      s.rankRow,
      { borderBottomWidth: index < total - 1 ? StyleSheet.hairlineWidth : 0, borderBottomColor: t.border },
      animatedStyle,
    ]}>
      <View style={[s.numPill, { borderColor: t.borderStrong }]}>
        <Text style={[s.numText, { color: t.textMuted }]}>{index + 1}</Text>
      </View>
      <Text style={[s.optionLabel, { color: t.text, flex: 1, fontFamily: 'SpaceGrotesk_400Regular' }]} numberOfLines={2}>
        {label}
      </Text>
      <View {...panRef.panHandlers} style={s.rankHandle} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
        <GripDots color={t.textMuted} />
      </View>
    </Animated.View>
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function ChatScreen() {
  const { colorMode } = useTheme();
  const isDark = colorMode === 'dark';
  const t = isDark ? CHAT_TOKENS.dark : CHAT_TOKENS.light;
  const insets = useSafeAreaInsets();

  const [messages, setMessages] = useState<Msg[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetDismissed, setSheetDismissed] = useState(false);
  const [answered, setAnswered] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  // Auto-open sheet after 900ms
  useEffect(() => {
    const t = setTimeout(() => {
      if (!sheetDismissed) setSheetOpen(true);
    }, 900);
    return () => clearTimeout(t);
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
  }, [messages, typing]);

  const handleSheetSubmit = (results: SubmitResult[]) => {
    setSheetOpen(false);
    setSheetDismissed(true);
    setAnswered(true);

    const entries = results
      .map(r => formatAnswer(r.question, r.answer, r.skipped))
      .filter((e): e is { question: string; answer: string } => e !== null);

    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: 'summary-' + Date.now(), role: 'summary',
        entries, time: formatTime(new Date()),
      }]);
      setTyping(true);
    }, 280);

    setTimeout(() => {
      setTyping(false);
      setMessages(prev => [...prev, {
        id: 'c-' + Date.now(), role: 'coach',
        time: formatTime(new Date()),
        text: coachReply(results),
        showAvatar: true,
      }]);
    }, 1800);
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    setInput('');
    setMessages(prev => [...prev, {
      id: 'u' + Date.now(), role: 'user',
      time: formatTime(new Date()), text,
    }]);
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMessages(prev => [...prev, {
        id: 'c' + Date.now(), role: 'coach',
        time: formatTime(new Date()),
        text: canaryReply(text),
        showAvatar: true,
      }]);
    }, 1400);
  };

  const showResumeBtn = sheetDismissed && !sheetOpen && !answered;

  return (
    <View style={[s.screen, { backgroundColor: t.bg }]}>
      <View style={{ height: insets.top, backgroundColor: t.bg }} />
      <ChatHeader t={t} />

      <KeyboardAvoidingView
        style={s.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={insets.top + 56}
      >
        <ScrollView
          ref={scrollRef}
          style={s.flex}
          contentContainerStyle={[s.messages, { paddingBottom: insets.bottom + 8 }]}
          keyboardShouldPersistTaps="handled"
        >
          {/* Date separator */}
          <Text style={[s.dateSep, { color: t.textDim }]}>AUJOURD'HUI</Text>

          {messages.map(msg => {
            if (msg.role === 'coach') return <CoachBubble key={msg.id} t={t} msg={msg} />;
            if (msg.role === 'user') return <UserBubble key={msg.id} t={t} msg={msg} />;
            if (msg.role === 'summary') return <SummaryCard key={msg.id} t={t} msg={msg} />;
            return null;
          })}

          {typing && <TypingIndicator t={t} />}
        </ScrollView>

        {/* Resume sheet button */}
        {showResumeBtn && (
          <TouchableOpacity
            onPress={() => setSheetOpen(true)}
            activeOpacity={0.8}
            style={[s.resumeBtn, { backgroundColor: t.accent }]}
          >
            <Text style={s.resumeText}>Reprendre les questions</Text>
          </TouchableOpacity>
        )}

        <InputBar
          t={t} value={input} onChange={setInput}
          onSend={handleSend} disabled={sheetOpen}
        />
      </KeyboardAvoidingView>

      <HITLSheet
        t={t} isDark={isDark}
        open={sheetOpen}
        questions={QUESTIONS}
        onSubmit={handleSheetSubmit}
        onClose={() => { setSheetOpen(false); setSheetDismissed(true); }}
        insetBottom={insets.bottom}
      />
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const s = StyleSheet.create({
  screen: { flex: 1 },
  flex: { flex: 1 },

  // Header
  header: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 4, paddingVertical: 6,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  headerBtn: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { flex: 1, textAlign: 'center', fontSize: 16, letterSpacing: -0.2, fontFamily: 'SpaceGrotesk_600SemiBold' },

  // Messages
  messages: { paddingHorizontal: 16, paddingTop: 16 },
  dateSep: {
    textAlign: 'center', fontSize: 11, letterSpacing: 0.4,
    textTransform: 'uppercase', paddingBottom: 16, fontFamily: 'SpaceGrotesk_400Regular',
  },

  // Coach bubble
  coachRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, paddingRight: 44 },
  avatarSlot: { width: 28, flexShrink: 0 },
  avatar: { width: 28, height: 28, borderRadius: 14, borderWidth: StyleSheet.hairlineWidth, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontSize: 10, fontFamily: 'SpaceGrotesk_600SemiBold', letterSpacing: 0.3 },
  coachBubbleWrap: { flexShrink: 1, gap: 4 },
  coachBubble: { padding: 10, paddingHorizontal: 14, borderRadius: 14, borderTopLeftRadius: 14 },
  coachBubbleRounded: { borderTopLeftRadius: 4 },
  bubbleText: { fontSize: 15, lineHeight: 21, letterSpacing: -0.1, fontFamily: 'SpaceGrotesk_400Regular' },
  bubbleTime: { fontSize: 10.5, letterSpacing: 0.2, paddingLeft: 4, fontFamily: 'SpaceGrotesk_400Regular' },

  // User bubble
  userRow: { flexDirection: 'row', justifyContent: 'flex-end', paddingLeft: 50 },
  userBubbleWrap: { flexShrink: 1, alignItems: 'flex-end', gap: 4 },
  userBubble: { padding: 10, paddingHorizontal: 14, borderRadius: 14, borderBottomRightRadius: 4 },
  bubbleTimeRight: { fontSize: 10.5, letterSpacing: 0.2, paddingRight: 4, fontFamily: 'SpaceGrotesk_400Regular' },

  // Summary card
  summaryCard: { borderWidth: 1, borderRadius: 14, borderBottomRightRadius: 4, padding: 12, minWidth: 220 },
  summaryHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  summaryHeaderText: { fontSize: 10, fontFamily: 'SpaceGrotesk_600SemiBold', letterSpacing: 0.6 },
  summaryEntry: { paddingVertical: 8 },
  summaryQ: { fontSize: 11, letterSpacing: -0.05, marginBottom: 3, lineHeight: 14, fontFamily: 'SpaceGrotesk_400Regular' },
  summaryA: { fontSize: 14, fontFamily: 'SpaceGrotesk_500Medium', letterSpacing: -0.1, lineHeight: 19 },

  // Typing
  typingBubble: { flexDirection: 'row', alignItems: 'center', gap: 4, padding: 12, paddingHorizontal: 14, borderRadius: 14, borderTopLeftRadius: 4 },
  typingDot: { width: 5, height: 5, borderRadius: 3 },

  // Input bar
  inputWrap: { borderTopWidth: StyleSheet.hairlineWidth, paddingHorizontal: 12, paddingTop: 10, paddingBottom: 8 },
  chipsScroll: { marginHorizontal: -12, marginBottom: 10 },
  chipsContent: { paddingHorizontal: 12, gap: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 13, paddingVertical: 7, flexShrink: 0 },
  chipText: { fontSize: 12.5, fontFamily: 'SpaceGrotesk_500Medium', letterSpacing: -0.05 },
  inputRow: {
    flexDirection: 'row', alignItems: 'flex-end', gap: 8,
    borderWidth: 1, borderRadius: 22,
    paddingLeft: 14, paddingRight: 6, paddingVertical: 6,
  },
  textInput: { flex: 1, fontSize: 15, fontFamily: 'SpaceGrotesk_400Regular', lineHeight: 20, maxHeight: 100, paddingVertical: 7 },
  sendBtn: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },

  // Resume button
  resumeBtn: { alignSelf: 'center', marginBottom: 8, borderRadius: 999, paddingHorizontal: 16, paddingVertical: 10 },
  resumeText: { color: '#FBFBF9', fontSize: 13, fontFamily: 'SpaceGrotesk_600SemiBold', letterSpacing: 0.2 },

  // Sheet
  sheet: {
    position: 'absolute', left: 0, right: 0, bottom: 0,
    borderTopLeftRadius: 20, borderTopRightRadius: 20,
    maxHeight: '80%',
    shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 40, shadowOffset: { width: 0, height: -10 },
    elevation: 24,
  },
  grabberWrap: { alignItems: 'center', paddingTop: 8, paddingBottom: 4 },
  grabber: { width: 36, height: 5, borderRadius: 999 },
  sheetHeader: {
    flexDirection: 'row', alignItems: 'flex-start',
    paddingHorizontal: 16, paddingBottom: 12, gap: 10,
  },
  sheetTitle: { flex: 1, fontSize: 17, fontFamily: 'SpaceGrotesk_600SemiBold', letterSpacing: -0.2, lineHeight: 22 },
  sheetHeaderRight: { flexDirection: 'row', alignItems: 'center', gap: 8, flexShrink: 0 },
  pager: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  pagerBtn: { padding: 6 },
  pagerCount: { fontSize: 12, letterSpacing: 0.2, fontFamily: 'SpaceGrotesk_400Regular', minWidth: 28, textAlign: 'center' },
  closeBtn: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  sheetSubtitle: { paddingHorizontal: 16, paddingBottom: 12, fontSize: 13, lineHeight: 18, letterSpacing: -0.05, fontFamily: 'SpaceGrotesk_400Regular' },
  sheetBody: { flexShrink: 1 },
  sheetBodyContent: { paddingHorizontal: 16, paddingBottom: 12 },
  rankHint: { fontSize: 11, letterSpacing: 0.2, textTransform: 'uppercase', marginTop: 10, fontFamily: 'SpaceGrotesk_400Regular' },
  sheetFooter: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingHorizontal: 16, paddingTop: 10, paddingBottom: 6,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  multiCount: { flex: 1, fontSize: 12, letterSpacing: 0.2, fontFamily: 'SpaceGrotesk_400Regular' },
  skipBtn: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 16, paddingVertical: 8 },
  skipText: { fontSize: 13, fontFamily: 'SpaceGrotesk_500Medium', letterSpacing: -0.05 },
  nextBtn: { width: 40, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },

  // Option rows
  optionRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 14, paddingHorizontal: 4 },
  numPill: { width: 28, height: 28, borderRadius: 7, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  numText: { fontSize: 12, fontFamily: 'SpaceGrotesk_500Medium' },
  checkbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  optionLabel: { fontSize: 15, letterSpacing: -0.1 },

  // Other row
  otherRow: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    paddingVertical: 14, paddingHorizontal: 12,
    marginTop: 4, borderRadius: 10, marginHorizontal: -8,
  },
  editIconWrap: { width: 28, alignItems: 'center' },
  otherInput: { flex: 1, fontSize: 15, letterSpacing: -0.1 },

  // Rank row
  rankRow: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 14, paddingHorizontal: 4, backgroundColor: 'transparent' },
  rankHandle: { width: 24, height: 44, alignItems: 'center', justifyContent: 'center' },
});
