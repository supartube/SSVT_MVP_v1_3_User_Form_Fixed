import type { CapacitorConfig } from '@capacitor/cli';
const config: CapacitorConfig = {
  appId: 'com.ssvt.app', appName: 'SSVT', webDir: 'www',
  server: { url: 'https://YOUR-SSVT-RENDER-URL.onrender.com', cleartext: false }
};
export default config;
