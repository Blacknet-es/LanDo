import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function HomeScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.hero}>
        <Text style={styles.emoji}>🧠</Text>
        <Text style={styles.title}>LanDo</Text>
        <Text style={styles.subtitle}>Your self-hosted AI assistant</Text>
      </View>
      <View style={styles.badge}>
        <Text style={styles.badgeText}>v0.1.0 · local-first</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
  },
  hero: {
    alignItems: 'center',
    gap: 12,
  },
  emoji: {
    fontSize: 72,
  },
  title: {
    fontSize: 48,
    fontWeight: '800',
    color: '#f8fafc',
    letterSpacing: -1,
  },
  subtitle: {
    fontSize: 16,
    color: '#94a3b8',
    letterSpacing: 0.5,
  },
  badge: {
    position: 'absolute',
    bottom: 48,
    backgroundColor: '#1e293b',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#334155',
  },
  badgeText: {
    color: '#64748b',
    fontSize: 12,
  },
});
