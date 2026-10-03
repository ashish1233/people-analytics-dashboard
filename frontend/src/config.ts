import type { TenantTier } from '@insights-platform/ui-kit';

/** Everything app-specific, in one file — the same shape as the scaffold. */

export const APP_NAME = 'Compensation Insights';

export const APP_DESCRIPTION =
  'People Analytics compensation reporting. Access is logged.';

export const TENANT_ID = 'people-analytics';

/**
 * `insights:read_sensitive` is what makes salary columns visible. The token is
 * issued with it; whether it is honoured is decided by the backend middleware
 * and the warehouse role, not here.
 */
export const SCOPES = ['insights:read', 'insights:read_sensitive'];

export const DATASET_LABEL = 'compensation metrics';

/**
 * The tier this tenant is assigned (ADR-2), used only as a display fallback
 * while `/health` is in flight or unreachable.
 *
 * The app does not get to assert its own tier — `/health` is the source of
 * truth, and `App.tsx` raises a warning if the backend disagrees with this
 * constant. That disagreement would mean a tenant believed to be restricted is
 * running without fail-closed audit, which is worth interrupting someone over.
 */
export const EXPECTED_TIER: TenantTier = 'restricted';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export const IDENTITY_BASE_URL =
  import.meta.env.VITE_IDENTITY_BASE_URL ?? 'http://localhost:8081';
