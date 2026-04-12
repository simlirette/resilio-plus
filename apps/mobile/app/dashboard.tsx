import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { Card, useTheme, Icon } from '@resilio/ui-mobile';
import { colors } from '@resilio/design-tokens';

export default function DashboardScreen() {
  const router = useRouter();
  const { colorMode } = useTheme();
  const themeColors = colorMode === 'dark' ? colors.dark : colors.light;

  const readinessScore = 75;
  const nextSession = {
    title: 'Easy Run Z1',
    detail: '45 min — Zone 1 (60–74% HRmax)',
    day: 'Today',
  };
  const readinessColor =
    readinessScore >= 70 ? colors.zoneGreen
    : readinessScore >= 50 ? colors.zoneYellow
    : colors.zoneRed;

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: themeColors.background }]}
      contentContainerStyle={styles.content}
    >
      <View style={styles.header}>
        <Text style={[styles.greeting, { color: themeColors.foreground }]}>
          Good morning 👋
        </Text>
        <Text style={[styles.subGreeting, { color: themeColors.textSecondary }]}>
          Here's your coaching summary
        </Text>
      </View>

      <Card style={styles.cardSpacing}>
        <View style={styles.cardRow}>
          <Icon.Heart color={readinessColor} size={20} />
          <Text style={[styles.cardLabel, { color: themeColors.textSecondary }]}>
            Readiness
          </Text>
        </View>
        <Text style={[styles.scoreValue, { color: readinessColor }]}>
          {readinessScore}
          <Text style={[styles.scoreUnit, { color: themeColors.textSecondary }]}> / 100</Text>
        </Text>
        <Text style={[styles.cardCaption, { color: themeColors.textSecondary }]}>
          Good to train — moderate intensity OK
        </Text>
      </Card>

      <Card style={styles.cardSpacing}>
        <View style={styles.cardRow}>
          <Icon.Activity color={colors.primary} size={20} />
          <Text style={[styles.cardLabel, { color: themeColors.textSecondary }]}>
            Prochaine séance
          </Text>
        </View>
        <Text style={[styles.sessionTitle, { color: themeColors.foreground }]}>
          {nextSession.title}
        </Text>
        <Text style={[styles.sessionDetail, { color: themeColors.textSecondary }]}>
          {nextSession.detail}
        </Text>
        <View style={[styles.badge, { backgroundColor: colors.primaryDim }]}>
          <Text style={[styles.badgeText, { color: colors.primary }]}>
            {nextSession.day}
          </Text>
        </View>
      </Card>

      <TouchableOpacity
        style={[styles.checkinButton, { backgroundColor: colors.primary }]}
        onPress={() => router.push('/check-in')}
        activeOpacity={0.8}
      >
        <Icon.Energy color="#fff" size={18} />
        <Text style={styles.checkinButtonText}>Daily Check-in</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, paddingTop: 60 },
  header: { marginBottom: 24 },
  greeting: { fontSize: 22, fontWeight: '700', marginBottom: 4 },
  subGreeting: { fontSize: 14 },
  cardSpacing: { marginBottom: 16 },
  cardRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12, gap: 8 },
  cardLabel: { fontSize: 12, fontWeight: '500', textTransform: 'uppercase', letterSpacing: 0.5 },
  scoreValue: { fontSize: 48, fontWeight: '700', lineHeight: 56 },
  scoreUnit: { fontSize: 20, fontWeight: '400' },
  cardCaption: { fontSize: 13, marginTop: 4 },
  sessionTitle: { fontSize: 18, fontWeight: '600', marginBottom: 4 },
  sessionDetail: { fontSize: 14, marginBottom: 12 },
  badge: { alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  badgeText: { fontSize: 12, fontWeight: '600' },
  checkinButton: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, paddingVertical: 14, borderRadius: 12, marginTop: 8,
  },
  checkinButtonText: { color: '#fff', fontSize: 15, fontWeight: '600' },
});
