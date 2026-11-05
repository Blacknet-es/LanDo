import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

type Energy = 'low' | 'medium' | 'high';
type CognitiveState = 'light' | 'moderate' | 'saturated';
type TaskTab = 'now' | 'today' | 'geofenced';
type EventItem = {
  id: string;
  title: string;
  description?: string | null;
  startAt: string;
  endAt?: string | null;
  energy: 'low' | 'medium' | 'high';
  load: 1 | 2 | 3 | 4 | 5;
  priority: 'low' | 'medium' | 'high';
  location?: string | null;
  triggerType: string;
  isMicroAction: boolean;
};

type ApiEvent = {
  id: string;
  title: string;
  description?: string | null;
  start_time: string;
  end_time?: string | null;
  energy_level?: string;
  cognitive_load?: number;
  trigger_type?: string;
  location_id?: string | null;
};

type ChatResponse = {
  reply: string;
  thread_id: string;
};

const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8001').replace(
  /\/$/,
  '',
);
const API_ROOT = `${API_URL}/api/v1`;

const MOCK_EVENTS: EventItem[] = [
  {
    id: 'mock-water',
    title: 'Preparar un vaso de agua',
    description: 'Un pequeño reinicio para empezar con calma.',
    startAt: new Date().toISOString(),
    energy: 'low',
    load: 1,
    priority: 'medium',
    triggerType: 'TIME_BASED',
    isMicroAction: true,
  },
  {
    id: 'mock-message',
    title: 'Responder el mensaje pendiente',
    description: 'Solo hace falta escribir una primera frase.',
    startAt: new Date(Date.now() + 30 * 60_000).toISOString(),
    energy: 'low',
    load: 2,
    priority: 'high',
    triggerType: 'TIME_BASED',
    isMicroAction: true,
  },
  {
    id: 'mock-break',
    title: 'Pausa sin pantallas',
    description: 'Diez minutos para despejar la mente.',
    startAt: new Date(Date.now() + 60 * 60_000).toISOString(),
    endAt: new Date(Date.now() + 70 * 60_000).toISOString(),
    energy: 'low',
    load: 1,
    priority: 'low',
    triggerType: 'TIME_BASED',
    isMicroAction: true,
  },
  {
    id: 'mock-location',
    title: 'Recoger el paquete',
    description: 'Al pasar por casa de tus padres.',
    startAt: new Date(Date.now() + 2 * 60 * 60_000).toISOString(),
    energy: 'medium',
    load: 2,
    priority: 'medium',
    location: 'Casa de tus padres',
    triggerType: 'LOCATION_ENTER',
    isMicroAction: false,
  },
];

const ENERGY_OPTIONS: { key: Energy; label: string; emoji: string }[] = [
  { key: 'low', label: 'Baja', emoji: '🪫' },
  { key: 'medium', label: 'Media', emoji: '⚡' },
  { key: 'high', label: 'Alta', emoji: '🚀' },
];

function mapApiEvent(event: ApiEvent): EventItem {
  const energy =
    event.energy_level === 'LOW_ENERGY'
      ? 'low'
      : event.energy_level === 'HIGH_ENERGY'
        ? 'high'
        : 'medium';
  const load = Math.max(1, Math.min(5, Math.round(event.cognitive_load ?? 3))) as
    | 1
    | 2
    | 3
    | 4
    | 5;
  const durationMinutes = event.end_time
    ? (new Date(event.end_time).getTime() - new Date(event.start_time).getTime()) / 60_000
    : undefined;

  return {
    id: event.id,
    title: event.title,
    description: event.description,
    startAt: event.start_time,
    endAt: event.end_time,
    energy,
    load,
    priority: load >= 4 ? 'high' : load <= 2 ? 'low' : 'medium',
    location: event.location_id,
    triggerType: event.trigger_type ?? 'TIME_BASED',
    isMicroAction: durationMinutes !== undefined && durationMinutes <= 15,
  };
}

function eventTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Hora por confirmar';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function durationLabel(event: EventItem): string {
  if (!event.endAt) return event.isMicroAction ? '≤15 min' : 'Flexible';
  const minutes = Math.max(
    0,
    Math.round((new Date(event.endAt).getTime() - new Date(event.startAt).getTime()) / 60_000),
  );
  return minutes <= 15 ? '≤15 min' : `${minutes} min`;
}

