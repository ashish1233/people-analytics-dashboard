import {
  Alert,
  AppShell,
  LoginPanel,
  useAuth,
  useHealth,
} from '@insights-platform/ui-kit';
import {
  API_BASE_URL,
  APP_DESCRIPTION,
  APP_NAME,
  EXPECTED_TIER,
  IDENTITY_BASE_URL,
  SCOPES,
  TENANT_ID,
} from './config';
import { CompensationPage } from './CompensationPage';

export function App() {
  const auth = useAuth({ identityUrl: IDENTITY_BASE_URL, scopes: SCOPES });
  const { health } = useHealth({ apiUrl: API_BASE_URL });

  // `/health` is authoritative; the constant only covers the gap before it
  // answers, so the restricted marking is never missing from the header.
  const tier = health?.tier ?? EXPECTED_TIER;
  const tierMismatch = health != null && health.tier !== EXPECTED_TIER;

  if (!auth.isAuthenticated) {
    return (
      <LoginPanel
        appName={APP_NAME}
        description={APP_DESCRIPTION}
        onSubmit={auth.login}
        busy={auth.status === 'signing-in'}
        tenants={[{ label: TENANT_ID, value: TENANT_ID }]}
        defaultTenantId={TENANT_ID}
        errorTitle={auth.expired ? 'Session expired' : 'Could not sign in'}
        error={
          auth.expired
            ? 'Your session timed out. Sign in again to continue.'
            : auth.error
        }
      />
    );
  }

  return (
    <AppShell
      appName={APP_NAME}
      tenantId={health?.tenant_id ?? TENANT_ID}
      tier={tier}
      subject={auth.session?.subject}
      onSignOut={() => auth.logout()}
    >
      {tierMismatch ? (
        <Alert
          tone="warning"
          title="Tier mismatch"
          className="page-alert"
        >
          The backend reports the <strong>{health?.tier}</strong> tier, but this
          app is registered as <strong>{EXPECTED_TIER}</strong>. Restricted-tier
          controls may not be active. Tell the platform team before using this
          data.
        </Alert>
      ) : null}

      <CompensationPage
        token={auth.token}
        onSessionExpired={() => auth.logout({ expired: true })}
      />
    </AppShell>
  );
}
