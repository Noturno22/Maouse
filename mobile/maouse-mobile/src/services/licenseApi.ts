import Constants from 'expo-constants';

const PROD_FALLBACK = 'https://license.maouse.app';

export interface EntitleResponse {
  tier: string;
  lease: string;
  session_id: string;
  first_time: boolean;
}

export interface EntitleParams {
  purchaseToken: string;
  productId: string;
  packageName: string;
  deviceId: string;
}

/**
 * Em desenvolvimento (dev-client ligado ao Metro) o hostUri e o
 * host:porta do Metro, ou seja o IP real deste PC na LAN. O
 * license-server vive no mesmo PC, na porta 8000.
 *
 * Usar o hostUri evita o problema classico de um IP fixo em .env:
 * o DHCP muda o IP e o APK dev deixa de falar com o servidor ate
 * recompilar.
 */
function devLicenseServerUrl(): string | null {
  const hostUri = Constants.expoConfig?.hostUri;
  if (!hostUri) return null;
  const host = String(hostUri)
    .replace(/^[a-z]+:\/\//i, '')
    .replace(/\/.*$/, '')
    .split(':')[0]
    .trim();
  if (!host) return null;
  // localhost/127.0.0.1 nao sao alcancaveis a partir do telemovel.
  if (host === 'localhost' || host === '127.0.0.1' || host === '::1') return null;
  return `http://${host}:8000`;
}

/**
 * O .env.example traz um placeholder (https://<service>.onrender.com).
 * Nao e um URL valido - se passar, o build de producao aponta para
 * um dominio que nao existe.
 */
function isUsable(value: string | undefined): value is string {
  return !!value && !value.includes('<') && !value.includes('>');
}

export function licenseServerUrl(): string {
  const baked = process.env.EXPO_PUBLIC_LICENSE_SERVER_URL;

  // Um https:// explicito e uma escolha deliberada (apontar o dev
  // para um servidor deployed) e ganha sobre a derivacao local.
  if (isUsable(baked) && /^https:\/\//i.test(baked)) return baked;

  const dev = devLicenseServerUrl();
  if (dev) return dev;

  if (isUsable(baked)) return baked;
  return (Constants.expoConfig?.extra?.licenseServerUrl as string) || PROD_FALLBACK;
}

export function isDevServer(): boolean {
  return devLicenseServerUrl() !== null;
}

export async function entitleMobilePurchase(
  params: EntitleParams
): Promise<EntitleResponse> {
  const res = await fetch(`${licenseServerUrl()}/api/v1/mobile/entitle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && body.error) message = String(body.error);
    } catch {
      // fallback to HTTP message
    }
    throw new Error(message);
  }
  return (await res.json()) as EntitleResponse;
}
