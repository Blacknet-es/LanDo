import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Redirect } from 'expo-router';

import { ApiClientError, createApiClient } from '@shared/api/client';
import { getDeviceLanguage, translate } from '@shared/i18n';
import { authenticate } from '../src/application/authenticate';
import { useSession } from '../src/auth/SessionProvider';

const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8001').replace(/\/$/, '');

export default function LoginScreen() {
  const { accessToken, storageError, ready, signIn } = useSession();
  const [language] = useState(getDeviceLanguage);
  const t = (key: Parameters<typeof translate>[1]) => translate(language, key);
  const api = useMemo(() => createApiClient(API_URL, () => null, () => language), [language]);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [registering, setRegistering] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  if (!ready) {
    return <ActivityIndicator style={styles.centered} />;
  }
  if (accessToken) return <Redirect href="/" />;

  const submit = async () => {
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !password) {
      setError(t('enter_credentials'));
      return;
    }

    setBusy(true);
    setError('');
    try {
      const token = await authenticate(api, normalizedEmail, password, registering);
      await signIn(token);
    } catch (caught) {
      const status = caught instanceof ApiClientError ? caught.status : undefined;
      setError(
        status === 409
          ? t('account_exists')
          : status === 401
            ? t('invalid_credentials')
            : caught instanceof Error
              ? caught.message
              : t('connection_failed'),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.card}>
        <Text style={styles.brand}>LanDo ✳</Text>
        <Text style={styles.title}>{registering ? t('create_account') : t('welcome_back')}</Text>
        <Text style={styles.subtitle}>{t('login_subtitle')}</Text>
        <TextInput
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          onChangeText={setEmail}
          placeholder={t('email')}
          placeholderTextColor="#8C8A98"
          style={styles.input}
          value={email}
        />
        <TextInput
          autoComplete={registering ? 'new-password' : 'current-password'}
          onChangeText={setPassword}
          placeholder={t('password')}
          placeholderTextColor="#8C8A98"
          secureTextEntry
          style={styles.input}
          value={password}
        />
        {error || storageError ? (
          <Text style={styles.error}>{error || storageError}</Text>
        ) : null}
        <Pressable disabled={busy} onPress={() => void submit()} style={styles.primary}>
          {busy ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.primaryText}>{registering ? t('create') : t('login')}</Text>
          )}
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={() => {
            setRegistering((current) => !current);
            setError('');
          }}
          style={styles.toggle}
        >
          <Text style={styles.toggleText}>
            {registering ? t('existing_account') : t('new_account')}
          </Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#F6F5F2',
  },
  centered: { flex: 1 },
  card: {
    width: '100%',
    maxWidth: 430,
    alignSelf: 'center',
    padding: 26,
    borderRadius: 24,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E8E6EC',
  },
  brand: { color: '#6555B7', fontSize: 16, fontWeight: '800', marginBottom: 24 },
  title: { color: '#282536', fontSize: 27, fontWeight: '800' },
  subtitle: { color: '#777483', fontSize: 14, lineHeight: 21, marginTop: 8, marginBottom: 24 },
  input: {
    borderWidth: 1,
    borderColor: '#E5E3EA',
    borderRadius: 13,
    paddingHorizontal: 14,
    paddingVertical: 13,
    marginBottom: 12,
    color: '#282536',
  },
  error: { color: '#C34E59', fontSize: 13, marginVertical: 4 },
  primary: {
    backgroundColor: '#6555B7',
    minHeight: 48,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 10,
  },
  primaryText: { color: '#FFFFFF', fontSize: 15, fontWeight: '700' },
  toggle: { alignItems: 'center', paddingTop: 18 },
  toggleText: { color: '#6555B7', fontSize: 14, fontWeight: '600' },
});
