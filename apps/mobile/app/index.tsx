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
import { Redirect } from 'expo-router';
import { ApiClientError, createApiClient } from '@shared/api/client';
import { getDeviceLanguage, translate, type AppLanguage } from '@shared/i18n';
import { listEvents } from '../src/application/listEvents';
import { sendAssistantMessage } from '../src/application/sendAssistantMessage';
import { updatePreferredLanguage } from '../src/application/updatePreferredLanguage';
import { useSession } from '../src/auth/SessionProvider';
import { MOCK_EVENTS } from '../src/features/events/mockEvents';
import {
  durationLabel,
  eventTime,
  type CognitiveState,
  type Energy,
  type EventItem,
  type TaskTab,
} from '../src/features/events/model';

const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8001').replace(
  /\/$/,
  '',
);

function HomeContent({ accessToken }: { accessToken: string }) {
  const { signOut } = useSession();
  const [language, setLanguage] = useState<AppLanguage>(getDeviceLanguage);
  const api = useMemo(
    () => createApiClient(API_URL, () => accessToken, () => language),
    [accessToken, language],
  );
  const t = (key: Parameters<typeof translate>[1]) => translate(language, key);
  const energyOptions: { key: Energy; label: string; emoji: string }[] = [
    { key: 'low', label: t('energy_low'), emoji: '🪫' },
    { key: 'medium', label: t('energy_medium'), emoji: '⚡' },
    { key: 'high', label: t('energy_high'), emoji: '🚀' },
  ];
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
        setEvents(await listEvents(api, controller.signal));
        setUsingFallback(false);
      } catch (error) {
        if (!controller.signal.aborted) {
          if (error instanceof ApiClientError && error.status === 401) {
            void signOut();
            return;
          }
          setEvents(MOCK_EVENTS);
          setUsingFallback(true);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };

    void loadEvents();
    return () => controller.abort();
  }, [api, signOut]);

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
      const data = await sendAssistantMessage(
        api,
        content,
        threadId,
        Intl.DateTimeFormat().resolvedOptions().timeZone,
      );
      setChatReply(data.reply);
      setThreadId(data.thread_id);
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) {
        await signOut();
      }
      setChatError(
        error instanceof Error ? error.message : t('chat_failed'),
      );
      setMessage(content);
    } finally {
      setSending(false);
    }
  }, [api, message, sending, signOut, threadId, language]);

  const cognitiveLoad =
    cognitiveState === 'light'
      ? t('cognitive_light')
      : cognitiveState === 'moderate'
        ? t('cognitive_moderate')
        : t('cognitive_saturated');
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
                <Text style={styles.greeting}>{t('greeting')}</Text>
              </View>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={t('change_language')}
                onPress={() => {
                  const nextLanguage = language === 'es' ? 'en' : 'es';
                  setLanguage(nextLanguage);
                  void updatePreferredLanguage(api, nextLanguage).catch((error: unknown) => {
                    setChatError(
                      error instanceof Error ? error.message : t('connection_failed'),
                    );
                  });
                }}
                style={styles.languageButton}
              >
                <Text style={styles.languageText}>{language.toUpperCase()}</Text>
              </Pressable>
              <Pressable
                accessibilityLabel={t('logout')}
                accessibilityRole="button"
                onPress={() => void signOut().catch(() => undefined)}
                style={styles.avatar}
              >
                <Text style={styles.avatarText}>L</Text>
              </Pressable>
            </View>

            <View style={styles.statusCard}>
              <View style={styles.sectionHeading}>
                <View>
                  <Text style={styles.eyebrow}>{t('quick_checkin')}</Text>
                  <Text style={styles.cardTitle}>{t('how_feeling')}</Text>
                </View>
                <Text style={styles.sparkle}>✦</Text>
              </View>

              <View style={styles.energyRow}>
                {energyOptions.map((option) => {
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
                <Text style={styles.loadText}>{t('cognitive_load')}</Text>
                <Text style={[styles.loadValue, { color: loadColor }]}>{cognitiveLoad}</Text>
              </View>
              <View style={styles.cognitiveOptions}>
                {([
                  ['light', t('cognitive_light'), colors.green],
                  ['moderate', t('cognitive_moderate'), colors.amber],
                  ['saturated', t('cognitive_saturated'), colors.red],
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
                    {decompression ? t('decompression_active') : t('overwhelmed')}
                  </Text>
                  <Text style={styles.decompressionSubtitle}>
                    {decompression ? t('low_effort_tasks') : t('start_gently')}
                  </Text>
                </View>
                <Text style={styles.decompressionArrow}>{decompression ? '✓' : '→'}</Text>
              </Pressable>
            </View>

            <View style={styles.taskSection}>
              <View style={styles.todayHeading}>
                <View>
                  <Text style={styles.eyebrow}>{t('flexible_plan')}</Text>
                  <Text style={styles.sectionTitle}>{t('one_step')}</Text>
                </View>
                <View style={styles.energyFit}>
                  <Text style={styles.energyFitDot}>●</Text>
                  <Text style={styles.energyFitText}>
                    {energy === 'low'
                      ? t('energy_soft')
                      : energy === 'medium'
                        ? t('energy_fit')
                        : t('energy_momentum')}
                  </Text>
                </View>
              </View>

              <View style={styles.tabs}>
                {([
                  ['now', t('tab_now')],
                  ['today', t('tab_today')],
                  ['geofenced', t('tab_geofenced')],
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
                  <Text style={styles.fallbackText}>{t('local_mode')}</Text>
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
                    <EventCard key={event.id} event={event} language={language} />
                  ))}
                </View>
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={styles.emptyIcon}>{tab === 'geofenced' ? '⌖' : '☀'}</Text>
                  <Text style={styles.emptyTitle}>{t('no_tasks')}</Text>
                  <Text style={styles.emptyCopy}>{t('empty_day')}</Text>
                </View>
              )}

              <View style={styles.encouragement}>
                <Text style={styles.encouragementIcon}>✧</Text>
                <Text style={styles.encouragementText}>{t('encouragement')}</Text>
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
              accessibilityLabel={t('chat_placeholder')}
              placeholder={t('chat_placeholder')}
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
              accessibilityLabel={t('send_message')}
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
          <Text style={styles.composerHint}>{t('chat_hint')}</Text>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function EventCard({ event, language }: { event: EventItem; language: AppLanguage }) {
  const t = (key: Parameters<typeof translate>[1]) => translate(language, key);
  const priorityLabel =
    event.priority === 'high'
      ? t('priority_high')
      : event.priority === 'low'
        ? t('priority_low')
        : t('priority_medium');
  const priorityStyle =
    event.priority === 'high' ? styles.priorityHigh : event.priority === 'low' ? styles.priorityLow : styles.priorityMedium;
  const loadLabel =
    event.load <= 2 ? t('load_light') : event.load === 3 ? t('load_moderate') : t('load_high');
  const energyLabel = t(
    event.energy === 'low' ? 'energy_low' : event.energy === 'high' ? 'energy_high' : 'energy_medium',
  );
  const energyEmoji = event.energy === 'low' ? '🪫' : event.energy === 'high' ? '🚀' : '⚡';
  const geofenced = event.triggerType.startsWith('LOCATION_');

  return (
    <View style={styles.eventCard}>
      <View style={styles.eventAccent} />
      <View style={styles.eventContent}>
        <View style={styles.eventTopline}>
          <Text style={styles.eventTime}>
            {geofenced
              ? t('location_arrival')
              : event.isMicroAction
                ? t('micro_action')
                : `◷  ${eventTime(event.startAt, language)}`}
          </Text>
          <Text style={[styles.priorityBadge, priorityStyle]}>{priorityLabel}</Text>
        </View>
        <Text style={styles.eventTitle}>{event.title}</Text>
        {event.description ? <Text style={styles.eventDescription}>{event.description}</Text> : null}
        {geofenced && event.location ? (
          <Text style={styles.locationText}>⌖  {event.location}</Text>
        ) : null}
        <View style={styles.eventBadges}>
          <Text style={styles.durationBadge}>◷  {durationLabel(event, language)}</Text>
          <Text style={styles.loadBadge}>◌  {t('load_label')} {loadLabel} · {event.load}/5</Text>
          <Text style={styles.energyBadge}>{energyLabel} {energyEmoji}</Text>
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
  loadingScreen: { flex: 1, alignItems: 'center', justifyContent: 'center' },
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
  languageButton: {
    minWidth: 42,
    height: 38,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 'auto',
    marginRight: 10,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.line,
  },
  languageText: { color: colors.violet, fontSize: 12, fontWeight: '800' },
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

export default function HomeScreen() {
  const { accessToken, ready } = useSession();
  if (!ready) {
    return (
      <View style={styles.loadingScreen}>
        <ActivityIndicator color={colors.violet} />
      </View>
    );
  }
  if (!accessToken) return <Redirect href="/login" />;
  return <HomeContent accessToken={accessToken} />;
}
