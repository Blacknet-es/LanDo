import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { SessionProvider } from '../src/auth/SessionProvider';

export default function RootLayout() {
  return (
    <SessionProvider>
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: '#F6F5F2' },
        }}
      />
      <StatusBar style="dark" />
    </SessionProvider>
  );
}
