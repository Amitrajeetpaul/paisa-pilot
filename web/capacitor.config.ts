import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.paisapilot.app',
  appName: 'Paisa Pilot',
  webDir: 'dist',
  server: {
    url: 'https://paisa-pilot-web-316611436028.asia-south1.run.app',
    cleartext: true,
  },
};

export default config;
