import React, { useState, useCallback, useRef } from 'react';
import {
  View, StyleSheet, ScrollView, TextInput, Pressable,
  KeyboardAvoidingView, Platform,
} from 'react-native';
import { Screen, Text, Icon, HITLSheet, useTheme } from '@resilio/ui-mobile';
import type { HITLOption } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

interface Message {
  id: string;
  role: 'coach' | 'user';
  content: string;
  timestamp: string;
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: '1',
    role: 'coach',
    content: "Bonjour. J'ai analysé ta semaine. Tu as 3 séances prévues. Veux-tu que je t'explique la logique du plan ?",
    timestamp: '09:41',
  },
];

const HITL_OPTIONS: HITLOption[] = [
  { id: 'explain', label: 'Explique la logique du plan', description: "Détail des choix d'intensité et volume" },
  { id: 'adjust', label: 'Ajuste le plan cette semaine', description: 'Je suis disponible / indisponible certains jours' },
  { id: 'question', label: "J'ai une question spécifique", description: 'Nutrition, récupération, blessure...' },
];

export default function CoachScreen(): React.JSX.Element {
  const { colors: themeColors } = useTheme();
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [hitlVisible, setHitlVisible] = useState(false);
  const scrollRef = useRef<ScrollView>(null);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text) return;
    const userMsg: Message = {
      id: String(Date.now()),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setTimeout(() => {
      const coachMsg: Message = {
        id: String(Date.now() + 1),
        role: 'coach',
        content: 'Je note. Je prends en compte ta disponibilité pour ajuster la charge de la semaine.',
        timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, coachMsg]);
    }, 800);
  }, [input]);

  const handleHITLSelect = useCallback((id: string) => {
    const option = HITL_OPTIONS.find((o) => o.id === id);
    if (!option) return;
    const userMsg: Message = {
      id: String(Date.now()),
      role: 'user',
      content: option.label,
      timestamp: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
  }, []);

  return (
    <Screen>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={88}
      >
        <View style={[styles.header, { borderBottomColor: themeColors.border }]}>
          <View style={styles.coachInfo}>
            <View style={[styles.onlineDot, { backgroundColor: colors.zoneGreen }]} />
            <Text variant="body" color={themeColors.foreground} style={styles.coachName}>
              Head Coach
            </Text>
          </View>
          <Pressable
            onPress={() => setHitlVisible(true)}
            style={[styles.hitlBtn, { borderColor: themeColors.border }]}
            accessibilityLabel="Options"
          >
            <Icon.Analytics size={16} color={themeColors.textSecondary} />
          </Pressable>
        </View>

        <ScrollView
          ref={scrollRef}
          style={styles.flex}
          contentContainerStyle={styles.messagesContent}
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((msg) => (
            <View
              key={msg.id}
              style={[
                styles.bubble,
                msg.role === 'user' ? styles.bubbleUser : styles.bubbleCoach,
                {
                  backgroundColor: msg.role === 'user' ? themeColors.surface2 : themeColors.surface1,
                  borderColor: themeColors.border,
                },
              ]}
            >
              <Text variant="body" color={themeColors.foreground}>{msg.content}</Text>
              <Text variant="label" color={themeColors.textMuted} style={styles.timestamp}>
                {msg.timestamp}
              </Text>
            </View>
          ))}
        </ScrollView>

        <View style={[styles.inputRow, { borderTopColor: themeColors.border, backgroundColor: themeColors.background }]}>
          <Pressable
            onPress={() => setHitlVisible(true)}
            style={[styles.optionsBtn, { borderColor: themeColors.border }]}
            accessibilityLabel="Suggestions"
          >
            <Icon.Add size={18} color={themeColors.textSecondary} />
          </Pressable>
          <View style={[styles.inputWrap, { backgroundColor: themeColors.surface1, borderColor: themeColors.border }]}>
            <TextInput
              style={[styles.textInput, { color: themeColors.foreground }]}
              placeholder="Message…"
              placeholderTextColor={themeColors.textMuted}
              value={input}
              onChangeText={setInput}
              multiline
              returnKeyType="send"
              onSubmitEditing={handleSend}
            />
          </View>
          <Pressable
            onPress={handleSend}
            disabled={!input.trim()}
            style={[
              styles.sendBtn,
              { backgroundColor: input.trim() ? colors.accent : themeColors.surface2 },
            ]}
            accessibilityLabel="Envoyer"
          >
            <Icon.ChevronUp size={16} color={input.trim() ? '#fff' : themeColors.textMuted} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>

      <HITLSheet
        visible={hitlVisible}
        title="Que veux-tu faire ?"
        options={HITL_OPTIONS}
        onSelect={handleHITLSelect}
        onDismiss={() => setHitlVisible(false)}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 0.5,
  },
  coachInfo: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  onlineDot: { width: 8, height: 8, borderRadius: 4 },
  coachName: { fontWeight: '500' } as const,
  hitlBtn: {
    width: 34, height: 34, borderRadius: 10,
    borderWidth: 0.5, alignItems: 'center', justifyContent: 'center',
  },
  messagesContent: { paddingHorizontal: 16, paddingVertical: 16, gap: 10 },
  bubble: {
    maxWidth: '85%',
    borderRadius: 16,
    borderWidth: 0.5,
    padding: 14,
    gap: 6,
  },
  bubbleCoach: { alignSelf: 'flex-start' },
  bubbleUser: { alignSelf: 'flex-end' },
  timestamp: { alignSelf: 'flex-end' },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 24,
    borderTopWidth: 0.5,
  },
  optionsBtn: {
    width: 36, height: 36, borderRadius: 18,
    borderWidth: 0.5, alignItems: 'center', justifyContent: 'center',
  },
  inputWrap: {
    flex: 1,
    borderRadius: 18,
    borderWidth: 0.5,
    paddingHorizontal: 14,
    paddingVertical: 8,
    minHeight: 36,
  },
  textInput: { fontSize: 15, lineHeight: 20, maxHeight: 100 },
  sendBtn: {
    width: 36, height: 36, borderRadius: 18,
    alignItems: 'center', justifyContent: 'center',
  },
});