function HomeScreen() {
  const [energy, setEnergy] = useState<Energy>('medium');
  const [cognitiveState, setCognitiveState] = useState<CognitiveState>('moderate');
  const [tab, setTab] = useState<TaskTab>('today');
  const [decompression, setDecompression] = useState(false);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [threadId, setThreadId] = useState<string>();
  const [chatReply, setChatReply] = useState('');
  const [chatError, setChatError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    const loadEvents = async () => {
      try {
        const response = await fetch(`${API_ROOT}/events`, { signal: controller.signal });
        if (!response.ok) throw new Error(`API responded with HTTP ${response.status}`);
        const data = (await response.json()) as ApiEvent[];
        setEvents(data.map(mapApiEvent));
        setUsingFallback(false);
      } catch {
        if (!controller.signal.aborted) {
          setEvents(MOCK_EVENTS);
          setUsingFallback(true);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };

    void loadEvents();
    return () => controller.abort();
  }, []);

  const visibleEvents = useMemo(() => {
    const now = new Date();
    const matchesTab = (event: EventItem) => {
      if (tab === 'geofenced') return event.triggerType.startsWith('LOCATION_');
      if (tab === 'now') return event.isMicroAction;
      const eventDate = new Date(event.startAt);
      return (
        eventDate.getFullYear() === now.getFullYear() &&
        eventDate.getMonth() === now.getMonth() &&
        eventDate.getDate() === now.getDate()
      );
    };

    return events
      .filter(matchesTab)
      .filter((event) => !decompression || event.energy === 'low')
      .sort((a, b) => a.startAt.localeCompare(b.startAt));
  }, [decompression, events, tab]);

  const sendMessage = useCallback(async () => {
    const content = message.trim();
    if (!content || sending) return;

    setSending(true);
    setChatError('');
    setChatReply('');
    setMessage('');
    try {
      const response = await fetch(`${API_ROOT}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          thread_id: threadId,
          user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        }),
      });
      if (!response.ok) throw new Error(`No se pudo conectar con LanDo (${response.status}).`);
      const data = (await response.json()) as ChatResponse;
      setChatReply(data.reply);
      setThreadId(data.thread_id);
    } catch (error) {
      setChatError(
        error instanceof Error ? error.message : 'No se pudo enviar el mensaje. Inténtalo de nuevo.',
      );
      setMessage(content);
    } finally {
      setSending(false);
    }
  }, [message, sending, threadId]);

  const cognitiveLoad =
    cognitiveState === 'light' ? 'Ligera' : cognitiveState === 'moderate' ? 'Moderada' : 'Saturado';
  const loadColor =
    cognitiveState === 'light'
      ? colors.green
      : cognitiveState === 'moderate'
        ? colors.amber
        : colors.red;

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.keyboard}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 12 : 0}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.page}>
            <View style={styles.header}>
              <View>
                <Text style={styles.brand}>LanDo <Text style={styles.brandMark}>✳</Text></Text>
                <Text style={styles.greeting}>Tu espacio, a tu ritmo.</Text>
              </View>
              <View style={styles.avatar}><Text style={styles.avatarText}>L</Text></View>
            </View>

            <View style={styles.statusCard}>
              <View style={styles.sectionHeading}>
                <View>
                  <Text style={styles.eyebrow}>CHECK-IN RÁPIDO</Text>
                  <Text style={styles.cardTitle}>¿Cómo vienes hoy?</Text>
                </View>
                <Text style={styles.sparkle}>✦</Text>
              </View>

              <View style={styles.energyRow}>
                {ENERGY_OPTIONS.map((option) => {
                  const selected = energy === option.key;
                  return (
                    <Pressable
                      key={option.key}
                      accessibilityRole="button"
                      accessibilityState={{ selected }}
                      onPress={() => setEnergy(option.key)}
                      style={[styles.energyOption, selected && styles.energyOptionSelected]}
                    >
                      <Text style={styles.energyEmoji}>{option.emoji}</Text>
                      <Text style={[styles.energyLabel, selected && styles.energyLabelSelected]}>
                        {option.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>

              <View style={styles.loadRow}>
                <View style={[styles.loadDot, { backgroundColor: loadColor }]} />
                <Text style={styles.loadText}>Carga cognitiva</Text>
                <Text style={[styles.loadValue, { color: loadColor }]}>{cognitiveLoad}</Text>
              </View>
              <View style={styles.cognitiveOptions}>
                {([
                  ['light', 'Ligera', colors.green],
                  ['moderate', 'Moderada', colors.amber],
                  ['saturated', 'Saturado', colors.red],
                ] as const).map(([key, label, color]) => (
                  <Pressable
                    key={key}
                    accessibilityRole="button"
                    accessibilityState={{ selected: cognitiveState === key }}
                    onPress={() => setCognitiveState(key)}
                    style={[
                      styles.cognitiveOption,
                      cognitiveState === key && { borderColor: color, backgroundColor: `${color}12` },
                    ]}
                  >
                    <View style={[styles.cognitiveDot, { backgroundColor: color }]} />
                    <Text style={[styles.cognitiveLabel, cognitiveState === key && { color }]}>
                      {label}
                    </Text>
                  </Pressable>
                ))}
              </View>

              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: decompression }}
                onPress={() => {
                  setDecompression((current) => !current);
                  setTab('now');
                }}
                style={[styles.decompressionButton, decompression && styles.decompressionActive]}
              >
                <Text style={styles.decompressionIcon}>☁</Text>
                <View style={styles.decompressionCopy}>
                  <Text style={styles.decompressionTitle}>
                    {decompression ? 'Modo descompresión activo' : '¿Mucho en la cabeza?'}
                  </Text>
                  <Text style={styles.decompressionSubtitle}>
                    {decompression ? 'Mostrando tareas de bajo esfuerzo' : 'Un toque para empezar suave'}
                  </Text>
                </View>
                <Text style={styles.decompressionArrow}>{decompression ? '✓' : '→'}</Text>
              </Pressable>
            </View>

            <View style={styles.taskSection}>
              <View style={styles.todayHeading}>
                <View>
                  <Text style={styles.eyebrow}>TU PLAN FLEXIBLE</Text>
                  <Text style={styles.sectionTitle}>Un paso cada vez</Text>
                </View>
                <View style={styles.energyFit}>
                  <Text style={styles.energyFitDot}>●</Text>
                  <Text style={styles.energyFitText}>
                    {energy === 'low' ? 'Suave' : energy === 'medium' ? 'A tu energía' : 'Con impulso'}
                  </Text>
                </View>
              </View>

              <View style={styles.tabs}>
                {([
                  ['now', 'Para ahora'],
                  ['today', 'Hoy'],
                  ['geofenced', 'Geofenced'],
                ] as const).map(([key, label]) => (
                  <Pressable
                    key={key}
                    accessibilityRole="tab"
                    accessibilityState={{ selected: tab === key }}
                    onPress={() => setTab(key)}
                    style={[styles.tab, tab === key && styles.tabSelected]}
                  >
                    <Text style={[styles.tabText, tab === key && styles.tabTextSelected]}>{label}</Text>
                  </Pressable>
                ))}
              </View>

              {usingFallback && !loading && (
                <View style={styles.fallbackBanner}>
                  <Text style={styles.fallbackIcon}>✦</Text>
                  <Text style={styles.fallbackText}>Modo local · ejemplos para inspirarte</Text>
                </View>
              )}

              {loading ? (
                <View style={styles.loadingCard}>
                  <ActivityIndicator color={colors.violet} />
                  <View style={styles.loadingLines}>
                    <View style={styles.skeletonLineLong} />
                    <View style={styles.skeletonLineShort} />
                  </View>
                </View>
              ) : visibleEvents.length > 0 ? (
                <View style={styles.eventList}>
                  {visibleEvents.map((event) => (
                    <EventCard key={event.id} event={event} />
                  ))}
                </View>
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyIcon}>{tab === 'geofenced' ? '⌖' : '☀'}</Text>
                  <Text style={styles.emptyTitle}>No hay tareas por aquí.</Text>
                  <Text style={styles.emptyCopy}>También está bien dejar espacio en tu día.</Text>
                </View>
              )}

              <View style={styles.encouragement}>
                <Text style={styles.encouragementIcon}>✧</Text>
                <Text style={styles.encouragementText}>No hace falta hacerlo todo. Solo lo siguiente.</Text>
              </View>
            </View>
          </View>
        </ScrollView>

        <View style={styles.composerOuter}>
          {chatReply ? (
            <View style={styles.chatReply}>
              <Text style={styles.chatReplyLabel}>LanDo</Text>
              <Text style={styles.chatReplyText}>{chatReply}</Text>
            </View>
          ) : null}
          {chatError ? <Text style={styles.chatError}>{chatError}</Text> : null}
          <View style={styles.composer}>
            <TextInput
              accessibilityLabel="Mensaje para LanDo"
              placeholder="¿Qué tienes en mente?"
              placeholderTextColor={colors.muted}
              value={message}
              onChangeText={setMessage}
              onSubmitEditing={() => void sendMessage()}
              returnKeyType="send"
              editable={!sending}
              style={styles.input}
            />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Enviar mensaje"
              disabled={!message.trim() || sending}
              onPress={() => void sendMessage()}
              style={[styles.sendButton, (!message.trim() || sending) && styles.sendButtonDisabled]}
            >
              {sending ? (
                <ActivityIndicator size="small" color={colors.white} />
              ) : (
                <Text style={styles.sendButtonText}>↑</Text>
              )}
            </Pressable>
          </View>
          <Text style={styles.composerHint}>LanDo te ayuda a encontrar el siguiente paso.</Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function EventCard({ event }: { event: EventItem }) {
  const priorityLabel =
    event.priority === 'high' ? 'Importante' : event.priority === 'low' ? 'Flexible' : 'En tu lista';
  const priorityStyle =
    event.priority === 'high' ? styles.priorityHigh : event.priority === 'low' ? styles.priorityLow : styles.priorityMedium;
  const loadLabel = event.load <= 2 ? 'Ligera' : event.load === 3 ? 'Moderada' : 'Alta';
  const energyLabel = ENERGY_OPTIONS.find((option) => option.key === event.energy)?.label;
  const geofenced = event.triggerType.startsWith('LOCATION_');

  return (
    <View style={styles.eventCard}>
      <View style={styles.eventAccent} />
      <View style={styles.eventContent}>
        <View style={styles.eventTopline}>
          <Text style={styles.eventTime}>
            {geofenced ? '⌖  Al llegar' : event.isMicroAction ? '✦  Micro-acción' : `◷  ${eventTime(event.startAt)}`}
          </Text>
          <Text style={[styles.priorityBadge, priorityStyle]}>{priorityLabel}</Text>
        </View>
        <Text style={styles.eventTitle}>{event.title}</Text>
        {event.description ? <Text style={styles.eventDescription}>{event.description}</Text> : null}
        {geofenced && event.location ? (
          <Text style={styles.locationText}>⌖  {event.location}</Text>
        ) : null}
        <View style={styles.eventBadges}>
          <Text style={styles.durationBadge}>◷  {durationLabel(event)}</Text>
          <Text style={styles.loadBadge}>◌  Carga {loadLabel} · {event.load}/5</Text>
          <Text style={styles.energyBadge}>{energyLabel} {ENERGY_OPTIONS.find((option) => option.key === event.energy)?.emoji}</Text>
        </View>
      </View>
    </View>
  );
}

const colors = {
  background: '#F6F5F2',
  surface: '#FFFFFF',
  ink: '#242332',
  muted: '#858493',
  line: '#ECEBF0',
  violet: '#7663C7',
  violetPale: '#F0EDFA',
  green: '#33896E',
  greenPale: '#E8F4EE',
  amber: '#B67C27',
  amberPale: '#FBF1DF',
  red: '#C6545D',
  redPale: '#F9E9E9',
  white: '#FFFFFF',
};

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  keyboard: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingBottom: 20 },
  page: { width: '100%', maxWidth: 760, alignSelf: 'center', paddingHorizontal: 22 },
  header: {
    minHeight: 82,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 8,
    paddingBottom: 18,
  },
  brand: { color: colors.ink, fontSize: 24, fontWeight: '800', letterSpacing: -0.8 },
  brandMark: { color: colors.violet, fontSize: 19 },
  greeting: { marginTop: 3, color: colors.muted, fontSize: 13 },
  avatar: {
    width: 42,
    height: 42,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.violetPale,
  },
  avatarText: { color: colors.violet, fontSize: 18, fontWeight: '800' },
  statusCard: {
    backgroundColor: colors.surface,
    borderRadius: 25,
    borderWidth: 1,
    borderColor: '#EFEDF3',
    padding: 20,
    shadowColor: '#37334D',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.045,
    shadowRadius: 18,
    elevation: 2,
  },
  sectionHeading: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  eyebrow: { color: colors.muted, fontSize: 10, fontWeight: '800', letterSpacing: 1.4 },
  cardTitle: { marginTop: 6, color: colors.ink, fontSize: 21, fontWeight: '700' },
  sparkle: { color: '#B9ADE8', fontSize: 22 },
  energyRow: { flexDirection: 'row', gap: 9, marginTop: 17 },
  energyOption: {
    minHeight: 48,
    flex: 1,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.line,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    backgroundColor: '#FCFCFD',
  },
  energyOptionSelected: { backgroundColor: colors.violetPale, borderColor: '#D9D0F2' },
  energyEmoji: { fontSize: 15 },
  energyLabel: { color: '#777584', fontSize: 13, fontWeight: '600' },
  energyLabelSelected: { color: colors.violet, fontWeight: '800' },
  loadRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: colors.line,
    marginTop: 16,
    paddingTop: 14,
  },
  loadDot: { width: 8, height: 8, borderRadius: 4, marginRight: 9 },
  loadText: { flex: 1, color: colors.muted, fontSize: 13 },
  loadValue: { fontSize: 13, fontWeight: '800' },
  decompressionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    paddingVertical: 13,
    paddingHorizontal: 14,
    backgroundColor: '#F4F1FC',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#EEE9FA',
  },
  decompressionActive: { backgroundColor: colors.greenPale, borderColor: '#D3EBDD' },
  decompressionIcon: { color: colors.violet, fontSize: 22, marginRight: 12 },
  decompressionCopy: { flex: 1 },
  decompressionTitle: { color: colors.ink, fontSize: 13, fontWeight: '700' },
  decompressionSubtitle: { color: colors.muted, fontSize: 11, marginTop: 3 },
  decompressionArrow: { color: colors.violet, fontSize: 20, fontWeight: '700', paddingHorizontal: 4 },
  taskSection: { marginTop: 29 },
  todayHeading: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' },
  sectionTitle: { marginTop: 5, color: colors.ink, fontSize: 22, fontWeight: '800', letterSpacing: -0.5 },
  energyFit: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.greenPale,
    borderRadius: 99,
    paddingHorizontal: 10,
    paddingVertical: 7,
    marginBottom: 2,
  },
  energyFitDot: { color: colors.green, fontSize: 8, marginRight: 6 },
  energyFitText: { color: colors.green, fontSize: 10, fontWeight: '700' },
  tabs: { flexDirection: 'row', gap: 7, marginTop: 17, marginBottom: 13 },
  tab: {
    minHeight: 37,
    justifyContent: 'center',
    paddingHorizontal: 14,
    backgroundColor: '#ECEBF0',
    borderRadius: 12,
  },
  tabSelected: { backgroundColor: colors.ink },
  tabText: { color: '#777584', fontSize: 12, fontWeight: '600' },
  tabTextSelected: { color: colors.white },
  fallbackBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 9,
    marginBottom: 10,
    borderRadius: 12,
    backgroundColor: colors.amberPale,
  },
  fallbackIcon: { color: colors.amber, marginRight: 8, fontSize: 14 },
  fallbackText: { color: '#80622F', fontSize: 11, fontWeight: '600' },
  loadingCard: {
    minHeight: 88,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 18,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 19,
  },
  loadingLines: { flex: 1, marginLeft: 16 },
  skeletonLineLong: { width: '72%', height: 11, borderRadius: 6, backgroundColor: '#ECEBF1' },
  skeletonLineShort: {
    width: '43%',
    height: 9,
    borderRadius: 6,
    backgroundColor: '#F1F0F4',
    marginTop: 10,
  },
  eventList: { gap: 10 },
  eventCard: {
    flexDirection: 'row',
    overflow: 'hidden',
    backgroundColor: colors.surface,
    borderRadius: 19,
    borderWidth: 1,
    borderColor: '#EFEDF2',
  },
  eventAccent: { width: 4, backgroundColor: '#B6A8E4' },
  eventContent: { flex: 1, paddingHorizontal: 15, paddingVertical: 13 },
  eventTopline: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  eventTime: { color: colors.violet, fontSize: 10, fontWeight: '700' },
  priorityBadge: { borderRadius: 99, paddingHorizontal: 8, paddingVertical: 4, fontSize: 9, fontWeight: '700' },
  priorityHigh: { color: colors.red, backgroundColor: colors.redPale },
  priorityMedium: { color: colors.amber, backgroundColor: colors.amberPale },
  priorityLow: { color: colors.green, backgroundColor: colors.greenPale },
  eventTitle: { color: colors.ink, fontSize: 15, fontWeight: '700', marginTop: 8 },
  eventDescription: { color: colors.muted, fontSize: 11, lineHeight: 16, marginTop: 4 },
  locationText: { color: colors.violet, fontSize: 11, fontWeight: '600', marginTop: 6 },
  eventBadges: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 11 },
  durationBadge: {
    overflow: 'hidden',
    backgroundColor: '#F2F1F5',
    color: '#666473',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 5,
    fontSize: 9,
    fontWeight: '600',
  },
  loadBadge: {
    overflow: 'hidden',
    backgroundColor: '#F0EDFA',
    color: colors.violet,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 5,
    fontSize: 9,
    fontWeight: '600',
  },
  energyBadge: {
    overflow: 'hidden',
    backgroundColor: '#EEF4F0',
    color: colors.green,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 5,
    fontSize: 9,
    fontWeight: '600',
  },
  emptyCard: {
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 19,
    borderWidth: 1,
    borderColor: colors.line,
    paddingVertical: 27,
    paddingHorizontal: 20,
  },
  emptyIcon: { color: colors.violet, fontSize: 25 },
  emptyTitle: { color: colors.ink, fontSize: 14, fontWeight: '700', marginTop: 8 },
  emptyCopy: { color: colors.muted, fontSize: 11, marginTop: 5, textAlign: 'center' },
  encouragement: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 17,
    marginBottom: 8,
  },
  encouragementIcon: { color: '#A99AD9', fontSize: 14, marginRight: 7 },
  encouragementText: { color: colors.muted, fontSize: 11 },
  composerOuter: {
    width: '100%',
    maxWidth: 760,
    alignSelf: 'center',
    paddingHorizontal: 18,
    paddingTop: 10,
    paddingBottom: Platform.OS === 'web' ? 12 : 6,
    backgroundColor: colors.background,
    borderTopWidth: 1,
    borderTopColor: '#ECEBF0',
  },
  composer: {
    minHeight: 54,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#E8E6ED',
    paddingLeft: 16,
    paddingRight: 6,
  },
  input: { flex: 1, minHeight: 50, color: colors.ink, fontSize: 13 },
  cognitiveOptions: { flexDirection: 'row', gap: 7, marginTop: 10 },
  cognitiveOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 32,
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: '#FCFCFD',
    gap: 6,
  },
  cognitiveDot: { width: 7, height: 7, borderRadius: 4 },
  cognitiveLabel: { color: colors.muted, fontSize: 10, fontWeight: '600' },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.violet,
  },
  sendButtonDisabled: { backgroundColor: '#C5C1D2' },
  sendButtonText: { color: colors.white, fontSize: 23, lineHeight: 27, fontWeight: '600' },
  composerHint: { color: colors.muted, textAlign: 'center', fontSize: 9, marginTop: 7 },
  chatReply: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.line,
    padding: 12,
    marginBottom: 8,
  },
  chatReplyLabel: { color: colors.violet, fontSize: 10, fontWeight: '800', marginBottom: 4 },
  chatReplyText: { color: colors.ink, fontSize: 12, lineHeight: 18 },
  chatError: { color: colors.red, fontSize: 11, marginHorizontal: 5, marginBottom: 7 },
});

export default HomeScreen;
